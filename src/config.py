import os
from dataclasses import dataclass, field


def positive_int(name: str, default: int) -> int:
    value = int(os.getenv(name, str(default)))
    if value <= 0:
        raise ValueError(f"{name} deve ser um inteiro positivo.")
    return value


@dataclass(frozen=True)
class Settings:
    discord_token: str = field(default="", repr=False)
    gemini_api_key: str = field(default="", repr=False)
    gemini_model: str = "gemini-3.1-flash-lite"
    code_channel_id: int | None = None
    queue_size: int = 20
    max_audio_seconds: int = 900
    max_download_bytes: int = 50 * 1024 * 1024
    max_video_bytes: int = 10 * 1024 * 1024
    download_timeout: int = 90
    chat_idle_timeout: int = 120
    chat_request_timeout: int = 45
    chat_max_turns: int = 20
    chat_max_sessions: int = 20

    @classmethod
    def from_env(cls):
        channel_id = os.getenv("CODIGO_DISCORD_CHANNEL_ID_TOKEN", "").strip()
        return cls(
            discord_token=os.getenv("DISCORD_TOKEN", "").strip(),
            gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
            gemini_model=os.getenv("GEMINI_MODEL", cls.gemini_model).strip(),
            code_channel_id=int(channel_id) if channel_id else None,
            queue_size=positive_int("AUDIO_QUEUE_SIZE", 20),
            max_audio_seconds=positive_int("MAX_AUDIO_SECONDS", 900),
            max_download_bytes=positive_int("MAX_DOWNLOAD_MB", 50) * 1024 * 1024,
            max_video_bytes=positive_int("MAX_VIDEO_MB", 10) * 1024 * 1024,
            download_timeout=positive_int("DOWNLOAD_TIMEOUT", 90),
            chat_idle_timeout=positive_int("CHAT_IDLE_TIMEOUT", 120),
            chat_request_timeout=positive_int("CHAT_REQUEST_TIMEOUT", 45),
            chat_max_turns=positive_int("CHAT_MAX_TURNS", 20),
            chat_max_sessions=positive_int("CHAT_MAX_SESSIONS", 20),
        )
