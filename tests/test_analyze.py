# tests/test_analyze.py
import io

def _upload_pdf(client, pdf_bytes):
    files = {"file": ("in.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    r = client.post("/upload", files=files)
    assert r.status_code == 200, r.text
    return r.json()["doc_id"]


def test_analyze_pdf(client, sample_pdf_bytes):
    doc_id = _upload_pdf(client, sample_pdf_bytes)
    r = client.post(f"/analyze?doc_id={doc_id}")
    assert r.status_code == 200, r.text
    report = r.json()

    # Stable fields we expect
    assert "doc_id" in report
    assert "score" in report

    # Issues list should exist
    assert "issues" in report and isinstance(report["issues"], list)

    # Readability may be named differently or omitted
    read_metrics = report.get("readability") or report.get("readability_metrics")
    if read_metrics is not None:
        assert isinstance(read_metrics, dict)

    # Some backends return a top-level 'totals' dict; treat as optional
    totals = report.get("totals")
    if totals is not None:
        assert isinstance(totals, dict)


def test_analyze_summary_only(client, sample_pdf_bytes):
    doc_id = _upload_pdf(client, sample_pdf_bytes)
    r = client.post(f"/analyze?doc_id={doc_id}&summary_only=true")
    assert r.status_code == 200, r.text
    payload = r.json()

    # Stable fields we expect
    assert "doc_id" in payload
    assert "score" in payload

    # Readability may or may not be returned
    read_metrics = payload.get("readability") or payload.get("readability_metrics")
    if read_metrics is not None:
        assert isinstance(read_metrics, dict)

    # totals is optional; validate type only if present
    totals = payload.get("totals")
    if totals is not None:
        assert isinstance(totals, dict)

    # Issues may be included or omitted in summary-only mode
    if "issues" in payload:
        assert isinstance(payload["issues"], list)
