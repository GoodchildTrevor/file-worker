import asyncio
import html
import logging
import os
import re
import subprocess
import tempfile
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional
from urllib.parse import quote


from fastapi import FastAPI, Form, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


from app.config import get_settings
from app.utils import FileWorker



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


EXPORT_DIR = os.path.realpath((os.getenv("FILE_EXPORT_DIR") or "/output").rstrip("/"))
os.makedirs(EXPORT_DIR, exist_ok=True)

# Публичный адрес, под которым nginx проксирует этот сервис наружу
# (должен включать тот же префикс пути, что и FILE_ROUTE_PREFIX ниже).
PUBLIC_BASE_URL = os.getenv("FILE_EXPORT_BASE_URL", "https://your-domain.example/files").rstrip("/")

# Префикс пути для раздачи файлов внутри самого сервиса.
# ВАЖНО: должен буквально совпадать с тем, что настроено в nginx
# (location + proxy_pass) и с хвостом FILE_EXPORT_BASE_URL — иначе 404.
FILE_ROUTE_PREFIX = "/" + os.getenv("FILE_ROUTE_PREFIX", "files").strip("/")

FILE_TTL_DAYS = float(os.getenv("FILE_TTL_DAYS", "7"))
FILE_TTL_SECONDS = FILE_TTL_DAYS * 24 * 60 * 60
CLEANUP_INTERVAL_SECONDS = float(os.getenv("FILE_CLEANUP_INTERVAL_SECONDS", str(6 * 60 * 60)))


# Ловит и канон, и покалеченные маркеры в одном тексте:
# **SPEAKER_00**:, SPEAKER_00:, *SPEAKER_00**:, **SPEAKER_00*:
SPEAKER_MARKER_PATTERN = re.compile(
    r"(?<!\w)\*{0,2}\s*(SPEAKER_\d+)\s*\*{0,2}\s*:\s*",
    flags=re.IGNORECASE,
)

# Литералы \n \r \t, которые приехали как текст, а не как переводы строк.
LITERAL_ESCAPE_PATTERN = re.compile(r"\\[nrt]")


