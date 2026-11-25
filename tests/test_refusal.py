from pathlib import Path
from src.indexer import build_index
from src.retrieval import HybridRetriever
from src.generation import generate_answer, REFUSAL

def test_out_of_scope_hr_question_refuses_without_api(tmp_path):
    root = Path(__file__).parents[1]
    build_index(root / "data" / "policy.txt", tmp_path)
    result = HybridRetriever(tmp_path).retrieve("What is the employee leave policy?")
    assert result.refused_by_scope
    assert generate_answer("What is the employee leave policy?", result) == REFUSAL

def test_uncovered_question_refuses_when_retrieval_empty(tmp_path):
    root = Path(__file__).parents[1]
    build_index(root / "data" / "policy.txt", tmp_path)
    result = HybridRetriever(tmp_path).retrieve("What is the distributor credit limit in rupees?")
    # This is not an explicit out-of-scope topic, so the retriever may return
    # related credit clauses; generation is required to refuse if they don't answer.
    assert not result.refused_by_scope
    assert result.clauses == []
    assert generate_answer("What is the distributor credit limit in rupees?", result) == REFUSAL
