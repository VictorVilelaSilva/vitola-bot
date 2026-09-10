"""Blocking YouTube requests run in a disposable child process, never on the bot loop."""

import json
import socket
import sys
from pathlib import Path

from pytubefix import YouTube

from src.services.youtube import DownloadError, validate_youtube_url


def download(url: str, directory: Path, max_seconds: int, max_bytes: int) -> dict:
    downloaded = 0

    def on_progress(stream, chunk, bytes_remaining):
        nonlocal downloaded
        downloaded += len(chunk)
        if downloaded > max_bytes:
            raise DownloadError("O áudio excede o tamanho máximo permitido.")

    video = YouTube(validate_youtube_url(url), on_progress_callback=on_progress)
    if not video.length or video.length > max_seconds:
        raise DownloadError(
            f"Escolha um vídeo de até {max_seconds // 60} minutos; lives não são aceitas."
        )
    stream = video.streams.filter(only_audio=True).order_by("abr").first()
    if stream is None:
        raise DownloadError("Esse vídeo não possui uma faixa de áudio disponível.")
    if stream.filesize > max_bytes:
        raise DownloadError("O áudio excede o tamanho máximo permitido.")
    filename = f"audio.{stream.subtype}"
    path = stream.download(output_path=str(directory), filename=filename, timeout=15, max_retries=1)
    if not path or Path(path).stat().st_size > max_bytes:
        raise DownloadError("O download não gerou um áudio dentro do limite permitido.")
    return {"filename": filename, "title": video.title}


def main():
    url, directory, max_seconds, max_bytes = sys.argv[1:]
    socket.setdefaulttimeout(15)
    try:
        result = download(url, Path(directory), int(max_seconds), int(max_bytes))
        status = 0
    except DownloadError as error:
        result, status = {"error": str(error)}, 1
    except Exception:
        result, status = (
            {"error": "Não foi possível baixar esse vídeo. Ele pode estar indisponível."},
            1,
        )
    (Path(directory) / "result.json").write_text(json.dumps(result), encoding="utf-8")
    return status


if __name__ == "__main__":
    sys.exit(main())
