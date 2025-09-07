# tests/conftest.py
from __future__ import annotations
import io
import shutil
import tempfile
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core import config

import fitz  # PyMuPDF
import docx

# --------------------------------------------------------------------
# Fixtures for temporary DATA_DIR so tests don't pollute real data dir
# --------------------------------------------------------------------
@pytest.fixture(scope="session")
def tmp_data_dir() -> Generator[str, None, None]:
    d = tempfile.mkdtemp(prefix="test-data-")
    yield d
    shutil.rmtree(d, ignore_errors=True)

@pytest.fixture(autouse=True, scope="session")
def patch_data_dir(tmp_data_dir):
    # Override app's DATA_DIR during tests
    config.DATA_DIR = tmp_data_dir

# --------------------------------------------------------------------
# FastAPI test client available as fixture `client`
# --------------------------------------------------------------------
@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)

# --------------------------------------------------------------------
# Helpers to create in-memory sample PDF and DOCX
# --------------------------------------------------------------------
def _pdf_bytes(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 100), text, fontsize=12)
    data = doc.tobytes()
    doc.close()
    return data

def _docx_bytes(text: str) -> bytes:
    d = docx.Document()
    for p in text.split("\n\n"):
        d.add_paragraph(p)
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()

@pytest.fixture
def sample_pdf_bytes() -> bytes:
    return _pdf_bytes("This is a smaple sentence with a typo.\nAnother line here.")

@pytest.fixture
def sample_docx_bytes() -> bytes:
    return _docx_bytes("This is a smaple sentence with a typo.\n\nAnother paragraph here.")

# --------------------------------------------------------------------
# Optional stubs: avoid requiring Java/LanguageTool during tests
# --------------------------------------------------------------------
@pytest.fixture(autouse=True)
def stub_language_tool(monkeypatch):
    from app.services import analyze as analyze_mod
    from app.services import revise as revise_mod

    # Fake issue match
    class _FakeMatch:
        def __init__(self, offset=10, length=6, msg="Possible typo"):
            self.offset = offset
            self.errorLength = length
            self.message = msg
            self.ruleId = "FAKE_RULE"
            self.ruleIssueType = "Grammar"
            self.replacements = []

    # Fake LanguageTool replacement
    class _FakeLT:
        def check(self, text: str):
            return [_FakeMatch()] if "smaple" in text else []

    if hasattr(analyze_mod, "LanguageTool"):
        monkeypatch.setattr(analyze_mod, "LanguageTool", lambda *a, **k: _FakeLT())
        if hasattr(analyze_mod, "_LT"):
            analyze_mod._LT = None

    # Stub auto_correct_text in revise
    def _fake_auto_correct(paragraphs: list[str]) -> list[str]:
        return [p.replace("smaple", "sample") for p in paragraphs]

    if hasattr(revise_mod, "auto_correct_text"):
        monkeypatch.setattr(revise_mod, "auto_correct_text", _fake_auto_correct)
