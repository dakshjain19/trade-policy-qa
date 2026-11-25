"""Hybrid retrieval with hard status filtering and parent/child rule expansion."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer
from .models import Clause, RetrievalResult
from .normalization import normalize_query
from .indexer import tokens, MODEL_NAME

OUT_OF_SCOPE_TERMS = (
    "employee travel", "business travel", "payroll", "salary", "leave policy",
    "annual leave", "sick leave", "hr policy", "human resources", "employee benefits",
)

class HybridRetriever:
    def __init__(self, index_dir: str | Path, top_k: int = 8):
        self.path = Path(index_dir)
        self.clauses = [Clause.from_dict(x) for x in json.loads(
            (self.path / "clauses.json").read_text(encoding="utf-8"))]
        self.corpus_tokens = json.loads((self.path / "bm25_corpus.json").read_text(encoding="utf-8"))
        self.bm25 = BM25Okapi(self.corpus_tokens)
        self.embeddings = np.load(self.path / "embeddings.npy")
        self.model = SentenceTransformer(MODEL_NAME)
        self.top_k = top_k

    def retrieve(self, question: str) -> RetrievalResult:
        normalized = normalize_query(question)
        if any(term in normalized for term in OUT_OF_SCOPE_TERMS):
            return RetrievalResult([], {}, True)
        # The policy states credit periods, not a monetary distributor credit limit.
        if "credit limit" in normalized and "credit period" not in normalized:
            return RetrievalResult([], {}, False)

        q_tokens = tokens(normalized)
        bm_scores = np.asarray(self.bm25.get_scores(q_tokens), dtype=float)
        q_vec = self.model.encode([normalized], normalize_embeddings=True)[0]
        semantic = self.embeddings @ q_vec

        # Rank fusion avoids mixing incomparable BM25 and cosine score scales.
        active = [i for i, c in enumerate(self.clauses) if c.status == "current"]
        bm_order = sorted(active, key=lambda i: bm_scores[i], reverse=True)
        sem_order = sorted(active, key=lambda i: semantic[i], reverse=True)
        fused: dict[int, float] = {}
        for rank, idx in enumerate(bm_order[:self.top_k * 2], start=1):
            fused[idx] = fused.get(idx, 0.0) + 1.0 / (60 + rank)
        for rank, idx in enumerate(sem_order[:self.top_k * 2], start=1):
            fused[idx] = fused.get(idx, 0.0) + 1.0 / (60 + rank)

        ranked = sorted(fused, key=fused.get, reverse=True)
        selected = ranked[:self.top_k]
        # Nested rule: for MT discount, include the governing section and its
        # revision subclause even if only one was in the top-k.
        q = normalized
        if ("modern trade" in q or "mt" in q) and ("discount" in q or "margin" in q):
            for i, c in enumerate(self.clauses):
                if c.status == "current" and c.section in {"3", "3.1"} and i not in selected:
                    selected.append(i)
        # Exact-string queries get a deterministic lexical safety net.
        exact_markers = ["12%", "10%", "8%", "rs 1 lakh", "rupees 1 lakh",
                         "rs 5 lakh", "rupees 5 lakh", "rs 50,000", "rupees 50 000",
                         "rs 5,000", "rupees 5 000", "21 days", "30 days", "rsm", "asm"]
        if any(m in question.lower() for m in exact_markers):
            for i in active:
                if any(m.replace("rs ", "").replace("rupees ", "") in self.clauses[i].text.lower()
                       for m in exact_markers):
                    if i not in selected and any(tok in self.clauses[i].text.lower() for tok in q_tokens):
                        selected.append(i)
        selected = list(dict.fromkeys(selected))
        clauses = [self.clauses[i] for i in selected if self.clauses[i].status == "current"]
        scores = {self.clauses[i].clause_id: float(fused.get(i, 0.0)) for i in selected}
        return RetrievalResult(clauses, scores, False)
