from __future__ import annotations
import os, shutil, re
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

def _measure_width(page: fitz.Page, text: str, fontname: str, fontsize: float) -> float:
    """
    Cross-version width measurement:
    - Prefer Page.get_text_length (older / many builds)
    - Fallback to module-level fitz.get_text_length (other builds)
    - Last-resort heuristic if neither exists
    """
    # 1) Page.get_text_length(...)
    if hasattr(page, "get_text_length"):
        return page.get_text_length(text, fontname=fontname, fontsize=fontsize)

    # 2) Module-level fitz.get_text_length(...)
    if hasattr(fitz, "get_text_length"):
        try:
            return fitz.get_text_length(text, fontname=fontname, fontsize=fontsize)
        except TypeError:
            # some signatures are (text, fontsize, fontname)
            return fitz.get_text_length(text, fontsize, fontname)

    # 3) Heuristic fallback (approx)
    return len(text) * fontsize * 0.5

def _pick_fontfile() -> str | None:
    for p in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]:
        if os.path.exists(p): return p
    return None  # falls back to Base14 Courier (monospace) which avoids overlap

def _ensure_font(doc: fitz.Document) -> str:
    # Prefer a Unicode TTF; else use a Base14 **monospace** (Courier) to avoid metric surprises
    fontname = "Courier"  # safer than proportional when metrics APIs vary
    ff = _pick_fontfile()
    if ff:
        try:
            fontname = doc.insert_font(fontfile=ff)
        except Exception:
            fontname = "Courier"
    return fontname

def _sanitize_paragraphs(paragraphs: list[str]) -> list[str]:
    out = []
    for p in paragraphs:
        # 1) normalize internal breaks / tabs → single spaces
        p = p.replace("\r\n", "\n").replace("\r", "\n")
        p = re.sub(r"[ \t\f\v]+", " ", p)
        p = re.sub(r"\s*\n\s*", " ", p)           # collapse hard newlines inside a paragraph
        # 2) collapse multiple spaces and trim
        p = re.sub(r" {2,}", " ", p).strip()
        out.append(p)
    return out

def write_pdf(paragraphs: list[str], out_path: str) -> str:
    doc = fitz.open()
    page_rect = fitz.paper_rect("a4")              # can change to "letter"
    margin = 72                                     # 1 inch margin for safety
    max_w = page_rect.width - 2 * margin
    max_h = page_rect.height - 2 * margin

    # Use sanitized text so hidden line-breaks can’t cause same-line redraws
    paragraphs = _sanitize_paragraphs(paragraphs)
    full_text = "\n\n".join(paragraphs).strip()

    page = doc.new_page(width=page_rect.width, height=page_rect.height)
    fontname = _ensure_font(doc)
    fontsize = 12.0                                  # slightly larger → clearer
    leading = fontsize * 1.6                         # generous line height (prevents overlap)

    if not full_text:
        doc.save(out_path); doc.close(); return out_path

    # Greedy wrap with cross-version width measurement (_measure_width)
    def wrap_para(p: str) -> list[str]:
        if not p: return [""]
        words = p.split(" ")
        lines, line = [], ""
        for w in words:
            cand = (line + " " + w).strip() if line else w
            width = _measure_width(page, cand, fontname, fontsize)
            if width <= max_w:
                line = cand
            else:
                if line: lines.append(line)
                line = w
        if line: lines.append(line)
        return lines

    x, y = margin, margin
    drew_anything = False

    for para in full_text.split("\n\n"):
        for line in wrap_para(para):
            # If next baseline would exceed page bottom → new page
            if y + leading > page_rect.height - margin:
                page = doc.new_page(width=page_rect.width, height=page_rect.height)
                y = margin
            # Draw once per line; baseline strictly increases → no overlap possible
            page.insert_text((x, y), line, fontname=fontname, fontsize=fontsize, render_mode=0)
            y += leading
            drew_anything = True
        # extra breathing room between paragraphs
        y += leading * 0.5

    # Ensure non-empty PDF even if everything trimmed
    if not drew_anything:
        page.insert_text((margin, margin), " ", fontname=fontname, fontsize=fontsize)

    doc.save(out_path)
    doc.close()
    return out_path
