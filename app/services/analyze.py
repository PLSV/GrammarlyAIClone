from app.services.extract import extract_text

def analyze_document(path: str) -> dict:
    """
    Stub analyzer for Step 2:
    - extracts paragraphs
    - returns count and first few samples
    """
    paragraphs = extract_text(path)
    return {
        "paragraph_count": len(paragraphs),
        "sample": paragraphs[:3],   # preview first 3 paras
    }
