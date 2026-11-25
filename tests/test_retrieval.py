from pathlib import Path
from src.indexer import build_index
from src.retrieval import HybridRetriever

def test_superseded_clauses_are_filtered(tmp_path):
    root = Path(__file__).parents[1]
    build_index(root / "data" / "policy.txt", tmp_path)
    result = HybridRetriever(tmp_path).retrieve("What is the current Modern Trade discount?")
    assert result.clauses
    assert all(c.status == "current" for c in result.clauses)
    assert any(c.section == "3" for c in result.clauses)
    assert any(c.section == "3.1" for c in result.clauses)
    assert not any("15%" in c.text for c in result.clauses)

def test_gt_credit_retrieves_clause_7_1(tmp_path):
    root = Path(__file__).parents[1]
    build_index(root / "data" / "policy.txt", tmp_path)
    result = HybridRetriever(tmp_path).retrieve("How many days credit for GT distributors?")
    assert any(c.section == "7.1" for c in result.clauses)
