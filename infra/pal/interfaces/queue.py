from __future__ import annotations
from abc import ABC, abstractmethod


class QueueProvider(ABC):
    @abstractmethod
    def enqueue(self, queue_name: str, payload: dict) -> str:
        """Enqueue a message. Returns message ID."""

    @abstractmethod
    def ping(self) -> bool:
        """Return True if the queue backend is reachable."""
