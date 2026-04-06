"""
Pydantic models for the Virtual File System (SystemFS).
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class NodeKind(str, Enum):
    FILE = "file"
    DIRECTORY = "directory"
    VIRTUAL = "virtual"  # computed/derived nodes (graph queries, etc.)


class Provenance(BaseModel):
    """Tracks where a piece of data came from."""
    source: str               # resolver name, e.g. "docs", "graph", "memory"
    origin_path: str          # original path before mount translation
    created_at: datetime = Field(default_factory=datetime.utcnow)
    modified_at: datetime = Field(default_factory=datetime.utcnow)
    confidence: float = 1.0   # 0.0-1.0, used by context evaluator
    tags: list[str] = []


class VFSNode(BaseModel):
    """Universal node in the virtual file system."""
    path: str                 # absolute VFS path
    kind: NodeKind
    name: str                 # basename
    content: str | None = None  # None for directories
    metadata: dict[str, Any] = {}
    provenance: Provenance | None = None
    children: list[str] = []  # child paths (for directories only)
    size: int = 0


class VFSOperation(str, Enum):
    READ = "read"
    WRITE = "write"
    LIST = "list"
    SEARCH = "search"
    EXEC = "exec"


class VFSResult(BaseModel):
    """Standardized result from any VFS operation."""
    success: bool
    operation: VFSOperation
    path: str
    data: VFSNode | list[VFSNode] | Any = None
    error: str | None = None


class ContextManifest(BaseModel):
    """Describes what context was selected and why."""
    selected_paths: list[str] = []
    total_tokens_estimate: int = 0
    freshness_scores: dict[str, float] = {}
    similarity_scores: dict[str, float] = {}
    trust_scores: dict[str, float] = {}
    compression_ratio: float = 1.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HistoryEntry(BaseModel):
    """Single entry in the append-only history log."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_type: str           # "query", "tool_call", "context_injection", "state_change"
    actor: str                # "user", "agent", "system"
    path: str | None = None   # VFS path involved, if any
    data: dict[str, Any] = {}
    session_id: str = ""


class MemoryEntry(BaseModel):
    """A fact, episode, or procedure stored in memory."""
    key: str                  # unique identifier
    content: str
    memory_type: str          # "fact", "episodic", "procedural"
    confidence: float = 1.0
    source_paths: list[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_accessed: datetime = Field(default_factory=datetime.utcnow)
    access_count: int = 0
    tags: list[str] = []
