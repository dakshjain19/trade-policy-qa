"""Build a persistent hybrid BM25 + sentence-embedding index."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer
from .parser import parse_policy

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

def tokens(text: str) -> list[str]:
    import re
    return re.findall(r"[a-z0-9]+(?:\.[0-9]+)?|[0-9]+%", text.lower())

def build_index(policy_path: str | Path, index_dir: str | Path) -> int:
    out = Path(index_dir)
    out.mkdir(parents=True, exist_ok=True)
    source = Path(policy_path)
    policy_files = sorted(source.glob("*.txt")) if source.is_dir() else [source]
    if not policy_files:
        raise FileNotFoundError(f"No .txt policy documents found in {source}")
    clauses = []
    manifest_path = source / "policy_manifest.json" if source.is_dir() else source.parent / "policy_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {"documents": {}}
    document_rules = manifest.get("documents", {})
    for file_path in policy_files:
        parsed = parse_policy(file_path)
        rule = document_rules.get(file_path.name, {})
        document_status = rule.get("status", "current")
        if document_status not in {"current", "superseded"}:
            raise ValueError(f"Invalid status for {file_path.name}: {document_status}")
        for clause in parsed:
            if clause.status != "superseded":
                clause.status = rule.get("clauses", {}).get(clause.section, document_status)
                if clause.status not in {"current", "superseded"}:
                    raise ValueError(f"Invalid clause status for {file_path.name} section {clause.section}")
        clauses.extend(parsed)
    (out / "clauses.json").write_text(
        json.dumps([c.to_dict() for c in clauses], indent=2), encoding="utf-8"
    )
    corpus = [f"{c.section} {c.title} {c.text}" for c in clauses]
    bm25 = BM25Okapi([tokens(x) for x in corpus])
    # Persist token corpus; BM25 is reconstructed cheaply at load time.
    (out / "bm25_corpus.json").write_text(json.dumps([tokens(x) for x in corpus]), encoding="utf-8")
    model = SentenceTransformer(MODEL_NAME)
    vectors = model.encode(corpus, normalize_embeddings=True, show_progress_bar=False)
    np.save(out / "embeddings.npy", np.asarray(vectors, dtype=np.float32))
    (out / "manifest.json").write_text(json.dumps({
        "embedding_model": MODEL_NAME,
        "clause_count": len(clauses),
        "index_format": 1
    }, indent=2), encoding="utf-8")
    return len(clauses)
