import io

def test_upload_pdf(client, sample_pdf_bytes):
    files = {"file": ("sample.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")}
    r = client.post("/upload", files=files)
    assert r.status_code == 200, r.text
    payload = r.json()
    assert "doc_id" in payload

def test_upload_docx(client, sample_docx_bytes):
    files = {"file": ("sample.docx", io.BytesIO(sample_docx_bytes),
                      "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    r = client.post("/upload", files=files)
    assert r.status_code == 200, r.text
    assert "doc_id" in r.json()

def test_upload_wrong_ext(client, sample_pdf_bytes):
    # send .txt but with pdf mime → should be blocked by extension guard
    files = {"file": ("bad.txt", io.BytesIO(sample_pdf_bytes), "text/plain")}
    r = client.post("/upload", files=files)
    assert r.status_code in (400, 415)
