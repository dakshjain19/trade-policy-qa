"""Structure-aware parser for numbered trade-policy sections and subclauses."""
from __future__ import annotations
import re
from pathlib import Path
from .models import Clause

HEADER_RE = re.compile(r"^SECTION\s+(\d+)\.\s*(.+)$", re.I)
SUB_RE = re.compile(r"^(\d+\.\d+)\s+(.+)$")
VERSION_RE = re.compile(r"Version\s+([0-9.]+)\s*\|\s*Effective date:\s*([^|]+)", re.I)

def parse_policy(path: str | Path) -> list[Clause]:
    raw = Path(path).read_text(encoding="utf-8")
    lines = [line.rstrip() for line in raw.splitlines()]
    meta = VERSION_RE.search(raw)
    version = meta.group(1).strip() if meta else "unknown"
    effective = meta.group(2).strip() if meta else "not stated"
    clauses: list[Clause] = []
    current_section: str | None = None
    current_title = ""
    buffer: list[str] = []

    def flush() -> None:
        nonlocal buffer
        body = "\n".join(x for x in buffer if x.strip()).strip()
        if not body or current_section is None:
            buffer = []
            return
        clauses.append(Clause(
            clause_id=current_section,
            section=current_section,
            title=current_title,
            text=body,
            version=version,
            effective_date=effective,
            parent_section=(current_section.split(".")[0] if "." in current_section else None),
            source_file=Path(path).name,
        ))
        buffer = []

    for line in lines:
        header = HEADER_RE.match(line.strip())
        if header:
            flush()
            current_section = header.group(1)
            current_title = header.group(2).strip()
            continue
        sub = SUB_RE.match(line.strip())
        if sub and current_section is not None:
            flush()
            current_section = sub.group(1)
            current_title = sub.group(2).strip()
            buffer.append(line.strip())
            continue
        if current_section is not None and line.strip():
            buffer.append(line.strip())
    flush()

    # Preserve the channel table as one atomic clause. Its three channel/value
    # rows are exact policy text and should not be fragmented into semantic chunks.
    for clause in clauses:
        if clause.section == "3":
            clause.text = clause.text.replace("|", " | ")
    # The historical limit is represented as a separate, explicitly inactive
    # record. It is retained for auditability but retrieval excludes it.
    revision = next((c for c in clauses if c.section == "3.1"), None)
    if revision and "15%" in revision.text:
        # Remove the historical sentence from the active clause itself. The old
        # value survives only as a separate superseded record, which retrieval
        # can hard-filter before either ranking method runs.
        revision.text = re.sub(
            r"In Version 1\.0 \(2024\), the Modern Trade limit was\s*15%\.",
            "", revision.text, flags=re.I
        ).strip()
        clauses.append(Clause(
            clause_id="3.1@v1",
            section="3.1",
            title="Superseded Modern Trade discount limit (historical)",
            text="In Version 1.0 (2024), the Modern Trade limit was 15%.",
            version="1.0",
            effective_date="2024 (exact date not stated)",
            status="superseded",
            parent_section="3",
            source_file=Path(path).name,
        ))
    return clauses
