# app/services/revise.py
from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import Literal, List, Dict, Any, Iterable
from shutil import copyfile

from app.services.convert import pdf_to_docx, docx_to_pdf, ConvertError
from app.services.docx_apply import collect_segments, apply_rewrites
from app.services.llm import rewrite_segments_with_gpt  # use-time API-key check below

log = logging.getLogger("revise")

GUIDELINES = os.getenv(
    "ENGLISH_GUIDELINES",
    (
        "Fix grammar, clarity, concision, and tone. "
        "Do NOT change layout, numbering, bullets, or indentation. "
        "Do NOT merge or split list items. Preserve meaning and terminology."
    ),
)


def _use_llm_now() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def _noop_rewrite(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [{"index": s["index"], "text": s.get("text", "")} for s in segments]


def _chunks(items: List[Dict[str, Any]], size: int) -> Iterable[List[Dict[str, Any]]]:
    for i in range(0, len(items), size):
        yield items[i: i + size]


def _rewrite_all(segments: List[Dict[str, Any]], batch_size: int = 50) -> List[Dict[str, Any]]:
    if not _use_llm_now():
        log.info("LLM disabled or OPENAI_API_KEY missing — performing no-op rewrite.")
        return _noop_rewrite(segments)

    rewrites: List[Dict[str, Any]] = []
    for batch in _chunks(segments, batch_size):
        batch_out = rewrite_segments_with_gpt(batch, GUIDELINES)
        for r in batch_out:
            try:
                rewrites.append({"index": int(r["index"]), "text": str(r["text"])})
            except Exception:
                continue
    return rewrites


def _all_empty(segments: List[Dict[str, Any]]) -> bool:
    return all(not (s.get("text") or "").strip() for s in segments)


def revise_document(
    input_path: str,
    out_dir: str,
    fmt: Literal["pdf", "docx"] = "pdf",
) -> str:
    """
    Normalize input to DOCX (if PDF) -> collect DOCX paragraphs (incl. tables) -> rewrite text
    -> write corrected DOCX -> optionally convert back to PDF.

    If we detect that LibreOffice produced a DOCX whose visible content is primarily
    in text boxes (unreadable by python-docx), we fall back to copying the original
    file so you never get a blank output.
    """
    in_path = Path(input_path).resolve()
    os.makedirs(out_dir, exist_ok=True)

    # 1) Normalize to DOCX
    in_ext = in_path.suffix.lower()
    if in_ext == ".pdf":
        log.info("Converting PDF to DOCX via LibreOffice: %s", in_path)
        docx_in = pdf_to_docx(str(in_path))
    elif in_ext == ".docx":
        docx_in = str(in_path)
    else:
        raise ValueError("Only .pdf or .docx inputs are supported")

    # 2) Collect segments (paragraphs + list items + table paragraphs)
    segments = collect_segments(docx_in)
    log.info("Collected %d segments from DOCX", len(segments))

    # If nothing meaningful found, bail out gracefully
    if not segments or _all_empty(segments):
        log.warning(
            "No usable text segments found in DOCX (likely text boxes). "
            "Falling back to returning the original document."
        )
        if fmt == "docx":
            target = Path(out_dir).joinpath("corrected.docx")
            copyfile(docx_in, target)
            return str(target.resolve())
        else:
            # want PDF
            if in_ext == ".pdf":
                target = Path(out_dir).joinpath("corrected.pdf")
                copyfile(str(in_path), target)
                return str(target.resolve())
            # input was DOCX, try export to PDF; if that fails, return the DOCX
            try:
                out_pdf = docx_to_pdf(docx_in)
                target = Path(out_dir).joinpath("corrected.pdf")
                copyfile(out_pdf, target)
                return str(target.resolve())
            except ConvertError:
                target = Path(out_dir).joinpath("corrected.docx")
                copyfile(docx_in, target)
                return str(target.resolve())

    # 3) Rewrite via LLM (or no-op)
    rewrites = _rewrite_all(segments)

    # 4) Apply rewrites back into a new DOCX (preserves list styles/indent)
    corrected_docx = str(Path(out_dir).joinpath("corrected.docx"))
    apply_rewrites(docx_in, rewrites, corrected_docx)

    # 5) Output in requested format
    if fmt == "docx":
        return str(Path(corrected_docx).resolve())

    if fmt == "pdf":
        try:
            out_pdf = docx_to_pdf(corrected_docx)  # produced in a temp folder
            target_pdf = str(Path(out_dir).joinpath("corrected.pdf"))
            copyfile(out_pdf, target_pdf)
            return str(Path(target_pdf).resolve())
        except ConvertError:
            # If export fails, still return the DOCX
            return str(Path(corrected_docx).resolve())

    raise ValueError("fmt must be 'pdf' or 'docx'")
