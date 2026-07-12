"""Which retriever, and does it matter? Measured without the model.

The retrieval-mode run said something the answer accuracy alone could never have said: of the 85
questions the model got wrong, **74 were retrieval misses** — the right page was never put in front
of it — against **2** where the page *was* retrieved and the model then fumbled it. The bottleneck is
not the model. Fine-tuning it, prompting it better, or swapping it for a bigger one would move almost
nothing, because the evidence isn't there to reason over.

So the retriever is the thing to fix, and this measures it properly.

**Recall@k needs no LLM inference at all.** It needs a query, a corpus, and the gold evidence — and
the gold is read *after* the retrieval, never before. So an ablation across three retrievers, three
values of k, and two scoping settings costs one pass over the corpus and no generation whatsoever.
It is the cheapest question in the platform and it is the one with the most leverage.

**Everything is reported.** A retriever chosen by its own benchmark and then presented without its
rivals is a number with the losing evidence deleted. If dense retrieval turns out to be no better
than BM25 over financial prose — which is entirely possible, because the questions name a company and
a year while the pages are a wall of near-identical tables — then that is the finding, and it means
the corpus is the problem rather than the ranker.
"""

from __future__ import annotations

import math
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from financebench.retrieval.corpus import build_corpus
from financebench.retrieval.metrics import score_retrieval
from financebench.retrieval.pipeline import make_retriever_factory
from financebench.retrieval.retriever import RetrievalResult
from financebench.schemas.sample import CanonicalSample

__all__ = ["AblationCell", "run_ablation"]

RETRIEVERS = ("bm25", "dense", "hybrid")
#: 1 and 3 are free: `_score_cell` grades a shallower k by TRUNCATING the deepest retrieval, so the
#: whole sweep still costs one pass. recall@1 is the number that matters most for a small model with
#: a short context — it is "did the very first page we pasted in contain the answer".
TOP_KS = (1, 3, 5, 10, 20)


@dataclass(frozen=True)
class AblationCell:
    """One (retriever, k, scoping) combination, scored over every question."""

    retriever: str
    top_k: int
    document_scoped: bool
    n_scored: int
    document_recall: float
    page_recall: float
    evidence_precision: float
    evidence_recall: float
    evidence_f1: float
    mean_gold_rank: float | None
    """Where the right page landed, among the questions where it was found at all. A retriever that
    finds the page but ranks it 18th is a different problem from one that never finds it: the first
    needs a re-ranker, the second needs a different index."""
    mrr: float
    """Mean reciprocal rank over ALL questions — a miss contributes 0.

    Deliberately different from ``mean_gold_rank``, which is conditioned on the page being found and
    therefore gets *better* the more questions a retriever fails: a retriever that finds one page,
    at rank 1, has a perfect mean_gold_rank and is useless. MRR cannot be gamed that way."""
    ndcg: float
    """nDCG@k with binary gains. With one gold page it reduces to 1/log2(rank+1), but FinanceBench
    questions can cite several pages, and nDCG is the standard way to say "it found two of the three,
    and it found them early"."""
    mean_query_ms: float
    """Wall-clock per query. Dense is a brute-force cosine over 11,927 vectors in pure Python, and
    that is not free — a retriever that is 3 points better and 40x slower is a different trade."""

    def to_json(self) -> dict[str, object]:
        return {
            "retriever": self.retriever,
            "top_k": self.top_k,
            "document_scoped": self.document_scoped,
            "n_scored": self.n_scored,
            "document_recall": round(self.document_recall, 4),
            "page_recall": round(self.page_recall, 4),
            "evidence_precision": round(self.evidence_precision, 4),
            "evidence_recall": round(self.evidence_recall, 4),
            "evidence_f1": round(self.evidence_f1, 4),
            "mean_gold_rank": None
            if self.mean_gold_rank is None
            else round(self.mean_gold_rank, 2),
            "mrr": round(self.mrr, 4),
            "ndcg": round(self.ndcg, 4),
            "mean_query_ms": round(self.mean_query_ms, 1),
        }


def _ndcg(sample: CanonicalSample, result: RetrievalResult) -> float:
    """nDCG@k with binary relevance: a retrieved page is worth 1 if it is a gold page, else 0."""
    gold = {f"{e.document_id}#p{e.page}" for e in sample.gold.evidence if e.page is not None}
    if not gold:
        return 0.0
    dcg = sum(
        1.0 / math.log2(rank + 1)
        for rank, retrieved in enumerate(result.pages, start=1)
        if retrieved.page.chunk_id in gold
    )
    # The ideal: every gold page packed into the top slots.
    ideal = sum(
        1.0 / math.log2(rank + 1) for rank in range(1, min(len(gold), len(result.pages)) + 1)
    )
    return dcg / ideal if ideal else 0.0


