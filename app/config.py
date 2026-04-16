import os
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

    MAX_FILE_SIZE = 200 * 1024 * 1024 

    PDF_PAGES_LIMIT = 21
    DPI = 300

    CACHE_MAXSIZE = 100

    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434/api/generate")
    OLLAMA_VISION_MODEL= os.getenv("OLLAMA_VISION_MODEL", "ministral-3:14b")

    IMAGE_PROMPT = os.getenv("IMAGE_PROMPT", """
        Извлеки ВЕСЬ текст с этого изображения документа. 
        Сохрани точную орфографию, пунктуацию и форматирование.
        Верни ТОЛЬКО текст, без комментариев.
        Если есть таблицы - представь их в следующем виде
        [
            'Загловок1': 'Значение из строки 1' | 'Загловок2': 'Значение из строки 1',
            'Загловок1': 'Значение из строки 2' | 'Загловок2': 'Значение из строки 2',
            'Загловок1': 'Значение из строки 3' | 'Загловок2': 'Значение из строки 3'
        ]    
        Если есть схема, то верни её пошаговое описание в виде
            1. Шаг 1
            2. Шаг 2
            3. Шаг 3
    """)

    SUPPORTED_EXTENSIONS = {
        ".pdf", ".jpg", ".jpeg", ".png", ".pptx", ".docx", ".doc", ".emf",
        "audio/mpeg", "audio/wav", "audio/x-wav", "audio/flac", "audio/ogg", "audio/x-flac", "audio/webm",
        "video/mp4", "video/webm", "video/quicktime", "video/x-matroska", "video/x-msvideo",   
    }

    MIME_TO_EXT = {
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
    WHISPER_API_URL = os.getenv("WHISPER_API_URL")
    WHISPER_TIMEOUT = os.getenv("WHISPER_TIMEOUT", 300)

def get_settings() -> Settings:
    return Settings()
