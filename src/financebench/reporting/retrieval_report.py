"""The retrieval-ablation report: does better retrieval produce better answers?

The report keeps three things apart that a single "RAG accuracy" number welds together, and the whole
value of the exercise is in the separation:

1. **Retrieval performance** — did the right page get retrieved? (No model involved. Cheap.)
2. **Generation given retrieval** — when the page *was* retrieved, did the model then use it?
3. **End-to-end** — did the user get the right answer?

A RAG system can fail at (1) or at (2), and the fixes are opposite: a retrieval miss needs a better
index, and a generation failure needs a better model. A single end-to-end score cannot tell you which
you have, so it reliably sends you to rebuild the component that was working.
"""

from __future__ import annotations

import html
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

__all__ = ["ArmResult", "write_ablation_report"]


@dataclass(frozen=True)
class ArmResult:
    """One retrieval arm, with its generation outcome attached when a live run exists for it."""

    name: str
    retriever: str
    top_k: int
    scope: str
    page_recall: float
    document_recall: float
    mrr: float
    ndcg: float
    mean_query_ms: float

    #: Present only for arms that were actually GENERATED against. Retrieval metrics are cheap and
    #: exist for every arm; answer accuracy costs ~110 s/sample and exists only where we paid for it.
    #: `None` here means "not run", and it is never rendered as a zero.
    run_id: str | None = None
    answer_accuracy: float | None = None
    n_generated: int | None = None
    unsupported_claim_rate: float | None = None
    retrieval_misses: int | None = None
    generation_errors_after_retrieval: int | None = None
    refusal_rate: float | None = None


def _cell(value: float | None, fmt: str = "{:.3f}") -> str:
    return "—" if value is None else fmt.format(value)


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{value * 100:.1f}%"


