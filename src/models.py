"""Typed data models shared by the trade-policy QA pipeline."""
from dataclasses import asdict, dataclass
from typing import Any

@dataclass
class Clause:
    clause_id: str
    section: str
    title: str
    text: str
    version: str
    effective_date: str
    status: str = "current"
    parent_section: str | None = None
    source_file: str = "policy.txt"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Clause":
        return cls(**value)

@dataclass
class RetrievalResult:
    clauses: list[Clause]
    scores: dict[str, float]
    refused_by_scope: bool = False
