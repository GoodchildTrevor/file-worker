import logging
import os
from pathlib import Path
import tempfile


from fastapi import FastAPI, Form, UploadFile, File, HTTPException


from app.config import get_settings
from app.utils import FileWorker


app = FastAPI()
settings = get_settings()


LOG_PATH = "fileworker.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)



@app.post("/filework", response_model=str)
async def create_item(
    file: UploadFile = File(...),
    language: str = Form(None),
    diarization: bool = Form(False),
    num_speakers: int | None = Form(None),
) -> str:
    """
    Accepts a file (PDF, image, PPTX, audio or video), validates its type,
    saves it temporarily, and passes it to the FileWorker for text extraction.

    :param file: Uploaded file via multipart/form-data.
    :param num_speakers: Ожидаемое число спикеров. None -> транскрайбер
        (whisperx/pyannote) определит их автоматически.
    :return: Extracted text from the document.
    :raises HTTPException: If file type is unsupported or processing fails.
    """
    diarization_params = None
    if diarization:
        diarization_params = {"diarization": diarization, "language": language}
        # ВАЖНО: httpx сериализует params={"key": None} как "key=" (пустую строку),
        # а не отбрасывает параметр вовсе. FastAPI на стороне /transcriber
        # не может распарсить "" как int -> 422 Unprocessable Entity.
        # Поэтому num_participants добавляем в словарь только если он реально задан.
        if num_speakers is not None:
            diarization_params["num_participants"] = num_speakers

    mime_type = file.content_type
    ext_from_mime = settings.MIME_TO_EXT.get(mime_type)
    ext_from_name = Path(file.filename).suffix.lower()

    file_ext = ext_from_mime if ext_from_mime in settings.SUPPORTED_EXTENSIONS else ext_from_name

    if file_ext not in settings.SUPPORTED_EXTENSIONS:
        logger.error(f"Unsupported file format {file_ext}. Supported: {', '.join(settings.SUPPORTED_EXTENSIONS)}")
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format {file_ext}. Supported: {', '.join(settings.SUPPORTED_EXTENSIONS)}"
        )

    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read uploaded file: {str(e)}")

    if len(content) > settings.MAX_FILE_SIZE:
        logger.error(f"File too large. Maximum size is {settings.MAX_FILE_SIZE/1024/1024}MB")
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {settings.MAX_FILE_SIZE/1024/1024}MB"
        )

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {str(e)}")

    try:
        fileworker = FileWorker(
            logger=logger,
            file=tmp_file_path,
            file_fmt=file_ext,
            settings=settings,
            diarization_params=diarization_params
        )
        extracted_text = await fileworker.text_extractor()
    except Exception as e:
        logger.error(f"Text extraction failed: {str(e)}")
        if os.path.exists(tmp_file_path):
            os.unlink(tmp_file_path)
        raise HTTPException(status_code=500, detail=f"Text extraction failed: {str(e)}")

    if os.path.exists(tmp_file_path):
        os.unlink(tmp_file_path)

    return extracted_text



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8055)
