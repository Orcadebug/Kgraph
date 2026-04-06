"""Abstract base class for all VFS resolvers."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any

from .models import VFSResult, VFSOperation


class BaseResolver(ABC):
    """Interface contract for all VFS resolvers."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def read(self, path: str) -> VFSResult: ...

    @abstractmethod
    def write(self, path: str, content: str, metadata: dict[str, Any] | None = None) -> VFSResult: ...

    @abstractmethod
    def list(self, path: str) -> VFSResult: ...

    @abstractmethod
    def search(self, query: str, path: str = "/", max_results: int = 10) -> VFSResult: ...

    def exec(self, path: str, args: dict[str, Any] | None = None) -> VFSResult:
        return VFSResult(
            success=False, operation=VFSOperation.EXEC, path=path,
            error=f"exec not supported by {self.name} resolver",
        )

    @property
    def readonly(self) -> bool:
        return True
