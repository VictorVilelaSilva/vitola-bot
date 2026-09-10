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


class YouTubeDownloader:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._slots = asyncio.Semaphore(2)

    @asynccontextmanager
    async def prepare(self, url: str):
        url = validate_youtube_url(url)
        with TemporaryDirectory(prefix="vitola-audio-") as directory:
            async with self._slots:
                process = await asyncio.create_subprocess_exec(
                    sys.executable,
                    "-m",
                    "src.services.youtube_worker",
                    url,
                    directory,
                    str(self.settings.max_audio_seconds),
                    str(self.settings.max_download_bytes),
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
            if path.parent != Path(directory) or not path.is_file():
                raise DownloadError("O download não gerou um arquivo de áudio válido.")
            yield DownloadedAudio(path=path, title=result["title"])
