"""Assembles a retriever for a run, and grades what it found afterwards.

This is the seam between the retrieval package (which knows about pages and BM25 and nothing about
benchmarks) and the orchestration layer (which knows about runs and nothing about PDFs).

Two retrieval settings are supported and reported separately, because they answer different
questions and averaging them would flatter whichever is easier:

- **open-corpus** — the retriever searches every page of every filing (~12,000 pages). This is the
  honest hard setting: the system must work out *which company's filing* as well as which page.
- **document-scoped** — the question already names the filing, so the corpus is narrowed to it and
  the job is to find the right **page** within a 160-page document. This is the setting a real
  deployment usually has, because a user asking about 3M's 2018 capex is not asking you to guess
  the company.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from financebench.prompts.profiles import RetrievedChunk
from financebench.retrieval.corpus import PageCorpus, build_corpus
from financebench.retrieval.embeddings import OllamaEmbedder, build_embeddings
from financebench.retrieval.retriever import (
    BM25Retriever,
    DenseRetriever,
    HybridRetriever,
    RetrievalResult,
    Retriever,
)
from financebench.schemas.sample import CanonicalSample

__all__ = [
    "RetrievalPipeline",
    "RetrieverFactory",
    "build_pipeline",
    "make_retriever_factory",
]


#: Builds a retriever over a corpus. Held as a factory rather than a built retriever so the
#: document-scoped setting can build one per filing without knowing which kind it is.
RetrieverFactory = Callable[[PageCorpus], Retriever]


@dataclass
class RetrievalPipeline:
    """Everything a retrieval-mode run needs, plus the record of what it did."""

    corpus: PageCorpus
    retriever: Retriever
    top_k: int
    document_scoped: bool
    #: sample_id -> what the retriever returned. Populated during the run, graded after it.
    results: dict[str, RetrievalResult]
    #: Rebuilds the same *kind* of retriever over a narrowed corpus, for the document-scoped setting.
    make_retriever: RetrieverFactory | None = None
    #: document_id -> a retriever over that document's pages alone. Built lazily, then reused: a
    #: 160-page BM25 index is cheap, but rebuilding it once per question would not be.
    _scoped: dict[str, Retriever] = field(default_factory=dict)

    @property
    def fingerprint(self) -> str:
        return self.corpus.fingerprint

    def to_json(self) -> dict[str, object]:
        return {
            "retriever": self.retriever.name,
            "top_k": self.top_k,
            "document_scoped": self.document_scoped,
            "corpus_pages": len(self.corpus),
            "corpus_documents": len(self.corpus.documents),
            "index_fingerprint": self.fingerprint,
        }

    def _retriever_for(self, document_id: str) -> Retriever:
        """A retriever over one filing's pages only.

        This is what ``document_scoped`` is supposed to mean, and for a long time it did not mean it.
        The setting used to leave the retriever searching all 12,013 pages and merely paste the
        document's name onto the front of the query — so a run artifact stamped
        ``document_scoped: true`` while nothing had been scoped at all. The label described a setting
        the code never entered.

        Narrowing the corpus is the whole point: a user asking about 3M's 2018 capex is not asking
        the system to guess the company. Scoped, the job is to find one page in ~160; unscoped, one
        page in 12,013. Those are different problems and they get different numbers.
        """
        if document_id not in self._scoped:
            scoped_corpus = self.corpus.scoped_to({document_id})
            factory = self.make_retriever or BM25Retriever
            self._scoped[document_id] = factory(scoped_corpus)
        return self._scoped[document_id]

    def retrieve_for(
        self, sample: CanonicalSample
    ) -> tuple[tuple[RetrievedChunk, ...], RetrievalResult]:
        """Retrieve for one sample.

        **Only the question text is ever used as the query.** Not the gold evidence, not the gold
        answer, not the justification — the retriever is handed exactly what a user would type, and
        it is handed no sample at all, so there is nothing on it to reach.

        In the document-scoped setting the *corpus* is narrowed to the filing the question names.
        That is a restriction on where to look, not a hint about what to find: it says "the answer is
        somewhere in 3M's 2018 10-K", which the question already said, and it says nothing whatsoever
        about which of its 160 pages.
        """
        retriever = self.retriever
        if self.document_scoped:
            document = sample.metadata.get("doc_name", "")
            if document:
                retriever = self._retriever_for(document)

        result = retriever.retrieve(sample.question, top_k=self.top_k)
        self.results[sample.sample_id] = result
        return result.to_chunks(), result


def build_pipeline(
    samples: list[CanonicalSample],
    *,
    pdf_dir: str | Path,
    retriever_name: str = "bm25",
    top_k: int = 5,
    document_scoped: bool = False,
    embed_cache_dir: str | Path | None = None,
) -> RetrievalPipeline:
    """Build the corpus and retriever a run needs.

    The corpus covers every document any sample in the run refers to. In the open-corpus setting
    that is the whole ~12,000-page collection — which is the point: the retriever has to find one
    page in it.
    """
    documents = {
        sample.metadata.get("doc_name", "") for sample in samples if sample.metadata.get("doc_name")
    }
    corpus = build_corpus(pdf_dir, documents=documents or None)
    factory = make_retriever_factory(
        corpus, retriever_name=retriever_name, pdf_dir=pdf_dir, embed_cache_dir=embed_cache_dir
    )

    return RetrievalPipeline(
        corpus=corpus,
        retriever=factory(corpus),
        top_k=top_k,
        document_scoped=document_scoped,
        results={},
        make_retriever=factory,
    )


def make_retriever_factory(
    corpus: PageCorpus,
    *,
    retriever_name: str = "bm25",
    pdf_dir: str | Path,
    embed_cache_dir: str | Path | None = None,
) -> RetrieverFactory:
    """A factory that builds ``retriever_name`` over *any* corpus — the full one, or one filing's.

    The embeddings are computed once, over the **whole** corpus, and then simply *filtered* when a
    narrowed corpus asks for them. Re-embedding a filing's pages every time it is scoped would cost
    12,013 embedding calls all over again for no new information: a page's vector does not depend on
    which pages it is sitting next to.
    """
    if retriever_name == "bm25":
        return BM25Retriever

    if retriever_name not in ("dense", "hybrid"):
        raise ValueError(f"unknown retriever {retriever_name!r}; expected bm25 | dense | hybrid")

    embedder = OllamaEmbedder()
    if not embedder.available():
        # Silently degrading to BM25 while still calling itself "dense" would be a lie in the run
        # artifacts. Say what actually happened.
        raise RuntimeError(
            f"retriever={retriever_name!r} needs the '{embedder.model}' embedding model, which "
            "Ollama does not have. Run: ollama pull nomic-embed-text — or use --retriever bm25."
        )
    cache = Path(embed_cache_dir or Path(pdf_dir).parent / "embed_cache")
    vectors = build_embeddings(corpus, embedder, cache_dir=cache)

    def build(scoped: PageCorpus) -> Retriever:
        subset = {
            page.chunk_id: vectors[page.chunk_id]
            for page in scoped.pages
            if page.chunk_id in vectors
        }
        dense = DenseRetriever(scoped, subset)
        dense.set_query_embedder(embedder.embed)
        if retriever_name == "dense":
            return dense
        return HybridRetriever(BM25Retriever(scoped), dense)

    return build
