from __future__ import annotations
from typing import List, Dict
import textstat
import re
import spacy
from app.core.config import LONG_SENTENCE_THRESHOLD

# load spaCy once
_nlp = None
def nlp():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm", disable=["ner"])
    return _nlp

WEASEL = {"very", "really", "quite", "basically", "actually", "clearly", "obviously"}
JARGON = {"utilize", "leverage", "synergy", "paradigm"}

def sent_tokens(paragraphs: List[str]) -> List[str]:
    docs = nlp().pipe(paragraphs, batch_size=100)
    sents: List[str] = []
    for d in docs:
        sents.extend([s.text.strip() for s in d.sents if s.text.strip()])
    return sents

def is_passive(sent_doc) -> bool:
    # heuristic: look for auxpass or passive dependency
    for token in sent_doc:
        if token.dep_ in {"auxpass"} or token.tag_ in {"VBN"} and any(t.dep_ == "aux" for t in token.head.children):
            return True
    return False

def clarity_long_sentences(paragraphs: List[str]) -> List[Dict]:
    issues = []
    for pi, p in enumerate(paragraphs):
        d = nlp()(p)
        for s in d.sents:
            words = [t.text for t in s if t.is_alpha or t.is_punct]
            if len([t for t in s if t.is_alpha]) > LONG_SENTENCE_THRESHOLD:
                issues.append({
                    "category": "clarity",
                    "severity": "medium" if len(words) < 35 else "high",
                    "message": f"Long sentence ({len(words)} words). Consider splitting.",
                    "rule": "LONG_SENTENCE",
                    "location": {"paragraph": pi, "start": s.start_char, "end": s.end_char},
                })
    return issues

def style_weasel_jargon(paragraphs: List[str]) -> List[Dict]:
    issues = []
    for pi, p in enumerate(paragraphs):
        tokens = [t.lower() for t in re.findall(r"[A-Za-z']+", p)]
        if any(w in WEASEL for w in tokens):
            issues.append({
                "category": "style",
                "severity": "low",
                "message": "Weasel words detected (e.g., very/really/quite).",
                "rule": "WEASEL_WORDS",
                "location": {"paragraph": pi},
            })
        if any(w in JARGON for w in tokens):
            issues.append({
                "category": "style",
                "severity": "low",
                "message": "Jargon detected (e.g., leverage/utilize/synergy).",
                "rule": "JARGON",
                "location": {"paragraph": pi},
            })
    return issues

def readability_metrics(text: str) -> Dict:
    return {
        "flesch_reading_ease": textstat.flesch_reading_ease(text),
        "smog_index": textstat.smog_index(text),
        "automated_readability_index": textstat.automated_readability_index(text),
        "avg_sentence_length": textstat.avg_sentence_length(text),
    }

def passive_voice_issues(paragraphs: List[str]) -> List[Dict]:
    issues = []
    for pi, p in enumerate(paragraphs):
        d = nlp()(p)
        for s in d.sents:
            if is_passive(s):
                issues.append({
                    "category": "clarity",
                    "severity": "low",
                    "message": "Passive voice detected. Prefer active voice where possible.",
                    "rule": "PASSIVE_VOICE",
                    "location": {"paragraph": pi, "start": s.start_char, "end": s.end_char},
                })
    return issues
