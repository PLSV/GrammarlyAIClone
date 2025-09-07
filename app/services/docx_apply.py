# app/services/docx_apply.py
from typing import List, Dict, Any
from docx import Document

def _is_list_paragraph(p) -> bool:
    pPr = getattr(p._p, "pPr", None)
    return bool(pPr is not None and getattr(pPr, "numPr", None) is not None) or ("List" in (p.style.name or ""))

def collect_segments(docx_path: str) -> List[Dict[str, Any]]:
    """
    Returns a list like:
    [{"index": 0, "kind": "paragraph" | "list_item", "text": "..."}]
    """
    doc = Document(docx_path)
    segments = []
    for i, p in enumerate(doc.paragraphs):
        text = (p.text or "").strip()
        kind = "list_item" if _is_list_paragraph(p) else "paragraph"
        segments.append({"index": i, "kind": kind, "text": text})
    return segments

def apply_rewrites(docx_path: str, rewrites: List[Dict[str, Any]], out_path: str) -> str:
    """
    Replaces paragraph text ONLY (preserves bullet/numbering/indent via style & numbering props).
    """
    doc = Document(docx_path)
    by_idx = {int(r["index"]): str(r["text"]) for r in rewrites if "index" in r and "text" in r}
    for i, p in enumerate(doc.paragraphs):
        if i in by_idx:
            p.text = by_idx[i]
    doc.save(out_path)
    return out_path
