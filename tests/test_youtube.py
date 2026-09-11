import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from src.cogs.music import MusicCog
from src.config import Settings
from src.services.youtube import (
    DownloadedVideo,
    DownloadError,
    YouTubeDownloader,
    validate_media_url,
    validate_youtube_url,
)
from src.services.youtube_worker import _video_format_selector, download


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


@pytest.mark.parametrize(
    "url",
    [
        "https://www.tiktok.com/@user/video/123456789",
        "https://www.instagram.com/reel/example/",
        "https://media.example/video.mp4",
    ],
)
def test_generic_video_links_accept_any_http_platform(url):
    assert validate_media_url(url) == url


@pytest.mark.parametrize("url", ["file:///etc/passwd", "javascript:alert(1)", "https://"])
def test_generic_video_links_reject_non_web_urls(url):
    with pytest.raises(DownloadError, match="plataforma compatível"):
        validate_media_url(url)


class FakeProcess:
    def __init__(self, directory, *, finish=False, error=None, media_type="audio"):
        self.directory = Path(directory)
        self.returncode = None
        self.killed = False
        self.done = asyncio.Event()
        if finish:
            if error:
                result = {"error": error}
                self.returncode = 1
            else:
                filename = "video.mp4" if media_type == "video" else "audio.webm"
                (self.directory / filename).write_bytes(b"audio")
                result = {"filename": filename, "title": "Video"}
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


def make_ydl(monkeypatch, *, seconds=60, size=100, ext="webm"):
    state = {}

    class FakeYoutubeDL:
        def __init__(self, options):
            state["options"] = options

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def extract_info(self, url, *, download):
            state.update(url=url, download=download)
            info = {"duration": seconds, "is_live": False, "title": "Video"}
            state["options"]["match_filter"](info, incomplete=False)
            state["options"]["progress_hooks"][0]({"downloaded_bytes": size, "total_bytes": size})
            output = Path(state["options"]["outtmpl"].replace("%(ext)s", ext))
            output.write_bytes(b"x" * size)
            return info

    factory = Mock(side_effect=FakeYoutubeDL)
    monkeypatch.setattr("src.services.youtube_worker.YoutubeDL", factory)
    return state, factory


@pytest.mark.parametrize("seconds,size", [(1000, 100), (0, 100), (60, 10000)])
def test_worker_checks_duration_and_size_before_download(monkeypatch, tmp_path, seconds, size):
    state, _ = make_ydl(monkeypatch, seconds=seconds, size=size)
    with pytest.raises(DownloadError):
        download("https://youtu.be/abcdefghijk", tmp_path, 900, 1000)
    assert not list(tmp_path.glob("audio.*"))


def test_worker_keeps_real_container_and_stable_metadata(monkeypatch, tmp_path):
    state, _ = make_ydl(monkeypatch)
    result = download("https://youtu.be/abcdefghijk", tmp_path, 900, 1000)
    assert result == {"filename": "audio.webm", "title": "Video"}
    assert (tmp_path / result["filename"]).is_file()
    assert state["download"] is True
    assert state["options"]["socket_timeout"] == 15
    assert state["options"]["noplaylist"] is True
    assert state["options"]["format"].startswith("bestaudio")


def test_progress_limit_handles_inaccurate_size_metadata(monkeypatch, tmp_path):
    make_ydl(monkeypatch, size=1001)
    with pytest.raises(DownloadError, match="tamanho"):
        download("https://youtu.be/abcdefghijk", tmp_path, 900, 1000)


def test_worker_downloads_video_with_audio_and_prefers_mp4(monkeypatch, tmp_path):
    state, _ = make_ydl(monkeypatch, ext="mp4")
    tiktok_url = "https://www.tiktok.com/@user/video/123456789"
    result = download(tiktok_url, tmp_path, 900, 1000, "video")
    assert result == {"filename": "video.mp4", "title": "Video"}
    assert state["url"] == tiktok_url
    assert callable(state["options"]["format"])
    assert state["options"]["merge_output_format"] == "mp4"


def test_video_selector_combines_compatible_streams_inside_limit():
    formats = [
        {
            "format_id": "audio",
            "ext": "m4a",
            "vcodec": "none",
            "acodec": "mp4a.40.2",
            "filesize": 200,
            "protocol": "https",
        },
        {
            "format_id": "video",
            "ext": "mp4",
            "vcodec": "avc1.4d401f",
            "acodec": "none",
            "filesize": 700,
            "protocol": "https",
        },
    ]
    selected = list(_video_format_selector(1000)({"formats": formats, "duration": 60}))
    assert selected[0]["format_id"] == "video+audio"
    assert selected[0]["ext"] == "mp4"


async def test_prepare_video_passes_discord_limit_and_cleans_file(monkeypatch):
    spawned = []

    async def spawn(*args, **kwargs):
        process = FakeProcess(args[4], finish=True, media_type=args[7])
        spawned.append((args, process))
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    downloader = YouTubeDownloader(Settings(max_video_bytes=500))
    async with downloader.prepare_video("https://youtu.be/abcdefghijk", 300) as video:
        assert video.path.name == "video.mp4"
        assert video.path.is_file()
    assert spawned[0][0][6:] == ("300", "video")
    assert not spawned[0][1].directory.exists()


async def test_video_command_sends_attachment_in_request_channel(tmp_path):
    path = tmp_path / "video.mp4"
    path.write_bytes(b"video")

    class FakeDownloader:
        def __init__(self):
            self.arguments = None

        @asynccontextmanager
        async def prepare_video(self, url, max_bytes):
            self.arguments = (url, max_bytes)
            yield DownloadedVideo(path=path, title="Meu vídeo")

    @asynccontextmanager
    async def typing():
        yield

    bot = SimpleNamespace(settings=Settings(max_video_bytes=10))
    cog = MusicCog(bot)
    cog.downloader = FakeDownloader()
    ctx = SimpleNamespace(
        guild=SimpleNamespace(filesize_limit=5),
        typing=typing,
        send=AsyncMock(),
    )

    await cog.video.callback(cog, ctx, "https://youtu.be/abcdefghijk")

    assert cog.downloader.arguments == ("https://youtu.be/abcdefghijk", 5)
    assert ctx.send.await_args.args == ("Vídeo baixado: Meu vídeo",)
    assert ctx.send.await_args.kwargs["file"].filename == "video.mp4"


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
