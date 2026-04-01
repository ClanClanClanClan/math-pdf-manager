"""Lightweight numpy substitute providing the minimal API used in tests."""
from __future__ import annotations

from typing import Iterable, Sequence

__all__ = ["array"]


class _Array(list):
    def __init__(self, data: Iterable[float]):
        super().__init__(float(x) for x in data)

    def tolist(self) -> list[float]:
        return list(self)


def array(values: Sequence[float] | Iterable[float], dtype: object | None = None) -> _Array:
    return _Array(values)


__version__ = "0.0.stub"
