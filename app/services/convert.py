# app/services/convert.py
import tempfile
from pathlib import Path
import subprocess

class ConvertError(RuntimeError):
    ...

def _run(cmd: list[str]) -> None:
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        raise ConvertError(
            f"Command failed ({p.returncode}): {' '.join(cmd)}\nSTDERR:\n{p.stderr}"
        )

def pdf_to_docx(src_pdf: str) -> str:
    src = Path(src_pdf).resolve()
    outdir = Path(tempfile.mkdtemp())
    cmd = [
        "soffice", "--headless",
        "--infilter=writer_pdf_import",
        "--convert-to", "docx",
        "--outdir", str(outdir),
        str(src),
    ]
    _run(cmd)
    out = outdir / (src.stem + ".docx")
    if not out.exists():
        # fallback to first docx in folder
        docs = list(outdir.glob("*.docx"))
        if not docs:
            raise ConvertError("LibreOffice did not produce a DOCX")
        out = docs[0]
    return str(out)

def docx_to_pdf(src_docx: str) -> str:
    src = Path(src_docx).resolve()
    outdir = Path(tempfile.mkdtemp())
    cmd = ["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(outdir), str(src)]
    _run(cmd)
    out = outdir / (src.stem + ".pdf")
    if not out.exists():
        pdfs = list(outdir.glob("*.pdf"))
        if not pdfs:
            raise ConvertError("LibreOffice did not produce a PDF")
        out = pdfs[0]
    return str(out)
