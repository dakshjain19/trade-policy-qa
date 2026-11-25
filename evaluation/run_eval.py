"""Run the gold set through retrieval + Gemini; report quality and leakage."""
from __future__ import annotations
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.retrieval import HybridRetriever
from src.generation import generate_answer, REFUSAL

def main() -> None:
    cases = json.loads((ROOT / "evaluation" / "eval_set.json").read_text(encoding="utf-8"))
    retriever = HybridRetriever(ROOT / "index")
    exact = citation_ok = refusal_ok = 0
    leaks = []
    for case in cases:
        result = retriever.retrieve(case["question"])
        answer = generate_answer(case["question"], result)
        time.sleep(5)
        refused = answer.strip() == REFUSAL
        refusal_ok += int(refused == case["should_refuse"])
        if case["should_refuse"]:
            exact += int(refused)
        else:
            expected = case["expected_answer"].lower()
            # Score presence of key expected content; allow natural-language phrasing.
            key = re.sub(r"[^a-z0-9% ]", "", expected)
            normalized_answer = re.sub(r"[^a-z0-9% ]", "", answer.lower())
            exact += int(all(token in normalized_answer for token in key.split() if token not in {"the", "a", "by", "within", "and"}))
            sections = [x.strip() for x in case["expected_section"].split("and")]
            citation_match = re.search(r"Source:\s*Section\s+(.+?)\s*\|\s*Version", answer)
            cited = set(re.findall(r"[0-9]+(?:\.[0-9]+)?", citation_match.group(1))) if citation_match else set()
            expected_sections = set(x for x in sections if re.fullmatch(r"[0-9.]+", x))
            citation_ok += int(bool(cited) and expected_sections.issubset(cited))
        if "15%" in answer and "12%" not in answer:
            leaks.append(case["question"])
    n = len(cases)
    answered_n = sum(not c["should_refuse"] for c in cases)
    print(f"Questions: {n}")
    print(f"Answer accuracy: {exact}/{n} = {exact/n:.1%}")
    print(f"Citation accuracy (answerable): {citation_ok}/{answered_n} = {citation_ok/answered_n:.1%}")
    print(f"Refusal accuracy: {refusal_ok}/{n} = {refusal_ok/n:.1%}")
    print(f"Superseded-value leaks: {len(leaks)}")
    if leaks:
        print("Leak questions:", *leaks, sep="\n- ")
        raise SystemExit(1)

if __name__ == "__main__":
    main()
