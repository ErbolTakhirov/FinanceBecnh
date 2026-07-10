# FinQA test fixture

`test.json` is a curated slice of 17 records (out of the official test split's 1,147) — named to
match the real download's split-based filenames (`train.json`/`dev.json`/`test.json`) so this
directory doubles as a drop-in `data_dir` for `FinQAAdapter`, exercising the exact same load path
a real prepared download would.
from the [FinQA dataset](https://github.com/czyssrs/FinQA) (Chen et al., EMNLP 2021,
[aclanthology.org/2021.emnlp-main.300](https://aclanthology.org/2021.emnlp-main.300/)),
redistributed here under the same terms as the official repository: MIT license (code) / CC BY
4.0 (data, via the FinTabNet/CDLA-Permissive provenance chain — see
[`docs/research/benchmark_review.md`](../../../docs/research/benchmark_review.md)).

Selected to cover every native operation type (`add`, `subtract`, `multiply`, `divide`, `exp`,
`greater`, `table_max`, `table_min`, `table_sum`, `table_average`) including both single-step and
multi-step (`#N`-chained) programs and `const_*` literal handling — used by
`tests/datasets/test_finqa_e2e.py` to prove the adapter and program executor against real data,
not synthetic approximations of it. This is a test fixture, not the full dataset — use
`financebench prepare finqa` to fetch the complete official train/dev/test splits.
