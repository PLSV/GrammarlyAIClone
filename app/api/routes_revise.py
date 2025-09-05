import os
from typing import Literal
from fastapi import APIRouter, Query, HTTPException
from app.core.config import DATA_DIR
from app.services.revise import revise_document

router = APIRouter(tags=["revise"])

@router.post("/revise")
def revise(
    doc_id: str = Query(..., description="Document ID returned by /upload"),
    fmt: Literal["docx", "txt", "pdf"] = Query("docx", description="Output format")
):
    doc_dir = os.path.join(DATA_DIR, doc_id)
    if not os.path.isdir(doc_dir):
        raise HTTPException(status_code=404, detail="Document not found")

    originals = [f for f in os.listdir(doc_dir) if f.startswith("original.")]
    if not originals:
        raise HTTPException(status_code=404, detail="No original file found")
    in_path = os.path.join(doc_dir, originals[0])

    out_path = revise_document(in_path, doc_dir, fmt=fmt)
    # return a simple payload with where to fetch it from
    return {
        "doc_id": doc_id,
        "format": fmt,
        "corrected_path": out_path
    }
