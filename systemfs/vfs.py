"""SystemFS — Virtual File System with mount-based resolver dispatch."""
from __future__ import annotations
from typing import Any

from .base import BaseResolver
from .models import VFSNode, VFSResult, VFSOperation, NodeKind
from .sandbox import Sandbox


class SystemFS:
    """
    Virtual File System.

    Usage:
        fs = SystemFS()
        fs.mount("/docs/", DocsResolver(docs_root))
        fs.mount("/graph/", GraphResolver(graph))
        result = fs.read("/docs/charges/create-charge.md")
    """

    def __init__(self):
        self._mounts: dict[str, BaseResolver] = {}
        self._history = None  # optional HistoryLayer, set via attach_history()

    def attach_history(self, history) -> None:
        self._history = history

    def mount(self, mount_point: str, resolver: BaseResolver) -> None:
        key = Sandbox.normalize(mount_point).rstrip("/") + "/"
        self._mounts[key] = resolver

    def unmount(self, mount_point: str) -> None:
        key = Sandbox.normalize(mount_point).rstrip("/") + "/"
        self._mounts.pop(key, None)

    def list_mounts(self) -> dict[str, str]:
        return {mp: r.name for mp, r in self._mounts.items()}

    def read(self, path: str) -> VFSResult:
        resolver, local_path = self._resolve(path)
        if resolver is None:
            result = VFSResult(success=False, operation=VFSOperation.READ,
                               path=path, error=f"No resolver mounted for {path}")
        else:
            result = resolver.read(local_path)
        self._log("read", path, result)
        return result

    def write(self, path: str, content: str, metadata: dict[str, Any] | None = None) -> VFSResult:
        resolver, local_path = self._resolve(path)
        if resolver is None:
            result = VFSResult(success=False, operation=VFSOperation.WRITE,
                               path=path, error=f"No resolver mounted for {path}")
        elif resolver.readonly:
            result = VFSResult(success=False, operation=VFSOperation.WRITE,
                               path=path, error=f"Resolver '{resolver.name}' is read-only")
        else:
            result = resolver.write(local_path, content, metadata)
        self._log("write", path, result)
        return result

    def list(self, path: str = "/") -> VFSResult:
        norm = Sandbox.normalize(path)
        if norm == "/":
            seen: set[str] = set()
            children: list[VFSNode] = []
            for mp in self._mounts:
                top = mp.strip("/").split("/")[0]
                vpath = f"/{top}/"
                if vpath not in seen:
                    seen.add(vpath)
                    children.append(VFSNode(path=vpath, kind=NodeKind.DIRECTORY, name=top))
            result = VFSResult(success=True, operation=VFSOperation.LIST, path="/", data=children)
        else:
            resolver, local_path = self._resolve(path)
            if resolver is None:
                result = VFSResult(success=False, operation=VFSOperation.LIST,
                                   path=path, error=f"No resolver mounted for {path}")
            else:
                result = resolver.list(local_path)
        self._log("list", path, result)
        return result

    def search(self, query: str, path: str = "/", max_results: int = 10) -> VFSResult:
        norm = Sandbox.normalize(path)
        if norm == "/":
            all_nodes: list[VFSNode] = []
            for resolver in self._mounts.values():
                r = resolver.search(query, "/", max_results)
                if r.success and r.data:
                    nodes = r.data if isinstance(r.data, list) else [r.data]
                    all_nodes.extend(nodes)
            result = VFSResult(success=True, operation=VFSOperation.SEARCH,
                               path="/", data=all_nodes[:max_results])
        else:
            resolver, local_path = self._resolve(path)
            if resolver is None:
                result = VFSResult(success=False, operation=VFSOperation.SEARCH,
                                   path=path, error=f"No resolver mounted for {path}")
            else:
                result = resolver.search(query, local_path, max_results)
        self._log("search", path, result)
        return result

    def exec(self, path: str, args: dict[str, Any] | None = None) -> VFSResult:
        resolver, local_path = self._resolve(path)
        if resolver is None:
            result = VFSResult(success=False, operation=VFSOperation.EXEC,
                               path=path, error=f"No resolver mounted for {path}")
        else:
            result = resolver.exec(local_path, args)
        self._log("exec", path, result)
        return result

    def _resolve(self, path: str) -> tuple[BaseResolver | None, str]:
        """Longest-prefix match to find resolver."""
        norm = Sandbox.normalize(path)
        best_mount = ""
        best_resolver: BaseResolver | None = None
        for mp, resolver in self._mounts.items():
            mp_stripped = mp.rstrip("/")
            if (norm == mp_stripped or norm.startswith(mp)) and len(mp) > len(best_mount):
                best_mount = mp
                best_resolver = resolver
        if best_resolver is None:
            return None, norm
        local = Sandbox.relative_to_mount(norm, best_mount)
        return best_resolver, local

    def _log(self, op: str, path: str, result: VFSResult) -> None:
        if self._history is not None:
            self._history.log(
                event_type=op, actor="system", path=path,
                data={"success": result.success, "error": result.error},
            )
