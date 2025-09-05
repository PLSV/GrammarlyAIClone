from __future__ import annotations
import os, shutil
from typing import List, Literal
from language_tool_python import LanguageTool
import docx
from app.services.extract import extract_text
import fitz

# reuse a singleton LT instance to avoid repeated startups
_LT = None
def LT():
    global _LT
    if _LT is None:
        _LT = LanguageTool("en-US")  # switch to en-GB if desired
    return _LT

def _simple_fixes(text: str) -> str:
    """
    Deterministic, safe edits (no style opinions).
    - Normalize whitespace
    - Normalize curly quotes to straight quotes
    """
    # normalize whitespace: collapse multiple spaces
    while "  " in text:
        text = text.replace("  ", " ")
    # normalize quotes
    text = (text
            .replace("“", "\"").replace("”", "\"")
            .replace("‘", "'").replace("’", "'"))
    # trim trailing spaces on lines
    lines = [ln.rstrip() for ln in text.splitlines()]
    return "\n".join(lines).strip()

def auto_correct_text(paragraphs: List[str]) -> List[str]:
    """
    Apply simple fixes + LanguageTool's automatic corrections.
    """
    fixed: List[str] = []
    for p in paragraphs:
        if not p.strip():
            fixed.append(p)
            continue
        base = _simple_fixes(p)
        corrected = LT().correct(base)  # LT chooses first suggestion per match
        fixed.append(corrected)
    return fixed

def write_docx(paragraphs: List[str], out_path: str) -> str:
    d = docx.Document()
    for p in paragraphs:
        d.add_paragraph(p)
    d.save(out_path)
    return out_path

def write_txt(paragraphs: List[str], out_path: str) -> str:
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(paragraphs) + "\n")
    return out_path

def revise_document(in_path: str, out_dir: str, fmt: Literal["docx", "txt", "pdf"]="docx") -> str:
    """
    Extract → fix → write corrected output in requested format (docx/txt/pdf).
    If input is PDF and the corrected text equals the original, copy the original PDF.
    """
    paragraphs = extract_text(in_path)
    # if extraction produced nothing, just copy original for PDF requests
    ext = os.path.splitext(in_path)[1].lower()
    os.makedirs(out_dir, exist_ok=True)

    if not any(p.strip() for p in paragraphs):
        if fmt == "pdf" and ext == ".pdf":
            out_path = os.path.join(out_dir, "corrected.pdf")
            shutil.copy2(in_path, out_path)
            return out_path
        # produce an empty-but-valid docx/txt
        corrected: list[str] = []
    else:
        corrected = auto_correct_text(paragraphs)

    original_text = "\n\n".join(paragraphs)
    corrected_text = "\n\n".join(corrected)

    # If the doc is a PDF and there are no textual changes, copy original to preserve layout
    if fmt == "pdf" and ext == ".pdf" and corrected_text == original_text:
        out_path = os.path.join(out_dir, "corrected.pdf")
        shutil.copy2(in_path, out_path)
        return out_path

    # Otherwise render in requested format
    if fmt == "txt":
        out_path = os.path.join(out_dir, "corrected.txt")
        return write_txt(corrected, out_path)
    if fmt == "pdf":
        out_path = os.path.join(out_dir, "corrected.pdf")
        return write_pdf(corrected, out_path)

    out_path = os.path.join(out_dir, "corrected.docx")
    return write_docx(corrected, out_path)

def write_pdf(paragraphs: list[str], out_path: str) -> str:
    """
    Create a simple text PDF from corrected paragraphs.
    Handles PyMuPDF insert_textbox return quirks and ensures text is placed.
    """
    doc = fitz.open()
    # Use a standard paper size; switch to "a4" if you prefer
    page_rect = fitz.paper_rect("letter")
    margin = 56  # ~0.78 in
    box = fitz.Rect(
        page_rect.x0 + margin, page_rect.y0 + margin,
        page_rect.x1 - margin, page_rect.y1 - margin
    )

    text = "\n\n".join(paragraphs).strip()
    if not text:
        # still emit a blank single-page PDF
        doc.new_page(width=page_rect.width, height=page_rect.height)
        doc.save(out_path)
        doc.close()
        return out_path

    fontsize = 11
    lineheight = fontsize * 1.4
    fontname = "helv"  # built-in Helvetica; you can also try "Helvetica"

    remaining: str | None = text
    while remaining:
        page = doc.new_page(width=page_rect.width, height=page_rect.height)
        res = page.insert_textbox(
            box,
            remaining,
            fontname=fontname,
            fontsize=fontsize,
            lineheight=lineheight,
            align=0,       # left
            render_mode=0  # fill text (default)
        )

        # Normalize return: some versions return leftover string,
        # others return 0/0.0 if all placed, some return (n_written, leftover)
        if isinstance(res, str):
            remaining = res
        elif isinstance(res, (int, float)):
            # 0 / 0.0 means "everything fit"; keep no remainder
            remaining = ""
        elif isinstance(res, tuple) and len(res) >= 2 and isinstance(res[1], str):
            remaining = res[1]
        else:
            # Assume done
            remaining = ""

    doc.save(out_path)
    doc.close()
    return out_path