from pathlib import Path
from src.parser import parse_policy

def test_parser_keeps_numbered_clauses_and_metadata():
    clauses = parse_policy(Path(__file__).parents[1] / "data" / "policy.txt")
    by_id = {c.clause_id: c for c in clauses}
    assert "3" in by_id and "3.1" in by_id and "4.3" in by_id
    assert by_id["3"].version == "2.0"
    assert by_id["3"].effective_date == "1 April 2025"
    assert "General Trade" in by_id["3"].text
    assert "Head of Sales" in by_id["4.3"].text
    assert "15%" not in by_id["3.1"].text
    assert "12%" in by_id["3.1"].text

def test_historical_value_is_explicitly_superseded():
    clauses = parse_policy(Path(__file__).parents[1] / "data" / "policy.txt")
    old = [c for c in clauses if c.clause_id == "3.1@v1"]
    assert len(old) == 1
    assert old[0].status == "superseded"
    assert "15%" in old[0].text
