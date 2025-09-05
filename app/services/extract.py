import os
import fitz          # PyMuPDF
import docx          # python-docx

def extract_text(path: str) -> list[str]:
    """
    Return a list of paragraph-like strings from a PDF or DOCX.
    Keeps memory modest by iterating pages/paragraphs.
    """
    ext = os.path.splitext(path)[1].lower()

    if ext == ".pdf":
        paras: list[str] = []
        with fitz.open(path) as doc:
            for page in doc:
                # 'blocks' yields tuples; index 4 is the text
                blocks = page.get_text("blocks") or []
                for b in blocks:
                    if isinstance(b, (list, tuple)) and len(b) >= 5:
                        text = (b[4] or "").strip()
                        if text:
                            paras.append(text)
        return paras

    if ext == ".docx":
        d = docx.Document(path)
        return [p.text.strip() for p in d.paragraphs if p.text and p.text.strip()]

    raise ValueError(f"Unsupported extension: {ext}")
