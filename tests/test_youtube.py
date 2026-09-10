import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.config import Settings
from src.services.youtube import DownloadError, YouTubeDownloader, validate_youtube_url
from src.services.youtube_worker import download


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/watch?v=abcdefghijk",
        "file:///etc/passwd",
        "https://www.youtube.com.evil.test/watch?v=abcdefghijk",
        "https://youtube.com/playlist?list=abc",
        "https://user:pass@youtube.com/watch?v=abcdefghijk",
        "https://youtu.be/short",
    ],
)
def test_reject_invalid_links(url):
    with pytest.raises(DownloadError):
        validate_youtube_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://youtu.be/abcdefghijk?t=10",
        "https://www.youtube.com/watch?v=abcdefghijk&list=playlist",
        "https://m.youtube.com/shorts/abcdefghijk",
    ],
)
def test_canonical_video_links(url):
    assert validate_youtube_url(url) == "https://www.youtube.com/watch?v=abcdefghijk"


class FakeProcess:
    def __init__(self, directory, *, finish=False, error=None):
        self.directory = Path(directory)
        self.returncode = None
        self.killed = False
        self.done = asyncio.Event()
        if finish:
            if error:
                result = {"error": error}
                self.returncode = 1
            else:
                (self.directory / "audio.webm").write_bytes(b"audio")
                result = {"filename": "audio.webm", "title": "Video"}
                self.returncode = 0
            (self.directory / "result.json").write_text(json.dumps(result))
            self.done.set()

    async def wait(self):
        await self.done.wait()
        return self.returncode

    def kill(self):
        self.killed = True
        self.returncode = -9
        self.done.set()


async def test_download_context_cleans_unique_files_after_use(monkeypatch):
    processes = []

    async def spawn(*args, **kwargs):
        process = FakeProcess(args[4], finish=True)
        processes.append(process)
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    downloader = YouTubeDownloader(Settings())
    paths = []
    for _ in range(2):
        async with downloader.prepare("https://youtu.be/abcdefghijk") as audio:
            paths.append(audio.path)
            assert audio.path.is_file()
            assert audio.title == "Video"
            assert audio.path.suffix == ".webm"
        assert not paths[-1].parent.exists()
    assert paths[0] != paths[1]


@pytest.mark.parametrize("cancel", [False, True])
async def test_timeout_or_cancel_kills_process_and_cleans_files(monkeypatch, cancel):
    processes = []
    started = asyncio.Event()

    async def spawn(*args, **kwargs):
        process = FakeProcess(args[4])
        processes.append(process)
        started.set()
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    downloader = YouTubeDownloader(Settings(download_timeout=60 if cancel else 0.01))

    async def operation():
        async with downloader.prepare("https://youtu.be/abcdefghijk"):
            pytest.fail("Download never completed.")

    task = asyncio.create_task(operation())
    await started.wait()
    if cancel:
        task.cancel()
    with pytest.raises(asyncio.CancelledError if cancel else DownloadError):
        await task
    assert processes[0].killed
    assert not processes[0].directory.exists()


async def test_download_error_is_reported_without_exiting_bot(monkeypatch):
    processes = []

    async def spawn(*args, **kwargs):
        process = FakeProcess(args[4], finish=True, error="Vídeo indisponível.")
        processes.append(process)
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    with pytest.raises(DownloadError, match="indisponível"):
        async with YouTubeDownloader(Settings()).prepare("https://youtu.be/abcdefghijk"):
            pytest.fail("Must not yield failed downloads.")
    assert not processes[0].directory.exists()


def make_video(monkeypatch, *, seconds=60, size=100):
    stream = SimpleNamespace(subtype="webm", filesize=size)

    def save(**kwargs):
        path = Path(kwargs["output_path"]) / kwargs["filename"]
        path.write_bytes(b"audio")
        return str(path)

    stream.download = Mock(side_effect=save)
    streams = Mock()
    streams.filter.return_value.order_by.return_value.first.return_value = stream
    video = SimpleNamespace(length=seconds, streams=streams, title="Video")
    factory = Mock(return_value=video)
    monkeypatch.setattr("src.services.youtube_worker.YouTube", factory)
    return stream, factory


@pytest.mark.parametrize("seconds,size", [(1000, 100), (0, 100), (60, 10000)])
def test_worker_checks_duration_and_size_before_download(monkeypatch, tmp_path, seconds, size):
    stream, _ = make_video(monkeypatch, seconds=seconds, size=size)
    with pytest.raises(DownloadError):
        download("https://youtu.be/abcdefghijk", tmp_path, 900, 1000)
    stream.download.assert_not_called()


def test_worker_keeps_real_container_and_stable_metadata(monkeypatch, tmp_path):
    stream, _ = make_video(monkeypatch)
    result = download("https://youtu.be/abcdefghijk", tmp_path, 900, 1000)
    assert result == {"filename": "audio.webm", "title": "Video"}
    assert (tmp_path / result["filename"]).is_file()
    assert stream.download.call_args.kwargs["timeout"] == 15


def test_progress_limit_handles_inaccurate_size_metadata(monkeypatch, tmp_path):
    stream, factory = make_video(monkeypatch)

    def oversized_download(**kwargs):
        factory.call_args.kwargs["on_progress_callback"](stream, b"x" * 1001, 0)

    stream.download.side_effect = oversized_download
    with pytest.raises(DownloadError, match="tamanho"):
        download("https://youtu.be/abcdefghijk", tmp_path, 900, 1000)


async def test_download_slots_are_released_before_playback_finishes(monkeypatch):
    from contextlib import AsyncExitStack

    processes = []

    async def spawn(*args, **kwargs):
        process = FakeProcess(args[4], finish=True)
        processes.append(process)
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    downloader = YouTubeDownloader(Settings())
    async with AsyncExitStack() as stack:
        # All three files remain in use, but none should hold a download slot.
        for _ in range(3):
            audio = await asyncio.wait_for(
                stack.enter_async_context(downloader.prepare("https://youtu.be/abcdefghijk")),
                1,
            )
            assert audio.path.is_file()
        assert len(processes) == 3
    assert all(not process.directory.exists() for process in processes)
