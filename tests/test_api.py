import io, os
import fitz
import docx
import pytest
from fastapi.testclient import TestClient

# import the FastAPI app
from app.main import app
from app.core.config import DATA_DIR

client = TestClient(app)

def _make_docx_bytes(text="Hello world."):
    d = docx.Document()
    d.add_paragraph(text)
    bio = io.BytesIO()
    d.save(bio)
    bio.seek(0)
    return bio.getvalue()

def _make_pdf_bytes(text="Hello PDF."):
    doc = fitz.open()
    page = doc.new_page()
    rect = fitz.Rect(72, 72, 540, 720)  # 1-inch margins letter-ish
    page.insert_textbox(rect, text)
    bio = io.BytesIO()
    doc.save(bio)
    doc.close()
    bio.seek(0)
    return bio.getvalue()

def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

@pytest.mark.parametrize("kind", ["docx", "pdf"])
def test_upload_and_analyze(kind, tmp_path):
    # generate a tiny file in-memory
    if kind == "docx":
        bytes_ = _make_docx_bytes("This is a simple sentence. Another one.")
        content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        name = "t.docx"
    else:
        bytes_ = _make_pdf_bytes("This is a simple sentence.\nAnother one.")
        content_type = "application/pdf"
        name = "t.pdf"

    files = {"file": (name, bytes_, content_type)}
    r = client.post("/upload", files=files)
    assert r.status_code == 200
    data = r.json()
    doc_id = data["doc_id"]

    # analyze
    r2 = client.post(f"/analyze?doc_id={doc_id}")
    assert r2.status_code == 200
    report = r2.json()
    assert "paragraph_count" in report or "issues" in report or "summary" in report

    # revise to txt (lightweight, always available)
    r3 = client.post(f"/revise?doc_id={doc_id}&fmt=txt")
    assert r3.status_code == 200
    out = r3.json()["corrected_path"]
    assert os.path.isfile(out)

    # download the corrected txt
    filename = os.path.basename(out)
    r4 = client.get(f"/download?doc_id={doc_id}&filename={filename}")
    assert r4.status_code == 200
    assert r4.content  # non-empty
