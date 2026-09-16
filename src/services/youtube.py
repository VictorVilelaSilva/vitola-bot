import asyncio
import json
import re
import sys
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import parse_qs, urlparse

from src.config import Settings


class DownloadError(Exception):
    pass


GENERIC_VIDEO_DOWNLOAD_ERROR = (
    "Não foi possível baixar esse vídeo. Verifique se o link é de um vídeo público "
    "em uma plataforma compatível."
)


def validate_media_url(url: str) -> str:
    parsed = urlparse(url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        raise DownloadError(GENERIC_VIDEO_DOWNLOAD_ERROR)
    return url


def validate_youtube_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or parsed.username or parsed.password:
        raise DownloadError("Envie um link válido do YouTube.")
    host = parsed.netloc.lower()
    if host in {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}:
        video_id = parse_qs(parsed.query).get("v", [""])[0] if parsed.path == "/watch" else ""
        if parsed.path.startswith(("/shorts/", "/live/")):
            video_id = parsed.path.split("/")[2]
    elif host == "youtu.be":
        video_id = parsed.path.lstrip("/")
    else:
        video_id = ""
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        raise DownloadError("Envie o link de um vídeo do YouTube, não de uma playlist.")
    return f"https://www.youtube.com/watch?v={video_id}"


@dataclass(frozen=True)
class DownloadedAudio:
    path: Path
    title: str


@dataclass(frozen=True)
class DownloadedVideo:
    path: Path
    title: str


class YouTubeDownloader:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._slots = asyncio.Semaphore(2)

    @asynccontextmanager
    async def prepare(self, url: str):
        async with self._prepare(url, "audio", self.settings.max_download_bytes) as downloaded:
            yield DownloadedAudio(path=downloaded.path, title=downloaded.title)

    @asynccontextmanager
    async def prepare_video(self, url: str, max_bytes: int | None = None):
        limit = min(max_bytes or self.settings.max_video_bytes, self.settings.max_video_bytes)
        async with self._prepare(url, "video", limit) as downloaded:
            yield DownloadedVideo(path=downloaded.path, title=downloaded.title)

    @asynccontextmanager
    async def prepare_mp3(self, url: str, max_bytes: int):
        limit = min(max_bytes, self.settings.max_download_bytes)
        async with self._prepare(url, "mp3", limit) as downloaded:
            yield DownloadedAudio(path=downloaded.path, title=downloaded.title)

    @asynccontextmanager
    async def _prepare(self, url: str, media_type: str, max_bytes: int):
        url = (
            validate_media_url(url) if media_type in {"video", "mp3"} else validate_youtube_url(url)
        )
        with TemporaryDirectory(prefix=f"vitola-{media_type}-") as directory:
            async with self._slots:
                process = await asyncio.create_subprocess_exec(
                    sys.executable,
                    "-m",
                    "src.services.youtube_worker",
                    url,
                    directory,
                    str(self.settings.max_audio_seconds),
                    str(max_bytes),
                    media_type,
                    cwd=Path(__file__).resolve().parents[2],
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                try:
                    await asyncio.wait_for(process.wait(), timeout=self.settings.download_timeout)
                except TimeoutError as error:
                    raise DownloadError("O download excedeu o tempo permitido.") from error
                finally:
                    if process.returncode is None:
                        try:
                            process.kill()
                        except ProcessLookupError:
                            pass
                        await process.wait()
            result_path = Path(directory) / "result.json"
            if not result_path.is_file():
                raise DownloadError("Não foi possível baixar esse vídeo.")
            result = json.loads(result_path.read_text())
            if process.returncode or "error" in result:
                raise DownloadError(result.get("error", "Download mal sucedido."))
            path = Path(directory) / result["filename"]
            if (
                path.parent != Path(directory)
                or not path.is_file()
                or path.stat().st_size > max_bytes
            ):
                raise DownloadError("O download não gerou um arquivo de mídia válido.")
            yield DownloadedVideo(path=path, title=result["title"])
