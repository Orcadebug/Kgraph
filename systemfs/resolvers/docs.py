"""DocsResolver — wraps kgraph.filesystem.FileSystem."""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from pathlib import Path
from typing import Any
from ..base import BaseResolver
from ..models import VFSNode, VFSResult, VFSOperation, NodeKind, Provenance
from kgraph.filesystem import FileSystem


class DocsResolver(BaseResolver):
    """Adapts the flat docs filesystem into the VFS hierarchy."""

    _name = "docs"

    def __init__(self, docs_root: str | Path):
        self._fs = FileSystem(docs_root)
        self._root = Path(docs_root)

    @property
    def name(self) -> str:
        return self._name

    @property
    def readonly(self) -> bool:
        return True

    def read(self, path: str) -> VFSResult:
        rel = path.lstrip("/")
        content = self._fs.read_file(rel)
        if content is None:
            return VFSResult(success=False, operation=VFSOperation.READ,
                             path=path, error=f"File not found: {rel}")
        node = VFSNode(
            path=f"/docs/{rel}", kind=NodeKind.FILE, name=Path(rel).name,
            content=content, size=len(content),
            provenance=Provenance(source="docs", origin_path=rel),
        )
        return VFSResult(success=True, operation=VFSOperation.READ, path=path, data=node)

    def write(self, path: str, content: str, metadata: dict[str, Any] | None = None) -> VFSResult:
        return VFSResult(success=False, operation=VFSOperation.WRITE,
                         path=path, error="docs resolver is read-only")

    def list(self, path: str) -> VFSResult:
        rel_dir = path.lstrip("/")
        target = self._root / rel_dir if rel_dir else self._root
        if not target.exists():
            return VFSResult(success=False, operation=VFSOperation.LIST,
                             path=path, error=f"Path not found: {rel_dir}")
        nodes: list[VFSNode] = []
        if target.is_dir():
            for child in sorted(target.iterdir()):
                rel = str(child.relative_to(self._root))
                vpath = f"/docs/{rel}"
                kind = NodeKind.DIRECTORY if child.is_dir() else NodeKind.FILE
                nodes.append(VFSNode(path=vpath, kind=kind, name=child.name))
        return VFSResult(success=True, operation=VFSOperation.LIST, path=path, data=nodes)

    def search(self, query: str, path: str = "/", max_results: int = 10) -> VFSResult:
        results = self._fs.search(query, max_results)
        nodes = [
            VFSNode(
                path=f"/docs/{r['path']}", kind=NodeKind.FILE, name=r["title"],
                metadata={"match_count": r["match_count"], "snippets": r["snippets"]},
                provenance=Provenance(source="docs", origin_path=r["path"]),
            )
            for r in results
        ]
        return VFSResult(success=True, operation=VFSOperation.SEARCH, path=path, data=nodes)
