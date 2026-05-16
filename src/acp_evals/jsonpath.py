from __future__ import annotations

from typing import Any


def get_path(payload: Any, path: str) -> Any:
    """Read a small dot/bracket JSON path, for example result.reply or items[0].name."""
    current = payload
    for token in _tokens(path):
        if isinstance(token, int):
            if not isinstance(current, list) or token >= len(current):
                raise KeyError(path)
            current = current[token]
            continue
        if not isinstance(current, dict) or token not in current:
            raise KeyError(path)
        current = current[token]
    return current


def _tokens(path: str) -> list[str | int]:
    tokens: list[str | int] = []
    for part in path.split("."):
        rest = part
        while rest:
            if "[" not in rest:
                tokens.append(rest)
                break
            before, after = rest.split("[", 1)
            if before:
                tokens.append(before)
            index, suffix = after.split("]", 1)
            tokens.append(int(index))
            rest = suffix
    return tokens
