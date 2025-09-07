# tests/test_revise.py
import io
import os
import fitz


def _upload(client, filename: str, b: bytes, mime: str) -> str:
    files = {"file": (filename, io.BytesIO(b), mime)}
    r = client.post("/upload", files=files)
    assert r.status_code == 200, r.text
    return r.json()["doc_id"]


def _get_output_path(payload: dict) -> str:
    # accept several common shapes, including corrected_path
    for key in ("path", "file", "filepath", "out_path", "output_path", "corrected_path"):
        if key in payload and isinstance(payload[key], str):
            return payload[key]
    if "output" in payload and isinstance(payload["output"], dict):
        for key in ("path", "file", "filepath", "corrected_path"):
            if key in payload["output"] and isinstance(payload["output"][key], str):
                return payload["output"][key]
    raise KeyError(f"No output file path field found in response: {payload}")


def _read_docx_text(path: str) -> str:
    import docx
    d = docx.Document(path)
    return "\n".join(p.text for p in d.paragraphs)


def test_revise_to_docx(client, sample_docx_bytes):
    doc_id = _upload(
        client,
        "in.docx",
        sample_docx_bytes,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    r = client.post(f"/revise?doc_id={doc_id}&fmt=docx")
    assert r.status_code == 200, r.text
    out = _get_output_path(r.json())
    assert out.endswith(".docx")
    text = _read_docx_text(out)
    # check that our fake correction worked
    assert "smaple" not in text
    assert "sample" in text


def test_revise_to_pdf(client, sample_pdf_bytes):
    doc_id = _upload(client, "in.pdf", sample_pdf_bytes, "application/pdf")
    r = client.post(f"/revise?doc_id={doc_id}&fmt=pdf")
    assert r.status_code == 200, r.text
    out = _get_output_path(r.json())
    assert out.endswith(".pdf")
    assert os.path.isfile(out)
    with fitz.open(out) as doc:
        assert doc.page_count >= 1
        txt = doc[0].get_text()
        assert "sample" in txt or "Sample" in txt
