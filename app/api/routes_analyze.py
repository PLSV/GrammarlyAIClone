import os
from fastapi import APIRouter, Query, HTTPException
from app.core.config import DATA_DIR
from app.services.analyze import analyze_document

router = APIRouter(tags=["analyze"])

@router.post("/analyze")
def analyze(doc_id: str = Query(...)):
    doc_dir = os.path.join(DATA_DIR, doc_id)
    if not os.path.isdir(doc_dir):
        raise HTTPException(status_code=404, detail="Document not found")
    originals = [f for f in os.listdir(doc_dir) if f.startswith("original.")]
    if not originals:
        raise HTTPException(status_code=404, detail="No original file found")
    path = os.path.join(doc_dir, originals[0])
    report = analyze_document(doc_id, path)
    return report.model_dump()
