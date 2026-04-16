# file-worker

A FastAPI microservice for extracting text from various file formats — documents, images, presentations, audio, and video. Uses OCR, Ollama vision models, and Whisper for transcription.

## Features

- **Documents**: PDF, DOCX, DOC, PPTX
- **Images**: JPG, JPEG, PNG, EMF — text extraction via Tesseract OCR and/or Ollama vision model
- **Audio**: MP3, WAV, FLAC, OGG, WebM — transcription via Whisper API
- **Video**: MP4, WebM, MOV, MKV, AVI — audio extraction + Whisper transcription
- Speaker diarization support for audio/video files
- File size limit: 200 MB by default
- Configurable via `.env`

## API

### `POST /filework`

Accepts a file via `multipart/form-data` and returns extracted text as a plain string.

**Form fields:**

| Field | Type | Required | Description |
|---|---|---|---|
| `file` | file | ✅ | File to process |
| `language` | string | ❌ | Language hint for transcription (e.g. `ru`, `en`) |
| `diarization` | bool | ❌ | Enable speaker diarization (default: `false`) |
| `num_speakers` | int | ❌ | Number of speakers for diarization (default: `1`) |

**Example request:**

```bash
curl -X POST http://localhost:8055/filework \
  -F "file=@document.pdf"
```

**Example with diarization:**

```bash
curl -X POST http://localhost:8055/filework \
  -F "file=@meeting.mp4" \
  -F "diarization=true" \
  -F "num_speakers=3" \
  -F "language=en"
```

## Configuration

Create a `.env` file in the project root. All variables are optional and fall back to defaults.

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_URL` | `http://ollama:11434/api/generate` | Ollama API endpoint |
| `OLLAMA_VISION_MODEL` | `ministral-3:14b` | Vision model for image OCR |
| `WHISPER_API_URL` | — | Whisper transcription API URL (required for audio/video) |
| `WHISPER_TIMEOUT` | `300` | Whisper request timeout (seconds) |
| `MAX_FILE_SIZE` | `209715200` (200 MB) | Max upload size in bytes |
| `PDF_PAGES_LIMIT` | `21` | Max PDF pages to process |
| `DPI` | `300` | DPI for PDF-to-image rendering |
| `IMAGE_PROMPT` | *(built-in)* | Prompt sent to vision model for image OCR |

## Running

### Docker Compose (recommended)

```bash
cp .env.example .env  # edit as needed
docker compose up -d
```

The service runs on port **8055** by default.

### Local development

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8055 --reload
```

**System dependencies required for local run:**

```bash
# Ubuntu/Debian
apt install tesseract-ocr libtesseract-dev poppler-utils imagemagick unoconv libreoffice
```

## Project Structure

```
file-worker/
├── app/
│   ├── main.py       # FastAPI app and /filework endpoint
│   ├── config.py     # Settings via pydantic-settings
│   └── utils.py      # FileWorker class with all extraction logic
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## License

[GPL-2.0](LICENSE)
