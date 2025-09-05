from __future__ import annotations
from typing import List, Dict
import os
from language_tool_python import LanguageTool
import spacy
from app.services.extract import extract_text
from app.services import rules as R
from app.models.report import Report, Issue, Summary
from app.core.config import DATA_DIR, WEIGHTS, READABILITY_TARGET

# Lazy singletons
_LT = None
def LT():
    global _LT
    if _LT is None:
        _LT = LanguageTool("en-US")  # switch to en-GB if needed
    return _LT

_NLP = None
def NLP():
    global _NLP
    if _NLP is None:
        _NLP = spacy.load("en_core_web_sm", disable=["ner"])
    return _NLP

def lt_issues(paragraphs: List[str]) -> List[Dict]:
    issues: List[Dict] = []
    for pi, p in enumerate(paragraphs):
        matches = LT().check(p)
        for m in matches:
            suggestion = ", ".join(m.replacements[:3]) if m.replacements else None
            issues.append({
                "category": "grammar",
                "severity": "high" if m.ruleIssueType in ("misspelling", "typographical") else "medium",
                "message": m.message,
                "rule": m.ruleId,
                "location": {"paragraph": pi, "start": m.offset, "end": m.offset + m.errorLength},
                "suggestion": suggestion,
            })
    return issues

def score_from_counts(counts: Dict, readability: Dict) -> int:
    # Simple weighted score: start at 100 and subtract penalties
    penalties = (
        counts.get("grammar", 0) * 1.5 +
        counts.get("style", 0) * 0.75 +
        counts.get("clarity", 0) * 1.0
    )
    # Readability penalty if below target
    fre = readability.get("flesch_reading_ease", 0.0)
    if fre < READABILITY_TARGET:
        penalties += (READABILITY_TARGET - fre) * 0.3
    return max(0, int(100 - min(100, penalties)))

def analyze_document(doc_id: str, path: str) -> Report:
    paragraphs = extract_text(path)
    full_text = "\n\n".join(paragraphs)

    # Collect issues
    grammar = lt_issues(paragraphs)
    style = R.style_weasel_jargon(paragraphs)
    clarity = R.clarity_long_sentences(paragraphs) + R.passive_voice_issues(paragraphs)

    all_issues = grammar + style + clarity

    # Tally
    counts = {"grammar": len(grammar), "style": len(style), "clarity": len(clarity)}
    readability = R.readability_metrics(full_text)
    score = score_from_counts(counts, readability)

    # Build pydantic Report
    issues_models = [
        Issue(
            id=f"{i}-{k}",
            category=i["category"], severity=i["severity"], message=i["message"],
            suggestion=i.get("suggestion"), rule=i.get("rule"),
            location=i["location"]
        )
        for k, i in enumerate(all_issues, start=1)
    ]
    summary = Summary(score=score, totals=counts, readability=readability)
    return Report(doc_id=doc_id, score=score, issues=issues_models, summary=summary)
