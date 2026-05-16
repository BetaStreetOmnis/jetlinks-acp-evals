from __future__ import annotations

import pytest

from acp_evals.jsonpath import get_path


def test_get_path_supports_dot_and_list_index() -> None:
    payload = {"result": {"content": [{"text": "ok"}]}}

    assert get_path(payload, "result.content[0].text") == "ok"


def test_get_path_raises_for_missing_path() -> None:
    with pytest.raises(KeyError):
        get_path({"a": {}}, "a.b")
