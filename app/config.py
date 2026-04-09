MAX_FILE_SIZE = 200 * 1024 * 1024 

PDF_PAGES_LIMIT = 21
PDF_SIZE_LIMIT = 50
DPI = 300

CACHE_MAXSIZE = 100

OLLAMA_URL = "http://ollama:11434/api/generate"
OLLAMA_VISION_MODEL= "ministral-3:14b"

IMAGE_PROMPT = """
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
"""

SUPPORTED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".pptx", ".docx", ".doc", ".emf"}

MIME_TO_EXT = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpeg",
    "image/png": ".png",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/msword": ".doc",
    "application/x-emf": ".emf",
    "image/emf": ".emf",
}