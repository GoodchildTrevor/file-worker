"""HTTP-level tests for the FastAPI endpoints in app.main."""

from fastapi.testclient import TestClient

import app.main as main

client = TestClient(main.app)


class FakeWorker:
    """Stand-in for FileWorker that records its constructor arguments."""

    captured: dict = {}

    def __init__(self, **kwargs):
        FakeWorker.captured = dict(kwargs)

    async def text_extractor(self) -> str:
        return "ok"


# ---------------------------------------------------------------------------
# GET /files/{folder}/{filename}
# ---------------------------------------------------------------------------

class TestServeFile:
    def test_rejects_dotdot_folder(self):
        response = client.get("/files/%2e%2e/x.docx")
        assert response.status_code == 400

    def test_rejects_dotdot_in_filename(self):
        response = client.get("/files/shared/a..b.docx")
        assert response.status_code == 400

    def test_unknown_file_is_404(self):
        response = client.get("/files/shared/missing.docx")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /filework
# ---------------------------------------------------------------------------

class TestFilework:
    def test_rejects_unsupported_extension(self):
        response = client.post(
            "/filework",
            files={"file": ("a.exe", b"x", "application/octet-stream")},
        )
        assert response.status_code == 400

    def test_rejects_oversized_file(self, monkeypatch):
        monkeypatch.setattr(main.settings, "MAX_FILE_SIZE", 10)
        response = client.post(
            "/filework",
            files={"file": ("a.pdf", b"x" * 11, "application/pdf")},
        )
        assert response.status_code == 413

    def test_accepts_file_at_limit(self, monkeypatch):
        monkeypatch.setattr(main.settings, "MAX_FILE_SIZE", 10)
        monkeypatch.setattr(main, "FileWorker", FakeWorker)
        response = client.post(
            "/filework",
            files={"file": ("a.pdf", b"x" * 10, "application/pdf")},
        )
        assert response.status_code == 200
        assert response.json() == "ok"

    def test_forwards_language_without_diarization(self, monkeypatch):
        monkeypatch.setattr(main, "FileWorker", FakeWorker)
        response = client.post(
            "/filework",
            data={"language": "en"},
            files={"file": ("a.mp3", b"abc", "audio/mpeg")},
        )
        assert response.status_code == 200
        assert FakeWorker.captured["file_fmt"] == ".mp3"
        assert FakeWorker.captured["diarization_params"] == {"language": "en"}

    def test_diarization_params_include_speakers(self, monkeypatch):
        monkeypatch.setattr(main, "FileWorker", FakeWorker)
        response = client.post(
            "/filework",
            data={"diarization": "true", "num_speakers": "2", "language": "ru"},
            files={"file": ("a.mp4", b"abc", "video/mp4")},
        )
        assert response.status_code == 200
        assert FakeWorker.captured["diarization_params"] == {
            "language": "ru",
            "diarization": True,
            "num_participants": 2,
        }

    def test_no_params_gives_empty_dict(self, monkeypatch):
        monkeypatch.setattr(main, "FileWorker", FakeWorker)
        response = client.post(
            "/filework",
            files={"file": ("a.wav", b"abc", "audio/wav")},
        )
        assert response.status_code == 200
        assert FakeWorker.captured["diarization_params"] == {}

    def test_extraction_failure_is_500(self, monkeypatch):
        class FailingWorker(FakeWorker):
            async def text_extractor(self) -> str:
                raise RuntimeError("boom")

        monkeypatch.setattr(main, "FileWorker", FailingWorker)
        response = client.post(
            "/filework",
            files={"file": ("a.docx", b"abc", "application/octet-stream")},
        )
        assert response.status_code == 500
        assert "boom" in response.json()["detail"]
