from pydantic import BaseModel, Field
from typing import List, Literal, Optional

Severity = Literal["low", "medium", "high"]
Category = Literal["grammar", "style", "clarity", "readability", "formatting", "consistency"]

class Location(BaseModel):
    paragraph: int
    start: Optional[int] = None
    end: Optional[int] = None

class Issue(BaseModel):
    id: str = Field(default_factory=lambda: "")
    category: Category
    severity: Severity
    message: str
    suggestion: Optional[str] = None
    rule: Optional[str] = None
    location: Location

class Summary(BaseModel):
    score: int
    totals: dict
    readability: dict

class Report(BaseModel):
    doc_id: str
    score: int
    issues: List[Issue]
    summary: Summary
