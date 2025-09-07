# app/services/revise.py
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal, List, Dict, Any, Iterable

from app.services.convert import pdf_to_docx, docx_to_pdf, ConvertError
from app.services.docx_apply import collect_segments, apply_rewrites

# Optional GPT integration: if llm.py is present and OPENAI_API_KEY is set,
# we will use it. Otherwise we no-op the text (layout-preserving pass-through).
_USE_LLM = False
try:
    from app.services.llm import rewrite_segments_with_gpt  # type: ignore
    _USE_LLM = bool(os.getenv("OPENAI_API_KEY"))
except Exception:
    _USE_LLM = False


# ----- Guidelines -------------------------------------------------------------

# You can keep this in an env var or a file. This default is safe.
GUIDELINES = os.getenv(
    "ENGLISH_GUIDELINES",
    (
        "Fix grammar, clarity, concision, and tone. "
        "Do NOT change layout, numbering, bullets, or indentation. "
        "Do NOT merge or split list items. Preserve meaning and terminology."
    ),
)


# ----- Utilities --------------------------------------------------------------

def _noop_rewrite(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return the same text back; useful for validating the LO pipeline."""
    return [{"index": s["index"], "text": s.get("text", "")} for s in segments]


def _chunks(items: List[Dict[str, Any]], size: int) -> Iterable[List[Dict[str, Any]]]:
    """Yield fixed-size chunks from a list."""
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _rewrite_all(
    segments: List[Dict[str, Any]],
    batch_size: int = 150,
) -> List[Dict[str, Any]]:
    """
    Rewrite all segments, batching through the LLM if available.
    Returns list of {"index": int, "text": str}.
    """
    if not _USE_LLM:
        return _noop_rewrite(segments)

    rewrites: List[Dict[str, Any]] = []
    for batch in _chunks(segments, batch_size):
        # Each batch is a list of {"index","kind","text"} dictionaries
        batch_out = rewrite_segments_with_gpt(batch, GUIDELINES)  # type: ignore[name-defined]
        # Normalize & extend
        for r in batch_out:
            try:
                rewrites.append({"index": int(r["index"]), "text": str(r["text"])})
            except Exception:
                # Skip malformed entries rather than fail the entire request
                continue
    return rewrites


# ----- Public API -------------------------------------------------------------

def revise_document(
    input_path: str,
    out_dir: str,
    fmt: Literal["pdf", "docx"] = "pdf",
) -> str:
    """
    Normalize input to DOCX (if PDF) -> collect DOCX paragraphs -> rewrite text
    (keeping list/bullet/indentation formatting) -> write corrected DOCX ->
    optionally convert back to PDF.

    Returns the absolute path to the generated output file.
    """
    in_path = Path(input_path).resolve()
    os.makedirs(out_dir, exist_ok=True)

    # 1) Normalize to DOCX
    in_ext = in_path.suffix.lower()
    if in_ext == ".pdf":
        docx_in = pdf_to_docx(str(in_path))
    elif in_ext == ".docx":
        docx_in = str(in_path)
    else:
        raise ValueError("Only .pdf or .docx inputs are supported")

    # 2) Collect segments (paragraphs + list items) from DOCX
    segments = collect_segments(docx_in)  # [{"index","kind","text"}, ...]

    # 3) Rewrite via LLM (or no-op if not configured)
    rewrites = _rewrite_all(segments)

    # 4) Apply rewrites back into a new DOCX (preserves list styles/indent)
    corrected_docx = str(Path(out_dir).joinpath("corrected.docx"))
    apply_rewrites(docx_in, rewrites, corrected_docx)

    # 5) Output in requested format
    if fmt == "docx":
        return str(Path(corrected_docx).resolve())

    if fmt == "pdf":
        try:
            out_pdf = docx_to_pdf(corrected_docx)
            return str(Path(out_pdf).resolve())
        except ConvertError as e:
            # If PDF export fails, still return the DOCX as a usable artifact.
            # You may also choose to re-raise depending on your API contract.
            return str(Path(corrected_docx).resolve())

    raise ValueError("fmt must be 'pdf' or 'docx'")
