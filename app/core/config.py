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

# Analyzer configuration
READABILITY_TARGET = 55  # Flesch Reading Ease target
LONG_SENTENCE_THRESHOLD = 25  # words
PASSIVE_THRESHOLD_PCT = 20    # % passive sentences considered high

WEIGHTS = {
    "grammar": 0.45,
    "style": 0.15,
    "clarity": 0.20,
    "readability": 0.20,
}
