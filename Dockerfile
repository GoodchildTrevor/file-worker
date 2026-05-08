FROM python:3.13-slim

RUN apt update && apt install -y \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
    imagemagick \
    libreoffice \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8055"]