def _score_cell(
    samples: Sequence[CanonicalSample],
    results: dict[str, RetrievalResult],
    *,
    retriever: str,
    top_k: int,
    document_scoped: bool,
    mean_query_ms: float = 0.0,
) -> AblationCell:
    """Grade one k by **truncating** a deeper retrieval, rather than re-running it.

    The top 5 of a ranked list of 20 *is* the top 5 — a retriever asked for 5 would return exactly
    those. So one retrieval at the deepest k answers every shallower k for free, and the ablation
    costs one pass instead of five.
    """
    scores = []
    ndcgs: list[float] = []
    reciprocal_ranks: list[float] = []
    for sample in samples:
        result = results.get(sample.sample_id)
        if result is None:
            continue
        truncated = RetrievalResult(
            pages=result.pages[:top_k], retriever=result.retriever, top_k=top_k
        )
        score = score_retrieval(sample, truncated)
        scores.append(score)
        ndcgs.append(_ndcg(sample, truncated))
        # A miss contributes ZERO, over every question — not "excluded from the average".
        reciprocal_ranks.append(
            1.0 / score.gold_page_rank if score.gold_page_rank is not None else 0.0
        )

    n = len(scores) or 1
    ranks = [s.gold_page_rank for s in scores if s.gold_page_rank is not None]
    return AblationCell(
        retriever=retriever,
        top_k=top_k,
        document_scoped=document_scoped,
        n_scored=len(scores),
        document_recall=sum(s.document_hit for s in scores) / n,
        page_recall=sum(s.page_hit for s in scores) / n,
        evidence_precision=sum(s.evidence_precision for s in scores) / n,
        evidence_recall=sum(s.evidence_recall for s in scores) / n,
        evidence_f1=sum(s.evidence_f1 for s in scores) / n,
        mean_gold_rank=(sum(ranks) / len(ranks)) if ranks else None,
        mrr=sum(reciprocal_ranks) / n,
        ndcg=sum(ndcgs) / n,
        mean_query_ms=mean_query_ms,
    )


def run_ablation(
    samples: Sequence[CanonicalSample],
    *,
    pdf_dir: str | Path,
    retrievers: Sequence[str] = RETRIEVERS,
    top_ks: Sequence[int] = TOP_KS,
    scopings: Sequence[bool] = (False, True),
    embed_cache_dir: str | Path | None = None,
    on_progress: object = None,
) -> list[AblationCell]:
    """Sweep every retriever, k, and scoping. No model is called, and no gold reaches a retriever."""
    documents = {
        sample.metadata.get("doc_name", "") for sample in samples if sample.metadata.get("doc_name")
    }
    corpus = build_corpus(pdf_dir, documents=documents or None)
    deepest = max(top_ks)

    cells: list[AblationCell] = []
    build_ms: dict[str, float] = {}
    for retriever_name in retrievers:
        factory = make_retriever_factory(
            corpus,
            retriever_name=retriever_name,
            pdf_dir=pdf_dir,
            embed_cache_dir=embed_cache_dir,
        )
        # Index-build time over the FULL corpus. Reported, because a retriever is not free before it
        # answers anything: BM25 tokenizes 12,013 pages, and the dense arm must have embedded them.
        started = time.perf_counter()
        full = factory(corpus)
        build_ms[retriever_name] = (time.perf_counter() - started) * 1000

        for document_scoped in scopings:
            scoped_cache: dict[str, object] = {}
            results: dict[str, RetrievalResult] = {}
            query_ms: list[float] = []

            for sample in samples:
                retriever = full
                if document_scoped:
                    document = sample.metadata.get("doc_name", "")
                    if document:
                        if document not in scoped_cache:
                            scoped_cache[document] = factory(corpus.scoped_to({document}))
                        retriever = scoped_cache[document]  # type: ignore[assignment]
                # The retriever is handed the question and nothing else — no sample, so no gold.
                query_started = time.perf_counter()
                results[sample.sample_id] = retriever.retrieve(sample.question, top_k=deepest)
                query_ms.append((time.perf_counter() - query_started) * 1000)

            mean_query_ms = sum(query_ms) / len(query_ms) if query_ms else 0.0
            for top_k in top_ks:
                cells.append(
                    _score_cell(
                        samples,
                        results,
                        retriever=retriever_name,
                        top_k=top_k,
                        document_scoped=document_scoped,
                        mean_query_ms=mean_query_ms,
                    )
                )
            if callable(on_progress):
                on_progress(retriever_name, document_scoped)

    run_ablation.last_index_build_ms = build_ms  # type: ignore[attr-defined]
    run_ablation.last_corpus = {  # type: ignore[attr-defined]
        "pages": len(corpus),
        "documents": len(corpus.documents),
        "fingerprint": corpus.fingerprint,
    }
    return cells
