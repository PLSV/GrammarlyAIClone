import os
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from app.core.config import DATA_DIR

router = APIRouter(tags=["download"])

@router.get("/download")
def download(
    doc_id: str = Query(..., description="Document ID returned by /upload"),
    filename: str = Query(..., description="File in the doc folder, e.g. corrected.docx or corrected.pdf")
):
    doc_dir = os.path.join(DATA_DIR, doc_id)
    path = os.path.join(doc_dir, filename)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, filename=filename)