def write_ablation_report(
    out_dir: str | Path,
    *,
    arms: list[ArmResult],
    cells: list[dict[str, Any]],
    corpus: dict[str, Any],
    index_build_ms: dict[str, float],
    finding: str,
    paired: dict[str, Any] | None = None,
) -> None:
    """Write ``report.html``, ``summary.md``, ``results.json`` and ``results.csv``."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    payload = {
        "corpus": corpus,
        "index_build_ms": {k: round(v, 1) for k, v in index_build_ms.items()},
        "cells": cells,
        "arms": [
            {
                "name": a.name,
                "retriever": a.retriever,
                "top_k": a.top_k,
                "scope": a.scope,
                "page_recall": a.page_recall,
                "document_recall": a.document_recall,
                "mrr": a.mrr,
                "ndcg": a.ndcg,
                "mean_query_ms": a.mean_query_ms,
                "run_id": a.run_id,
                "answer_accuracy": a.answer_accuracy,
                "n_generated": a.n_generated,
                "unsupported_claim_rate": a.unsupported_claim_rate,
                "retrieval_misses": a.retrieval_misses,
                "generation_errors_after_retrieval": a.generation_errors_after_retrieval,
                "refusal_rate": a.refusal_rate,
            }
            for a in arms
        ],
        "paired_comparisons": paired or {},
        "finding": finding,
    }
    (out / "results.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    # -- CSV: every cell, so the raw grid is re-analysable without parsing our prose.
    lines = [
        "retriever,top_k,document_scoped,n_scored,document_recall,page_recall,mrr,ndcg,"
        "evidence_f1,mean_query_ms"
    ]
    for c in cells:
        lines.append(
            f"{c['retriever']},{c['top_k']},{c['document_scoped']},{c['n_scored']},"
            f"{c['document_recall']},{c['page_recall']},{c['mrr']},{c['ndcg']},"
            f"{c['evidence_f1']},{c['mean_query_ms']}"
        )
    (out / "results.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # -- Markdown
    md = [
        "# Retrieval ablation — FinanceBench",
        "",
        f"Corpus: **{corpus['pages']:,} pages** across **{corpus['documents']} filings** "
        f"(fingerprint `{corpus['fingerprint']}`).",
        "",
        "## 1. Retrieval performance (no model in the loop)",
        "",
        "| retriever | scope | k | page recall | doc recall | MRR | nDCG | query ms |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for c in cells:
        scope = "doc-scoped" if c["document_scoped"] else "open-corpus"
        md.append(
            f"| {c['retriever']} | {scope} | {c['top_k']} | {c['page_recall'] * 100:.1f}% "
            f"| {c['document_recall'] * 100:.1f}% | {c['mrr']:.3f} | {c['ndcg']:.3f} "
            f"| {c['mean_query_ms']:.0f} |"
        )

    md += [
        "",
        "Index build time (full corpus): "
        + ", ".join(f"**{k}** {v / 1000:.1f}s" for k, v in index_build_ms.items()),
        "",
        "## 2. Does better retrieval produce better answers?",
        "",
        "Retrieval metrics are cheap — no model runs. **Answer accuracy is not**: at 109.5 s/sample "
        "on this hardware, each generated arm is ~4.6 GPU-hours. So every arm below has retrieval "
        "numbers, and only the arms we paid to generate have answer numbers. A dash means **not "
        "run** — never zero.",
        "",
        "| arm | page recall | answer accuracy | n | unsupported claims | retrieval misses "
        "| gen-fail-after-retrieval |",
        "|---|---|---|---|---|---|---|",
    ]
    for a in arms:
        md.append(
            f"| {a.name} | {_pct(a.page_recall)} | {_pct(a.answer_accuracy)} "
            f"| {a.n_generated or '—'} | {_pct(a.unsupported_claim_rate)} "
            f"| {a.retrieval_misses if a.retrieval_misses is not None else '—'} "
            f"| {a.generation_errors_after_retrieval if a.generation_errors_after_retrieval is not None else '—'} |"
        )

    if paired:
        md += ["", "## 3. Paired comparisons (same sample ids, bootstrap CI)", ""]
        for key, value in paired.items():
            md.append(f"- **{key}**: {value.get('verdict', '')}")

    md += ["", "## Finding", "", finding, ""]
    (out / "summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    # -- HTML
    rows = "\n".join(
        f"<tr><td>{html.escape(a.name)}</td><td>{_pct(a.page_recall)}</td>"
        f"<td>{_pct(a.answer_accuracy)}</td><td>{a.n_generated or '&mdash;'}</td>"
        f"<td>{_pct(a.unsupported_claim_rate)}</td></tr>"
        for a in arms
    )
    cell_rows = "\n".join(
        f"<tr><td>{html.escape(c['retriever'])}</td>"
        f"<td>{'doc-scoped' if c['document_scoped'] else 'open-corpus'}</td>"
        f"<td>{c['top_k']}</td><td>{c['page_recall'] * 100:.1f}%</td>"
        f"<td>{c['document_recall'] * 100:.1f}%</td><td>{c['mrr']:.3f}</td>"
        f"<td>{c['ndcg']:.3f}</td><td>{c['mean_query_ms']:.0f}</td></tr>"
        for c in cells
    )
    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Retrieval ablation — FinanceBench</title>
<style>
 body {{ font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
        max-width: 1100px; margin: 2rem auto; color: #1a1a1a; line-height: 1.5; }}
 table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
 th, td {{ border: 1px solid #ddd; padding: .45rem .7rem; text-align: left; }}
 th {{ background: #f4f4f4; }}
 .finding {{ background: #fff8e1; border-left: 4px solid #f0ad4e; padding: 1rem; }}
</style></head><body>
<h1>Retrieval ablation — FinanceBench</h1>
<p>Corpus: <strong>{corpus["pages"]:,} pages</strong> across <strong>{corpus["documents"]}</strong>
filings (fingerprint <code>{html.escape(str(corpus["fingerprint"]))}</code>).</p>

<h2>1. Retrieval performance (no model in the loop)</h2>
<table><tr><th>retriever</th><th>scope</th><th>k</th><th>page recall</th><th>doc recall</th>
<th>MRR</th><th>nDCG</th><th>query ms</th></tr>
{cell_rows}
</table>

<h2>2. Does better retrieval produce better answers?</h2>
<p>Retrieval metrics are cheap. Answer accuracy is not &mdash; ~4.6 GPU-hours per generated arm on
this hardware. A dash means <strong>not run</strong>, never zero.</p>
<table><tr><th>arm</th><th>page recall</th><th>answer accuracy</th><th>n</th>
<th>unsupported claims</th></tr>
{rows}
</table>

<h2>Finding</h2>
<div class="finding">{html.escape(finding)}</div>
</body></html>
"""
    (out / "report.html").write_text(doc, encoding="utf-8")
