"""ModuleResolver — extensible external API mount skeleton."""
from __future__ import annotations
from typing import Any, Callable
from ..base import BaseResolver
from ..models import VFSNode, VFSResult, VFSOperation, NodeKind


class ModuleResolver(BaseResolver):
    """
    Extensible resolver for external API mounts.
    Register handlers per sub-path name.

    Example:
        mod = ModuleResolver()
        mod.register("github", GitHubHandler())
        fs.mount("/modules/", mod)
    """

    _name = "modules"

    def __init__(self):
        self._modules: dict[str, Any] = {}

    @property
    def name(self) -> str:
        return self._name

    @property
    def readonly(self) -> bool:
        return True

    def register_module(self, name: str, handler: Any) -> None:
        """Register a handler for a sub-path."""
        self._modules[name] = handler

    def read(self, path: str) -> VFSResult:
        handler, sub_path = self._get_handler(path)
        if handler is None:
            return self._not_configured(VFSOperation.READ, path)
        if hasattr(handler, "read"):
            return handler.read(sub_path)
        return VFSResult(success=False, operation=VFSOperation.READ,
                         path=path, error=f"Handler for {path} does not support read")

    def write(self, path: str, content: str, metadata: dict[str, Any] | None = None) -> VFSResult:
        return VFSResult(success=False, operation=VFSOperation.WRITE,
                         path=path, error="modules resolver is read-only")

    def list(self, path: str) -> VFSResult:
        parts = [p for p in path.strip("/").split("/") if p]
        if not parts:
            nodes = [VFSNode(path=f"/modules/{name}/", kind=NodeKind.DIRECTORY, name=name)
                     for name in sorted(self._modules)]
            return VFSResult(success=True, operation=VFSOperation.LIST, path=path, data=nodes)
        handler, sub_path = self._get_handler(path)
        if handler is None:
            return self._not_configured(VFSOperation.LIST, path)
        if hasattr(handler, "list"):
            return handler.list(sub_path)
        return VFSResult(success=False, operation=VFSOperation.LIST,
                         path=path, error=f"Handler for {path} does not support list")

    def search(self, query: str, path: str = "/", max_results: int = 10) -> VFSResult:
        parts = [p for p in path.strip("/").split("/") if p]
        if not parts:
            return VFSResult(success=True, operation=VFSOperation.SEARCH, path=path, data=[])
        handler, sub_path = self._get_handler(path)
        if handler is None:
            return self._not_configured(VFSOperation.SEARCH, path)
        if hasattr(handler, "search"):
            return handler.search(query, sub_path, max_results)
        return VFSResult(success=True, operation=VFSOperation.SEARCH, path=path, data=[])

    def exec(self, path: str, args: dict[str, Any] | None = None) -> VFSResult:
        handler, sub_path = self._get_handler(path)
        if handler is None:
            return self._not_configured(VFSOperation.EXEC, path)
        if hasattr(handler, "exec"):
            return handler.exec(sub_path, args)
        return VFSResult(success=False, operation=VFSOperation.EXEC,
                         path=path, error=f"Handler for {path} does not support exec")

    def _get_handler(self, path: str) -> tuple[Any | None, str]:
        parts = [p for p in path.strip("/").split("/") if p]
        if not parts:
            return None, "/"
        module_name = parts[0]
        sub_path = "/" + "/".join(parts[1:]) if len(parts) > 1 else "/"
        return self._modules.get(module_name), sub_path

    def _not_configured(self, op: VFSOperation, path: str) -> VFSResult:
        parts = [p for p in path.strip("/").split("/") if p]
        module_name = parts[0] if parts else path
        return VFSResult(success=False, operation=op, path=path,
                         error=f"Module '{module_name}' not configured. Use register_module() to add it.")
