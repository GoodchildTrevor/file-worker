from fastapi import FastAPI, UploadFile, File, HTTPException
import logging
import os
from pathlib import Path
import tempfile

from app.config import get_settings
from app.utils import FileWorker

app = FastAPI()
settings= get_settings()

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
async def create_item(file: UploadFile = File(...)) -> str:
    """
    Accepts a file (PDF, image, or PPTX), validates its type,
    saves it temporarily, and passes it to the `foo` function for text extraction.

    :param file: Uploaded file via multipart/form-data.
    :return: Extracted text from the document.
    :raises HTTPException: If file type is unsupported or processing fails.
    """
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
            format=file_ext
        )
        extracted_text = fileworker.text_extractor()
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
