"""The retriever ablation: measured without the model, and reported without the losers removed.

The retrieval-mode run attributed its failures, and the attribution is the whole reason this module
exists: of 85 wrong answers, **74 were retrieval misses** — the right page was never put in front of
the model — against **2** where the page WAS retrieved and the model then fumbled it.

That single ratio redirects all the effort. A better model would move almost nothing; the evidence
isn't there to reason over. So the retriever is what gets measured, and it gets measured cheaply:
recall@k needs a query, a corpus, and gold read AFTER the fact. No generation at all.
"""

from __future__ import annotations

from financebench.retrieval.ablation import _score_cell, run_ablation
from financebench.retrieval.corpus import Page, PageCorpus
from financebench.retrieval.retriever import BM25Retriever, RetrievalResult
from financebench.schemas.common import AnswerType, SplitOrigin
from financebench.schemas.sample import (
    CanonicalSample,
    EvaluationSpec,
    Evidence,
    GoldAnswer,
    SampleContext,
    SourceInfo,
)


def _sample(sample_id: str, question: str, doc: str, gold_page: int) -> CanonicalSample:
    return CanonicalSample(
        benchmark="financebench",
        benchmark_version="test",
        split="open_source",
        split_origin=SplitOrigin.PUBLIC_SUBSET,
        sample_id=f"financebench:open_source:{sample_id}",
        task_family="grounded_qa",
        capability_tags=("evidence_grounding",),
        question=question,
        context=SampleContext(),
        gold=GoldAnswer(
            answer="1234",
            answer_type=AnswerType.NUMERIC,
            numeric_value=1234.0,
            evidence=(Evidence(document_id=doc, page=gold_page),),
        ),
        evaluation=EvaluationSpec(),
        source=SourceInfo(license="CC-BY-4.0", url="https://e.com", redistributable=True),
        metadata={"doc_name": doc},
    )


def _corpus() -> PageCorpus:
    return PageCorpus(
        [
            Page(document_id="ACME", page=1, text="revenue segment disclosure"),
            Page(document_id="ACME", page=2, text="capital expenditure was 1234"),
            Page(document_id="ACME", page=3, text="capital lease obligations"),
        ]
    )


def _result(corpus: PageCorpus, query: str, k: int) -> RetrievalResult:
    return BM25Retriever(corpus).retrieve(query, top_k=k)


# --------------------------------------------------------------------------- truncation


def test_a_shallower_k_is_scored_by_truncating_a_deeper_retrieval() -> None:
    """The top 5 of a ranked list of 20 IS the top 5 — a retriever asked for 5 would have returned
    exactly those. So one retrieval at the deepest k answers every shallower k for free, and the
    sweep costs one pass instead of three."""
    corpus = _corpus()
    sample = _sample("1", "capital expenditure", "ACME", 2)
    deep = _result(corpus, sample.question, 3)
    results = {sample.sample_id: deep}

    at_3 = _score_cell([sample], results, retriever="bm25", top_k=3, document_scoped=False)
    at_1 = _score_cell([sample], results, retriever="bm25", top_k=1, document_scoped=False)

    assert at_3.page_recall == 1.0, "the gold page is somewhere in the top 3"
    # Whether it is *first* is a different question, and that is exactly what k=1 measures.
    assert at_1.page_recall in (0.0, 1.0)
    assert at_1.n_scored == at_3.n_scored == 1


def test_precision_falls_as_k_rises_and_recall_does_not() -> None:
    """The trade the ablation exists to expose. Retrieving 20 pages to find one is a real cost — it
    is 20 pages of context the model has to read and 19 chances to be distracted."""
    corpus = _corpus()
    sample = _sample("1", "capital expenditure", "ACME", 2)
    results = {sample.sample_id: _result(corpus, sample.question, 3)}

    shallow = _score_cell([sample], results, retriever="bm25", top_k=1, document_scoped=False)
    deep = _score_cell([sample], results, retriever="bm25", top_k=3, document_scoped=False)

    assert deep.page_recall >= shallow.page_recall
    assert deep.evidence_precision <= shallow.evidence_precision


def test_the_gold_rank_separates_a_ranking_problem_from_an_indexing_one() -> None:
    """A retriever that finds the page and ranks it 18th needs a re-ranker. One that never finds it
    needs a different index. Recall alone cannot tell them apart, and they have opposite fixes."""
    corpus = _corpus()
    sample = _sample("1", "capital expenditure", "ACME", 2)
    results = {sample.sample_id: _result(corpus, sample.question, 3)}

    cell = _score_cell([sample], results, retriever="bm25", top_k=3, document_scoped=False)
    assert cell.mean_gold_rank is not None
    assert cell.mean_gold_rank >= 1


def test_a_retriever_that_never_finds_the_page_reports_no_rank_rather_than_a_zero() -> None:
    """`None` is not rank zero. Rank zero would be the *best possible* result."""
    corpus = _corpus()
    sample = _sample("1", "something entirely absent from this corpus", "ACME", 99)
    results = {sample.sample_id: _result(corpus, sample.question, 3)}

    cell = _score_cell([sample], results, retriever="bm25", top_k=3, document_scoped=False)
    assert cell.page_recall == 0.0
    assert cell.mean_gold_rank is None


# --------------------------------------------------------------------------- the sweep


def test_the_sweep_reports_every_cell_it_was_asked_for(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Every retriever swept is reported, losers included. A retriever chosen by its own benchmark
    and then presented without its rivals is a number with the losing evidence deleted."""
    import json

    # A tiny fake corpus on disk, so the sweep runs without the 12,013-page download.
    cache = tmp_path / "pages"
    cache.mkdir()
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()

    samples = [_sample("1", "capital expenditure", "ACME", 2)]

    # build_corpus reads PDFs; with no PDFs it yields an empty corpus, which is still a valid sweep
    # and must not crash — an empty corpus is a coverage gap, not an exception.
    cells = run_ablation(
        samples, pdf_dir=pdf_dir, retrievers=["bm25"], top_ks=[5, 10], scopings=[False]
    )
    assert len(cells) == 2
    assert {c.top_k for c in cells} == {5, 10}
    assert all(c.retriever == "bm25" for c in cells)
    assert json.dumps([c.to_json() for c in cells])  # serializable for the report


def test_an_unknown_retriever_is_refused_rather_than_silently_becoming_bm25() -> None:
    """Silently degrading to BM25 while still calling itself "dense" would put a lie in the run
    artifacts, and it is the single easiest lie to tell here."""
    import pytest

    from financebench.retrieval.pipeline import make_retriever_factory

    with pytest.raises(ValueError, match="unknown retriever"):
        make_retriever_factory(_corpus(), retriever_name="magic", pdf_dir=".")
