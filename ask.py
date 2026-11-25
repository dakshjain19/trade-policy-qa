"""CLI entry point: python ask.py --index, then python ask.py "question"."""
from __future__ import annotations
import argparse
from pathlib import Path
from src.indexer import build_index
from src.retrieval import HybridRetriever
from src.generation import generate_answer

BASE = Path(__file__).resolve().parent

def main() -> None:
    parser = argparse.ArgumentParser(description="Trade policy question-answering assistant")
    parser.add_argument("question", nargs="?", help="Question in plain language")
    parser.add_argument("--index", action="store_true", help="Build/rebuild the local retrieval index")
    parser.add_argument("--policy", default=str(BASE / "data"))
    parser.add_argument("--index-dir", default=str(BASE / "index"))
    args = parser.parse_args()
    if args.index:
        count = build_index(args.policy, args.index_dir)
        print(f"Indexed {count} clauses into {args.index_dir}")
        return
    if not args.question:
        parser.error('provide a question or use --index')
    retriever = HybridRetriever(args.index_dir)
    result = retriever.retrieve(args.question)
    print(generate_answer(args.question, result))

if __name__ == "__main__":
    main()
