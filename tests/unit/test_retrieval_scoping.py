"""`document_scoped` must actually scope the document.

For a long time it did not. The setting left the retriever searching all 12,013 pages and merely
pasted the document's name onto the front of the query — so a run artifact stamped
``document_scoped: true`` while nothing whatsoever had been scoped. The label described a setting the
code never entered, and every number produced under it belonged to a different experiment.

The bug is invisible from the inside: the run completes, the artifact looks right, and the score is
plausible. It was caught by an ablation, which produced *exactly* the same page recall (4.0 % @ k=10)
for "document-scoped" as for open-corpus — because they were the same thing.

Truly scoped, the same retriever gets **18.7 %**. Nearly five times better, and the model never
changed.

These tests pin the property that a mislabelled setting cannot come back quietly:
a scoped retrieval must be **incapable** of returning a page from another filing.
"""

from __future__ import annotations

from financebench.prompts.profiles import (
    RetrievedChunk,  # noqa: F401  (keeps the import graph honest)
)
from financebench.retrieval.corpus import Page, PageCorpus
from financebench.retrieval.pipeline import RetrievalPipeline
from financebench.retrieval.retriever import BM25Retriever
from financebench.schemas.common import AnswerType, SplitOrigin
from financebench.schemas.sample import (
    CanonicalSample,
    EvaluationSpec,
    GoldAnswer,
    SampleContext,
    SourceInfo,
)


def _corpus() -> PageCorpus:
    """Two filings. The word "capex" appears in BOTH, and the DISTRACTOR's page says it far more
    often — so an unscoped BM25 will rank the wrong filing's page first, every time."""
    pages = [
        Page(document_id="ACME_2018_10K", page=7, text="capital expenditure was 1234 million"),
        Page(document_id="ACME_2018_10K", page=8, text="unrelated segment disclosure"),
        Page(
            document_id="DISTRACTOR_2020_10K",
            page=1,
            text="capital expenditure capital expenditure capital expenditure 9999",
        ),
        Page(document_id="DISTRACTOR_2020_10K", page=2, text="more capital expenditure noise"),
    ]
    return PageCorpus(pages)


def _sample() -> CanonicalSample:
    return CanonicalSample(
        benchmark="financebench",
        benchmark_version="test",
        split="open_source",
        split_origin=SplitOrigin.PUBLIC_SUBSET,
        sample_id="financebench:open_source:1",
        task_family="grounded_qa",
        capability_tags=("evidence_grounding",),
        question="What was the capital expenditure?",
        context=SampleContext(),
        gold=GoldAnswer(answer="1234", answer_type=AnswerType.NUMERIC, numeric_value=1234.0),
        evaluation=EvaluationSpec(),
        source=SourceInfo(license="CC-BY-4.0", url="https://example.com", redistributable=True),
        metadata={"doc_name": "ACME_2018_10K"},
    )


def _pipeline(*, document_scoped: bool) -> RetrievalPipeline:
    corpus = _corpus()
    return RetrievalPipeline(
        corpus=corpus,
        retriever=BM25Retriever(corpus),
        top_k=2,
        document_scoped=document_scoped,
        results={},
        make_retriever=BM25Retriever,
    )


def test_an_unscoped_retrieval_can_return_the_wrong_filing() -> None:
    """The baseline, and the reason the setting exists at all. Over the whole corpus, the loudest
    page wins — and the loudest page is in the wrong filing."""
    _, result = _pipeline(document_scoped=False).retrieve_for(_sample())
    assert "DISTRACTOR_2020_10K" in result.documents


def test_a_scoped_retrieval_cannot_return_another_filings_page_at_all() -> None:
    """Not "is unlikely to" — **cannot**. The corpus it searches does not contain them.

    This is what the setting always claimed and never did. A test that merely asserted the right page
    ranked first would have passed under the old query-augmentation hack too, on an easy fixture, and
    the bug would have survived.
    """
    _, result = _pipeline(document_scoped=True).retrieve_for(_sample())

    assert result.documents == {"ACME_2018_10K"}
    assert "DISTRACTOR_2020_10K" not in result.documents
    assert all(hit.page.document_id == "ACME_2018_10K" for hit in result.pages)


def test_scoping_finds_the_gold_page_the_open_corpus_buries() -> None:
    _, result = _pipeline(document_scoped=True).retrieve_for(_sample())
    assert "ACME_2018_10K#p7" in result.chunk_ids


def test_the_query_is_the_question_and_nothing_is_pasted_onto_it() -> None:
    """The old implementation prepended the document's name to the query. With the corpus genuinely
    narrowed that is not merely unnecessary, it is harmful: every page of a 10-K mentions the
    company, so the company name is pure noise for choosing *between* its pages."""
    seen: list[str] = []

    corpus = _corpus()

    class Recorder(BM25Retriever):
        def retrieve(self, query: str, *, top_k: int = 5):  # type: ignore[no-untyped-def]
            seen.append(query)
            return super().retrieve(query, top_k=top_k)

    pipeline = RetrievalPipeline(
        corpus=corpus,
        retriever=Recorder(corpus),
        top_k=2,
        document_scoped=True,
        results={},
        make_retriever=Recorder,
    )
    sample = _sample()
    pipeline.retrieve_for(sample)

    assert seen == [sample.question]
    assert "ACME" not in seen[0], "the document name must not be pasted onto the query"


def test_a_scoped_retriever_is_built_once_per_document_not_once_per_question() -> None:
    """A 160-page BM25 index is cheap. Rebuilding it for all 150 questions would not be."""
    built: list[int] = []

    def counting_factory(corpus: PageCorpus) -> BM25Retriever:
        built.append(len(corpus))
        return BM25Retriever(corpus)

    corpus = _corpus()
    pipeline = RetrievalPipeline(
        corpus=corpus,
        retriever=BM25Retriever(corpus),
        top_k=2,
        document_scoped=True,
        results={},
        make_retriever=counting_factory,
    )
    for _ in range(5):
        pipeline.retrieve_for(_sample())

    assert len(built) == 1, "the scoped retriever must be cached, not rebuilt per question"


def test_the_retrieval_version_is_in_the_fingerprint() -> None:
    """The scoping fix moves every retrieval_required score without the model changing. If it did not
    change the fingerprint, an old run and a new one would sit next to each other on a leaderboard
    claiming to be the same experiment."""
    from financebench.evaluation.fingerprint import RETRIEVAL_VERSION, current_fingerprint

    assert RETRIEVAL_VERSION == "2"
    assert current_fingerprint().retrieval_version == "2"
    assert "retrieval_version" in current_fingerprint().to_json()
