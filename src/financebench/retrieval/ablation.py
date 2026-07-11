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
TOP_KS = (5, 10, 20)


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
        }


def _score_cell(
    samples: Sequence[CanonicalSample],
    results: dict[str, RetrievalResult],
    *,
    retriever: str,
    top_k: int,
    document_scoped: bool,
) -> AblationCell:
    """Grade one k by **truncating** a deeper retrieval, rather than re-running it.

    The top 5 of a ranked list of 20 *is* the top 5 — a retriever asked for 5 would return exactly
    those. So one retrieval at the deepest k answers every shallower k for free, and the ablation
    costs one pass instead of three.
    """
    scores = []
    for sample in samples:
        result = results.get(sample.sample_id)
        if result is None:
            continue
        truncated = RetrievalResult(
            pages=result.pages[:top_k], retriever=result.retriever, top_k=top_k
        )
        scores.append(score_retrieval(sample, truncated))

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
    for retriever_name in retrievers:
        factory = make_retriever_factory(
            corpus,
            retriever_name=retriever_name,
            pdf_dir=pdf_dir,
            embed_cache_dir=embed_cache_dir,
        )
        full = factory(corpus)

        for document_scoped in scopings:
            scoped_cache: dict[str, object] = {}
            results: dict[str, RetrievalResult] = {}

            for sample in samples:
                retriever = full
                if document_scoped:
                    document = sample.metadata.get("doc_name", "")
                    if document:
                        if document not in scoped_cache:
                            scoped_cache[document] = factory(corpus.scoped_to({document}))
                        retriever = scoped_cache[document]  # type: ignore[assignment]
                # The retriever is handed the question and nothing else — no sample, so no gold.
                results[sample.sample_id] = retriever.retrieve(sample.question, top_k=deepest)

            for top_k in top_ks:
                cells.append(
                    _score_cell(
                        samples,
                        results,
                        retriever=retriever_name,
                        top_k=top_k,
                        document_scoped=document_scoped,
                    )
                )
            if callable(on_progress):
                on_progress(retriever_name, document_scoped)

    return cells
