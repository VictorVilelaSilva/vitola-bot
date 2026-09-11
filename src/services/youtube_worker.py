"""Blocking media requests run in a disposable child process, never on the bot loop."""

import json
import socket
import sys
from pathlib import Path

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError as YtDlpDownloadError

from src.services.youtube import (
    GENERIC_VIDEO_DOWNLOAD_ERROR,
    DownloadError,
    validate_media_url,
    validate_youtube_url,
)


def _limit_message(media_type: str) -> str:
    subject = "O vídeo" if media_type == "video" else "O áudio"
    return f"{subject} excede o tamanho máximo permitido."


def _estimated_size(format_info: dict, duration: float) -> int | None:
    if size := format_info.get("filesize") or format_info.get("filesize_approx"):
        return int(size)
    if bitrate := format_info.get("tbr"):
        return int(float(bitrate) * 1000 / 8 * duration)
    return None


def _video_format_selector(max_bytes: int):
    budget = int(max_bytes * 0.97)

    def selector(context):
        formats = list(reversed(context.get("formats") or []))
        duration = float(context.get("duration") or 0)
        if not any(item.get("vcodec") != "none" for item in formats):
            raise DownloadError(GENERIC_VIDEO_DOWNLOAD_ERROR)
        videos = [
            item
            for item in formats
            if item.get("vcodec") != "none" and item.get("acodec") == "none"
        ]
        audios = [
            item
            for item in formats
            if item.get("vcodec") == "none" and item.get("acodec") != "none"
        ]
        compatibility_groups = (
            (
                lambda item: (
                    item.get("ext") == "mp4" and str(item.get("vcodec", "")).startswith("avc1")
                ),
                lambda item: item.get("ext") == "m4a",
                "mp4",
            ),
            (
                lambda item: item.get("ext") == "mp4",
                lambda item: item.get("ext") == "m4a",
                "mp4",
            ),
            (
                lambda item: item.get("ext") == "webm",
                lambda item: item.get("ext") == "webm",
                "webm",
            ),
        )
        for video_filter, audio_filter, extension in compatibility_groups:
            for video in filter(video_filter, videos):
                video_size = _estimated_size(video, duration)
                if video_size is None:
                    continue
                for audio in filter(audio_filter, audios):
                    audio_size = _estimated_size(audio, duration)
                    if audio_size is None or video_size + audio_size > budget:
                        continue
                    yield {
                        "format_id": f"{video['format_id']}+{audio['format_id']}",
                        "ext": extension,
                        "requested_formats": [video, audio],
                        "protocol": f"{video['protocol']}+{audio['protocol']}",
                    }
                    return

        for item in formats:
            size = _estimated_size(item, duration)
            if (
                item.get("vcodec") != "none"
                and item.get("acodec") != "none"
                and size is not None
                and size <= budget
            ):
                yield item
                return
        raise DownloadError(_limit_message("video"))

    return selector


def _format_selector(media_type: str, max_bytes: int):
    if media_type == "audio":
        return (
            f"bestaudio[filesize<={max_bytes}]/bestaudio[filesize_approx<={max_bytes}]/worstaudio"
        )
    return _video_format_selector(max_bytes)


def download(
    url: str,
    directory: Path,
    max_seconds: int,
    max_bytes: int,
    media_type: str = "audio",
) -> dict:
    if media_type not in {"audio", "video"}:
        raise DownloadError("Tipo de download inválido.")

    def check_video(info, *, incomplete):
        if incomplete:
            return None
        duration = info.get("duration")
        if info.get("is_live") or not duration or duration > max_seconds:
            raise DownloadError(
                f"Escolha um vídeo de até {max_seconds // 60} minutos; lives não são aceitas."
            )
        return None

    downloaded_files = {}

    def on_progress(progress):
        downloaded = progress.get("downloaded_bytes") or 0
        total = progress.get("total_bytes") or progress.get("total_bytes_estimate") or 0
        key = progress.get("filename") or "download"
        downloaded_files[key] = max(downloaded, total)
        if sum(downloaded_files.values()) > max_bytes:
            raise DownloadError(_limit_message(media_type))

    output_template = str(directory / f"{media_type}.%(ext)s")
    options = {
        "format": _format_selector(media_type, max_bytes),
        "outtmpl": output_template,
        "noplaylist": True,
        "max_filesize": max_bytes,
        "match_filter": check_video,
        "progress_hooks": [on_progress],
        "socket_timeout": 15,
        "retries": 1,
        "fragment_retries": 1,
        "merge_output_format": "mp4" if media_type == "video" else None,
        "quiet": True,
        "noprogress": True,
        "no_warnings": True,
    }
    try:
        with YoutubeDL(options) as ydl:
            validated_url = (
                validate_media_url(url) if media_type == "video" else validate_youtube_url(url)
            )
            info = ydl.extract_info(validated_url, download=True)
    except DownloadError:
        raise
    except YtDlpDownloadError as error:
        message = str(error).lower()
        if "max-filesize" in message or "larger than" in message:
            raise DownloadError(_limit_message(media_type)) from error
        raise DownloadError(GENERIC_VIDEO_DOWNLOAD_ERROR) from error

    candidates = [
        path
        for path in directory.glob(f"{media_type}.*")
        if path.is_file() and not path.name.endswith((".part", ".ytdl"))
    ]
    if not info or len(candidates) != 1 or candidates[0].stat().st_size > max_bytes:
        raise DownloadError(
            f"O download não gerou um {media_type == 'video' and 'vídeo' or 'áudio'} "
            "dentro do limite permitido."
        )
    return {"filename": candidates[0].name, "title": str(info.get("title") or "YouTube")}


def main():
    url, directory, max_seconds, max_bytes, *arguments = sys.argv[1:]
    media_type = arguments[0] if arguments else "audio"
    socket.setdefaulttimeout(15)
    try:
        result = download(url, Path(directory), int(max_seconds), int(max_bytes), media_type)
        status = 0
    except DownloadError as error:
        result, status = {"error": str(error)}, 1
    except Exception:
        result, status = ({"error": GENERIC_VIDEO_DOWNLOAD_ERROR}, 1)
    (Path(directory) / "result.json").write_text(json.dumps(result), encoding="utf-8")
    return status


if __name__ == "__main__":
    sys.exit(main())
