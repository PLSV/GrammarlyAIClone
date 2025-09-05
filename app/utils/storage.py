import os, uuid, tempfile
from fastapi import UploadFile, HTTPException
import magic
from app.core.config import ALLOWED_EXTENSIONS, MIME_ALLOW, DATA_DIR

async def save_secure(file: UploadFile) -> tuple[str, str]:
    _, ext = os.path.splitext(file.filename or "")
    ext = ext.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only .pdf or .docx allowed")

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        while True:
            chunk = await file.read(1 << 20)  # 1 MB
            if not chunk:
                break
            tmp.write(chunk)
        tmp_path = tmp.name

    mime = magic.Magic(mime=True)
    file_mime = mime.from_file(tmp_path)
    if file_mime not in MIME_ALLOW[ext]:
        os.remove(tmp_path)
        raise HTTPException(
            status_code=400,
            detail=f"Unexpected MIME type: {file_mime} for {ext}"
        )

    doc_id = uuid.uuid4().hex[:12]
    doc_dir = os.path.join(DATA_DIR, doc_id)
    os.makedirs(doc_dir, mode=0o700, exist_ok=True)
    dest = os.path.join(doc_dir, f"original{ext}")
    os.replace(tmp_path, dest)
    return doc_id, dest
