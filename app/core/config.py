MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB soft cap
ALLOWED_EXTENSIONS = {'.pdf', '.docx'}
DATA_DIR = "data"
MIME_ALLOW = {
    ".pdf": {"application/pdf"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",
    },
}
