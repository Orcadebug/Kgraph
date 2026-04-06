"""MemoryResolver — writable persistent knowledge store."""
from __future__ import annotations
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from ..base import BaseResolver
from ..models import VFSNode, VFSResult, VFSOperation, NodeKind, Provenance, MemoryEntry

MEMORY_TYPES = ("fact", "episodic", "procedural")


class MemoryResolver(BaseResolver):
    """Manages persistent memory entries in data/memory/."""

    _name = "memory"

    def __init__(self, data_root: str | Path):
        self._root = Path(data_root) / "memory"
        self._root.mkdir(parents=True, exist_ok=True)
        for sub in MEMORY_TYPES:
            (self._root / sub).mkdir(exist_ok=True)
        self._index: dict[str, MemoryEntry] = {}
        self._load_index()

    @property
    def name(self) -> str:
        return self._name

    @property
    def readonly(self) -> bool:
        return False

    def read(self, path: str) -> VFSResult:
        parts = [p for p in path.strip("/").split("/") if p]
        if not parts:
            return self.list(path)
        if len(parts) == 1 and parts[0] in MEMORY_TYPES:
            return self.list(path)
        if len(parts) == 2:
            mem_type, key = parts
            entry_key = f"{mem_type}/{key}"
            entry = self._index.get(entry_key)
            if entry is None:
                return VFSResult(success=False, operation=VFSOperation.READ,
                                 path=path, error=f"Memory entry not found: {entry_key}")
            entry.last_accessed = datetime.utcnow()
            entry.access_count += 1
            self._save_entry(entry)
            content = json.dumps(entry.model_dump(), indent=2, default=str)
            node = VFSNode(
                path=f"/context/memory/{entry_key}", kind=NodeKind.FILE, name=key,
                content=content, size=len(content),
                provenance=Provenance(source="memory", origin_path=entry_key,
                                      confidence=entry.confidence),
            )
            return VFSResult(success=True, operation=VFSOperation.READ, path=path, data=node)
        return VFSResult(success=False, operation=VFSOperation.READ,
                         path=path, error=f"Invalid memory path: {path}")

    def write(self, path: str, content: str, metadata: dict[str, Any] | None = None) -> VFSResult:
        parts = [p for p in path.strip("/").split("/") if p]
        if len(parts) != 2:
            return VFSResult(success=False, operation=VFSOperation.WRITE,
                             path=path, error=f"Memory write path must be /type/key, got: {path}")
        mem_type, key = parts
        if mem_type not in MEMORY_TYPES:
            return VFSResult(success=False, operation=VFSOperation.WRITE,
                             path=path, error=f"Unknown memory type: {mem_type}. Must be one of {MEMORY_TYPES}")
        meta = metadata or {}
        entry_key = f"{mem_type}/{key}"
        existing = self._index.get(entry_key)
        entry = MemoryEntry(
            key=key,
            content=content,
            memory_type=mem_type,
            confidence=meta.get("confidence", 1.0),
            source_paths=meta.get("source_paths", []),
            tags=meta.get("tags", []),
            created_at=existing.created_at if existing else datetime.utcnow(),
            last_accessed=datetime.utcnow(),
            access_count=(existing.access_count + 1) if existing else 0,
        )
        self._index[entry_key] = entry
        self._save_entry(entry)
        node = VFSNode(path=f"/context/memory/{entry_key}", kind=NodeKind.FILE, name=key,
                       content=content, size=len(content))
        return VFSResult(success=True, operation=VFSOperation.WRITE, path=path, data=node)

    def list(self, path: str) -> VFSResult:
        parts = [p for p in path.strip("/").split("/") if p]
        if not parts:
            nodes = [VFSNode(path=f"/context/memory/{t}/", kind=NodeKind.DIRECTORY, name=t)
                     for t in MEMORY_TYPES]
            return VFSResult(success=True, operation=VFSOperation.LIST, path=path, data=nodes)
        if len(parts) == 1 and parts[0] in MEMORY_TYPES:
            mem_type = parts[0]
            nodes = [
                VFSNode(path=f"/context/memory/{mem_type}/{e.key}", kind=NodeKind.FILE, name=e.key)
                for ek, e in self._index.items() if ek.startswith(f"{mem_type}/")
            ]
            return VFSResult(success=True, operation=VFSOperation.LIST, path=path, data=nodes)
        return VFSResult(success=False, operation=VFSOperation.LIST,
                         path=path, error=f"Invalid memory list path: {path}")

    def search(self, query: str, path: str = "/", max_results: int = 10) -> VFSResult:
        q = query.lower()
        parts = [p for p in path.strip("/").split("/") if p]
        mem_type_filter = parts[0] if parts and parts[0] in MEMORY_TYPES else None

        results: list[VFSNode] = []
        for entry_key, entry in self._index.items():
            if mem_type_filter and not entry_key.startswith(f"{mem_type_filter}/"):
                continue
            if q in entry.content.lower() or q in entry.key.lower() or any(q in t for t in entry.tags):
                results.append(VFSNode(
                    path=f"/context/memory/{entry_key}", kind=NodeKind.FILE, name=entry.key,
                    metadata={"memory_type": entry.memory_type, "confidence": entry.confidence,
                              "tags": entry.tags},
                    provenance=Provenance(source="memory", origin_path=entry_key,
                                          confidence=entry.confidence),
                ))
        return VFSResult(success=True, operation=VFSOperation.SEARCH, path=path,
                         data=results[:max_results])

    def _load_index(self) -> None:
        for json_file in self._root.rglob("*.json"):
            try:
                data = json.loads(json_file.read_text())
                entry = MemoryEntry(**data)
                rel = json_file.relative_to(self._root)
                entry_key = str(rel.with_suffix(""))
                self._index[entry_key] = entry
            except Exception:
                pass

    def _save_entry(self, entry: MemoryEntry) -> None:
        sub_dir = self._root / entry.memory_type
        sub_dir.mkdir(exist_ok=True)
        file_path = sub_dir / f"{_safe_key(entry.key)}.json"
        file_path.write_text(json.dumps(entry.model_dump(), indent=2, default=str))
        self._index[f"{entry.memory_type}/{entry.key}"] = entry


def _safe_key(key: str) -> str:
    return re.sub(r"[^\w\-]", "_", key)[:100]
