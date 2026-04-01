"""Minimal subset of the ``respx`` API used in the test-suite."""
from __future__ import annotations

import asyncio
import functools
from contextlib import AbstractAsyncContextManager, AbstractContextManager
from typing import Callable, List, Optional

import httpx
from httpx import URL

__all__ = ["mock", "get"]


class _Route:
    def __init__(self, method: str, url: str) -> None:
        self.method = method.upper()
        self.url = URL(url)
        self.response: Optional[httpx.Response] = None

    def mock(self, *, return_value: httpx.Response) -> "_Route":
        self.response = return_value
        return self

    def matches(self, method: str, url: URL) -> bool:
        if self.method != method.upper():
            return False
        if self.url.host != url.host:
            return False
        if self.url.scheme != url.scheme:
            return False
        return url.path.startswith(self.url.path)


class _Mock(AbstractAsyncContextManager, AbstractContextManager):
    def __init__(self) -> None:
        self._routes: List[_Route] = []
        self._original_request: Optional[Callable] = None

    # Route registration -------------------------------------------------
    def add(self, method: str, url: str) -> _Route:
        route = _Route(method, url)
        self._routes.append(route)
        return route

    def _match(self, method: str, url: str) -> Optional[_Route]:
        target = URL(str(url))
        for route in reversed(self._routes):
            if route.matches(method, target):
                return route
        return None

    # Patching -----------------------------------------------------------
    def _patch(self) -> None:
        if self._original_request is not None:
            return
        self._original_request = httpx.AsyncClient.request

        async def fake_request(client: httpx.AsyncClient, method: str, url: str, *args, **kwargs):
            route = self._match(method, url)
            if route and route.response is not None:
                original = route.response
                request = httpx.Request(method, str(url))
                response = httpx.Response(
                    status_code=original.status_code,
                    headers=original.headers,
                    content=original.content,
                    request=request,
                )
                return response
            assert self._original_request is not None  # for mypy
            return await self._original_request(client, method, url, *args, **kwargs)

        httpx.AsyncClient.request = fake_request  # type: ignore[assignment]

    def _unpatch(self) -> None:
        if self._original_request is None:
            return
        httpx.AsyncClient.request = self._original_request  # type: ignore[assignment]
        self._original_request = None
        self._routes.clear()

    # Context manager protocol ------------------------------------------
    def __enter__(self) -> "_Mock":
        global _CURRENT_MOCK
        _CURRENT_MOCK = self
        self._patch()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        global _CURRENT_MOCK
        _CURRENT_MOCK = None
        self._unpatch()
        return None

    async def __aenter__(self) -> "_Mock":
        return self.__enter__()

    async def __aexit__(self, exc_type, exc, tb) -> None:
        self.__exit__(exc_type, exc, tb)

    # Decorator ----------------------------------------------------------
    def __call__(self, func):
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                async with self:
                    return await func(*args, **kwargs)

            return async_wrapper

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with self:
                return func(*args, **kwargs)

        return wrapper


_CURRENT_MOCK: Optional[_Mock] = None


def mock(func: Optional[Callable] = None):
    """Return a decorator/context manager mimicking ``respx.mock``."""

    router = _Mock()
    if func is not None:
        return router(func)
    return router


def get(url: str) -> _Route:
    if _CURRENT_MOCK is None:
        raise RuntimeError("respx.get() must be used inside a respx.mock context")
    return _CURRENT_MOCK.add("GET", url)
