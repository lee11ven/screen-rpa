from __future__ import annotations

import threading
from collections import deque
from typing import Protocol

class Broker(Protocol):
    def push(self, payload: str) -> None: ...
    def pop_blocking(self, timeout_sec: float) -> str | None: ...


class MemoryBroker:
    def __init__(self) -> None:
        self._q: deque[str] = deque()
        self._cv = threading.Condition()

    def push(self, payload: str) -> None:
        with self._cv:
            self._q.append(payload)
            self._cv.notify()

    def pop_blocking(self, timeout_sec: float) -> str | None:
        with self._cv:
            if not self._q:
                self._cv.wait(timeout=timeout_sec)
            if not self._q:
                return None
            return self._q.popleft()


_broker_singleton: Broker | None = None
_broker_lock = threading.Lock()


def get_broker() -> Broker:
    global _broker_singleton
    with _broker_lock:
        if _broker_singleton is None:
            _broker_singleton = MemoryBroker()
        return _broker_singleton


def reset_broker_for_tests() -> None:
    global _broker_singleton
    with _broker_lock:
        _broker_singleton = None
