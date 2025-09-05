from fastapi import APIRouter, UploadFile, File
from app.utils.storage import save_secure

router = APIRouter(tags=["upload"])

@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    doc_id, path = await save_secure(file)
    return {"doc_id": doc_id, "stored_path": path}
