"""Unit tests for FileWorker behaviour that needs no external services."""

import asyncio
import logging

import pytest

import app.main as main
from app.utils import OLLAMA_ERROR_PREFIX, FileWorker


def make_worker(file_fmt: str = ".mp3", diarization_params: dict | None = None) -> FileWorker:
    return FileWorker(
        logger=logging.getLogger("test"),
        file="does-not-exist" + file_fmt,
        file_fmt=file_fmt,
        settings=main.settings,
        diarization_params=diarization_params if diarization_params is not None else {},
    )


# ---------------------------------------------------------------------------
# Result cache
# ---------------------------------------------------------------------------

class TestCache:
    def test_cache_is_shared_across_instances(self):
        first = make_worker()
        second = make_worker()
        first._set_cached_text("hash-shared", ".pdf", "cached text")
        try:
            assert second._get_cached_text("hash-shared", ".pdf") == "cached text"
        finally:
            FileWorker._document_cache.pop("hash-shared:.pdf", None)

    def test_cache_miss_returns_none(self):
        assert make_worker()._get_cached_text("no-such-hash", ".pdf") is None


# ---------------------------------------------------------------------------
# Media transcription
# ---------------------------------------------------------------------------

class TestMedia:
    def test_missing_whisper_url_raises(self, monkeypatch):
        monkeypatch.setattr(main.settings, "WHISPER_API_URL", None)
        worker = make_worker()
        with pytest.raises(RuntimeError, match="WHISPER_API_URL"):
            asyncio.run(worker._extract_text_from_media())

    def test_segments_without_diarization_have_no_labels(self):
        worker = make_worker()
        segments = [
            {"speaker": "SPEAKER_00", "text": "Hi"},
            {"speaker": "SPEAKER_01", "text": "Hello"},
        ]
        assert worker._convert_segments_to_text(segments, diarization=False) == "Hi\n\nHello"

    def test_segments_with_diarization_have_labels(self):
        worker = make_worker()
        segments = [
            {"speaker": "SPEAKER_00", "text": "Hi"},
            {"speaker": "SPEAKER_00", "text": "there"},
            {"speaker": "SPEAKER_01", "text": "Hello"},
        ]
        assert worker._convert_segments_to_text(segments, diarization=True) == (
            "**SPEAKER_00**: Hi there\n\n**SPEAKER_01**: Hello"
        )


# ---------------------------------------------------------------------------
# Ollama error placeholders
# ---------------------------------------------------------------------------

class TestOllamaPlaceholders:
    def test_missing_image_returns_error_prefix(self):
        worker = make_worker(".png")
        result = asyncio.run(worker._send_image_to_ollama("no-such-image.png"))
        assert result.startswith(OLLAMA_ERROR_PREFIX)

    def test_image_handler_passes_error_through(self):
        worker = make_worker(".png")
        result = asyncio.run(worker._extract_text_from_image())
        assert result.startswith(OLLAMA_ERROR_PREFIX)
        assert "IMAGE ANALYSIS" not in result
