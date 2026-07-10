from __future__ import annotations

import financebench


def test_version_is_a_nonempty_string() -> None:
    assert isinstance(financebench.__version__, str)
    assert financebench.__version__
