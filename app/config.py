import os
from functools import lru_cache
from dotenv import load_dotenv

from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    MAX_FILE_SIZE: int = 200 * 1024 * 1024

    PDF_PAGES_LIMIT: int = 21
    DPI: int = 300

    CACHE_MAXSIZE: int = 100

    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://ollama:11434/api/generate")
    OLLAMA_VISION_MODEL: str = os.getenv("OLLAMA_VISION_MODEL", "ministral-3:14b")

    IMAGE_PROMPT: str = os.getenv("IMAGE_PROMPT", """
        Extract ALL text from this document image.
        Preserve exact spelling, punctuation, and formatting.
        Return ONLY the text, without comments.
        If there are tables, present them in the following format:
        [
            'Header1': 'Value from row 1' | 'Header2': 'Value from row 1',
            'Header1': 'Value from row 2' | 'Header2': 'Value from row 2',
            'Header1': 'Value from row 3' | 'Header2': 'Value from row 3'
        ]
        If there is a diagram, return its step-by-step description:
            1. Step 1
            2. Step 2
            3. Step 3
    """)

    SUPPORTED_EXTENSIONS: set = {
        ".pdf", ".jpg", ".jpeg", ".png", ".pptx", ".docx", ".doc", ".emf",
        ".mp3", ".wav", ".flac", ".ogg", ".webm",
        ".mp4", ".mov", ".mkv", ".avi",
    }

    MIME_TO_EXT: dict = {
        "application/pdf": ".pdf",
        "image/jpeg": ".jpeg",
        "image/png": ".png",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "application/msword": ".doc",
        "application/x-emf": ".emf",
        "image/emf": ".emf",

        # Audio
        "audio/mpeg": ".mp3",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/flac": ".flac",
        "audio/ogg": ".ogg",
        "audio/x-flac": ".flac",
        "audio/webm": ".webm",

        # Video
        "video/mp4": ".mp4",
        "video/webm": ".webm",
        "video/quicktime": ".mov",
        "video/x-matroska": ".mkv",
        "video/x-msvideo": ".avi",
    }
    WHISPER_API_URL: str | None = None
    WHISPER_TIMEOUT: int = 300


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
