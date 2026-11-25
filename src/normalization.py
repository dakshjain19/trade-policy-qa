"""Query normalization for spelling variants and common trade abbreviations."""
import re

EXPANSIONS = {
    "gt": "gt general trade",
    "mt": "mt modern trade",
    "ec": "ec e-commerce",
    "asm": "asm area sales manager",
    "rsm": "rsm regional sales manager",
    "hr": "human resources",
    "rs": "rupees",
    "inr": "rupees",
}

def normalize_query(query: str) -> str:
    q = query.lower().replace("₹", " rs ")
    q = re.sub(r"\b(rs\.?)\s*(?=\d)", "rs rupees ", q)
    q = re.sub(r"\b(\d+)\s*lakh\b", r"\1 lakh", q)
    for short, long in EXPANSIONS.items():
        q = re.sub(rf"\b{re.escape(short)}\b", long, q)
    q = re.sub(r"[^a-z0-9.%\s-]", " ", q)
    return re.sub(r"\s+", " ", q).strip()
