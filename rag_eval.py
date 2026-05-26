"""RAG evaluation helpers for CodeMiner/RepoMiner.

Evaluates retrieval layer using a user-provided JSON dataset.

Dataset schema (JSON list):
  {
    "id": "tc-1",
    "question": "How does auth work?",
    "expected_sources": ["src/auth.py", "auth_store.py"],
    "expected_keywords": ["JWT", "cookie"]
  }
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class EvalCase:
    id: str
    question: str
    expected_sources: List[str]
    expected_keywords: List[str]


def load_eval_dataset(raw: bytes) -> List[EvalCase]:
    data = json.loads(raw.decode("utf-8", errors="ignore"))
    if not isinstance(data, list):
        raise ValueError("Dataset must be a JSON list")

    cases: List[EvalCase] = []
    for idx, row in enumerate(data):
        if not isinstance(row, dict):
            continue
        cases.append(EvalCase(
            id=str(row.get("id") or f"case-{idx+1}"),
            question=str(row.get("question") or "").strip(),
            expected_sources=[str(s) for s in (row.get("expected_sources") or []) if str(s).strip()],
            expected_keywords=[str(s) for s in (row.get("expected_keywords") or []) if str(s).strip()],
        ))

    return [c for c in cases if c.question]


def load_vectorstore(persist_directory: str = "./chroma_db"):
    """Load a Chroma vectorstore using the same embeddings as the app."""

    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_chroma import Chroma

    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    return Chroma(persist_directory=persist_directory, embedding_function=embeddings)


def _norm(p: str) -> str:
    return p.replace("\\\\", "/").lstrip("./")


def evaluate_retrieval(vectorstore, cases: List[EvalCase], *, k: int = 6) -> Dict[str, Any]:
    """Evaluate retrieval quality: hit@k, precision@k, recall@k, MRR + latency."""

    per_case: List[Dict[str, Any]] = []

    hit_count = 0
    rr_sum = 0.0
    prec_sum = 0.0
    rec_sum = 0.0
    retrieval_ms: List[float] = []

    for case in cases:
        start = time.perf_counter()
        docs = vectorstore.similarity_search(case.question, k=k)
        elapsed = (time.perf_counter() - start) * 1000.0
        retrieval_ms.append(elapsed)

        retrieved_sources = [_norm((d.metadata.get("source") or "")) for d in docs]
        expected = [_norm(s) for s in (case.expected_sources or [])]
        expected_set = set(expected)

        matches = [s for s in retrieved_sources if s in expected_set] if expected_set else []

        hit = bool(matches) if expected_set else None
        if hit is True:
            hit_count += 1

        rr = 0.0
        if expected_set:
            for i, s in enumerate(retrieved_sources, start=1):
                if s in expected_set:
                    rr = 1.0 / i
                    break
            rr_sum += rr

            precision = len(matches) / max(k, 1)
            recall = len(set(matches)) / max(len(expected_set), 1)
            prec_sum += precision
            rec_sum += recall
        else:
            precision = None
            recall = None

        keyword_hits = 0
        if case.expected_keywords:
            blob = "\n".join((d.page_content or "")[:10_000] for d in docs).lower()
            keyword_hits = sum(1 for kw in case.expected_keywords if kw.lower() in blob)

        per_case.append({
            "id": case.id,
            "question": case.question,
            "retrieved_sources": retrieved_sources,
            "expected_sources": expected,
            "hit_at_k": hit,
            "reciprocal_rank": rr if expected_set else None,
            "precision_at_k": precision,
            "recall_at_k": recall,
            "retrieval_ms": round(elapsed, 2),
            "keyword_hits": keyword_hits,
            "keyword_total": len(case.expected_keywords),
        })

    n = len(cases) or 1
    cases_with_sources = sum(1 for c in cases if c.expected_sources)
    denom = cases_with_sources or 1

    summary = {
        "cases": len(cases),
        "k": k,
        "hit_at_k": round(hit_count / denom, 4) if cases_with_sources else None,
        "mrr": round(rr_sum / denom, 4) if cases_with_sources else None,
        "precision_at_k": round(prec_sum / denom, 4) if cases_with_sources else None,
        "recall_at_k": round(rec_sum / denom, 4) if cases_with_sources else None,
        "avg_retrieval_ms": round(sum(retrieval_ms) / n, 2) if retrieval_ms else None,
        "p95_retrieval_ms": round(sorted(retrieval_ms)[int(0.95 * (len(retrieval_ms) - 1))], 2) if len(retrieval_ms) >= 2 else (retrieval_ms[0] if retrieval_ms else None),
    }

    return {"summary": summary, "cases": per_case}