def _unescape_transcript(text: str) -> str:
    """
    Клиент иногда присылает уже сериализованные '\\n\\n*' вместо абзацев.
    Превращаем их в настоящие переводы строк и вычищаем хвосты markdown.
    """
    def _replace(match: re.Match[str]) -> str:
        return {"n": "\n", "r": "\r", "t": "\t"}[match.group(0)[1]]

    text = LITERAL_ESCAPE_PATTERN.sub(_replace, text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # одиночные '*' / '**' на своей строке — объедки от **SPEAKER_00**
    text = re.sub(r"^[ \t]*\*+[ \t]*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def _clean_speech(text: str) -> str:
    text = text.strip(' \t\r\n“"”*')
    text = re.sub(r"^[ \t]*\*+[ \t]*", "", text)
    text = re.sub(r"[ \t]*\*+[ \t]*$", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _split_transcript_turns(text: str) -> list[tuple[Optional[str], str]]:
    text = _unescape_transcript(text)
    matches = list(SPEAKER_MARKER_PATTERN.finditer(text))
    if not matches:
        stripped = _clean_speech(text)
        return [(None, stripped)] if stripped else []

    turns: list[tuple[Optional[str], str]] = []
    preamble = _clean_speech(text[:matches[0].start()])
    if preamble:
        turns.append((None, preamble))

    for i, match in enumerate(matches):
        label = match.group(1).upper()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        remainder = _clean_speech(text[start:end])
        if remainder or label:
            turns.append((label, remainder))

    return turns


def transcript_to_html(title: str, text: str) -> str:
    """
    HTML, не Markdown. Pandoc больше не видит _ и * в SPEAKER_00,
    поэтому не склеивает весь файл в один абзац.
    """
    parts = [f"<h1>{html.escape(title)}</h1>"]

    for label, remainder in _split_transcript_turns(text):
        body = html.escape(remainder).replace("\n", "<br/>\n")
        if label:
            parts.append(
                f"<p><strong>{html.escape(label)}:</strong> {body}</p>"
            )
        elif body:
            parts.append(f"<p>{body}</p>")

    return "\n".join(parts)


def _cleanup_expired_files() -> None:
    now = time.time()
    removed_files = 0

    for root, dirs, files in os.walk(EXPORT_DIR, topdown=False):
        for filename in files:
            file_path = os.path.join(root, filename)
            try:
                mtime = os.path.getmtime(file_path)
            except OSError:
                continue

            if now - mtime > FILE_TTL_SECONDS:
                try:
                    os.remove(file_path)
                    removed_files += 1
                except OSError as e:
                    logger.warning(f"Failed to remove expired file {file_path}: {e}")

        if root != EXPORT_DIR and not os.listdir(root):
            try:
                os.rmdir(root)
            except OSError:
                pass

    if removed_files:
        logger.info(f"Cleanup: removed {removed_files} expired file(s)")


async def _cleanup_loop() -> None:
    while True:
        try:
            _cleanup_expired_files()
        except Exception as e:
            logger.error(f"Cleanup loop error: {e}")
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(_: FastAPI):
    task = asyncio.create_task(_cleanup_loop())
    try:
        yield
    finally:
        task.cancel()


app = FastAPI(lifespan=lifespan)


def _safe_folder_name(raw: str) -> str:
    return str(raw).replace("/", "_").replace("\\", "_").replace("..", "_")


class ExportDocxRequest(BaseModel):
    text: str
    filename_base: str = "transcription"
    folder: str = "shared"


class ExportDocxResponse(BaseModel):
    link: str


@app.post("/export/docx", response_model=ExportDocxResponse)
async def export_docx(payload: ExportDocxRequest) -> ExportDocxResponse:
    """
    Режет диаризацию на абзацы и собирает .docx через pandoc из HTML.
    Markdown намеренно не используется: _ в SPEAKER_00 ломает разметку.
    """
    folder = _safe_folder_name(payload.folder)
    target_dir = os.path.join(EXPORT_DIR, folder)
    os.makedirs(target_dir, exist_ok=True)

    unique_suffix = uuid.uuid4().hex[:8]
    safe_base = _safe_folder_name(payload.filename_base) or "transcription"
    filename = f"{safe_base}_{unique_suffix}.docx"
    file_path = os.path.join(target_dir, filename)

    turns = _split_transcript_turns(payload.text)
    html_content = transcript_to_html(safe_base, payload.text)
    logger.info(
        "DOCX export: source_length=%d turns=%d speakers=%s",
        len(payload.text),
        len(turns),
        [label for label, _ in turns if label],
    )

    try:
        process = subprocess.run(
            ["pandoc", "-f", "html", "-t", "docx", "-o", file_path],
            input=html_content.encode("utf-8"),
            capture_output=True,
            timeout=30,
        )
        if process.returncode != 0:
            raise RuntimeError(process.stderr.decode(errors="ignore"))
    except Exception as e:
        logger.error(f"Pandoc conversion failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to build docx: {e}")

    encoded_folder = quote(folder, safe="")
    encoded_filename = quote(filename, safe="")
    link = f"{PUBLIC_BASE_URL}/{encoded_folder}/{encoded_filename}"

    return ExportDocxResponse(link=link)


@app.get(FILE_ROUTE_PREFIX + "/{folder_name}/{filename}")
async def serve_file(folder_name: str, filename: str):
    if ".." in folder_name or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid path")

    file_path = os.path.realpath(os.path.join(EXPORT_DIR, folder_name, filename))
    try:
        Path(file_path).relative_to(EXPORT_DIR)
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    for _ in range(10):
        if os.path.isfile(file_path):
            break
        await asyncio.sleep(0.5)
    else:
        raise HTTPException(status_code=404, detail="File not found")

    encoded = quote(filename, safe="")
    content_disposition = f"attachment; filename*=UTF-8''{encoded}"

    return FileResponse(
        path=file_path,
        media_type="application/octet-stream",
        headers={"Content-Disposition": content_disposition},
    )


app.mount(FILE_ROUTE_PREFIX, StaticFiles(directory=EXPORT_DIR), name="exported_files")


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
