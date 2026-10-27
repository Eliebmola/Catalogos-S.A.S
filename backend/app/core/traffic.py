"""Lightweight in-process abuse controls for public endpoints and request bodies."""
from __future__ import annotations

import asyncio
import time
from collections import deque

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class InMemoryRateLimiter:
    """Fixed-window sliding event limiter; state is bounded and shared by app requests."""

    def __init__(self, max_keys: int = 20_000) -> None:
        self._events: dict[str, deque[float]] = {}
        self._max_keys = max_keys
        self._lock = asyncio.Lock()

    async def allow(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        now = time.monotonic()
        async with self._lock:
            events = self._events.get(key)
            if events is None:
                if len(self._events) >= self._max_keys:
                    cutoff = now - window_seconds
                    stale = [name for name, values in self._events.items() if not values or values[-1] <= cutoff]
                    for name in stale:
                        self._events.pop(name, None)
                    if len(self._events) >= self._max_keys:
                        return False, window_seconds
                events = deque()
                self._events[key] = events
            cutoff = now - window_seconds
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= limit:
                return False, max(1, int(window_seconds - (now - events[0])))
            events.append(now)
            return True, 0


class RequestBodyLimitMiddleware:
    """Reject oversized HTTP bodies from their declared length before route parsing."""

    def __init__(self, app: ASGIApp, max_bytes: int = 4 * 1024 * 1024) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            headers = {key.lower(): value for key, value in scope.get("headers", [])}
            length = headers.get(b"content-length")
            if length:
                try:
                    too_large = int(length) > self.max_bytes
                except ValueError:
                    too_large = True
                if too_large:
                    response = JSONResponse(
                        status_code=413,
                        content={"error": "La solicitud supera el tamaño permitido.", "code": 413, "type": "request_too_large"},
                    )
                    await response(scope, receive, send)
                    return
        await self.app(scope, receive, send)
