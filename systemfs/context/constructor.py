"""Context Constructor — queries VFS, ranks artifacts, builds context manifest."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from ..models import VFSNode, ContextManifest

if TYPE_CHECKING:
    from ..vfs import SystemFS


class ContextConstructor:
    """
    Queries the VFS for query-relevant artifacts, scores them by freshness/
    similarity/trust, selects within a token budget, and produces a ContextManifest.
    """

    def __init__(self, vfs: "SystemFS", max_tokens: int = 8000):
        self._vfs = vfs
        self._max_tokens = max_tokens

    def build_context(self, query: str, hints: list[str] | None = None) -> ContextManifest:
        """
        Search VFS for relevant nodes, score and rank them, select within budget.
        Returns a ContextManifest describing what was selected.
        """
        candidates: list[VFSNode] = []

        # Search across all resolvers
        search_result = self._vfs.search(query, "/", max_results=20)
        if search_result.success and search_result.data:
            nodes = search_result.data if isinstance(search_result.data, list) else [search_result.data]
            candidates.extend(nodes)

        # Add hint paths directly
        if hints:
            for hint_path in hints:
                r = self._vfs.read(hint_path)
                if r.success and r.data:
                    candidates.append(r.data)

        # Deduplicate by path
        seen: set[str] = set()
        unique: list[VFSNode] = []
        for node in candidates:
            if node.path not in seen:
                seen.add(node.path)
                unique.append(node)

        # Score each candidate
        freshness: dict[str, float] = {}
        similarity: dict[str, float] = {}
        trust: dict[str, float] = {}

        for node in unique:
            freshness[node.path] = self._score_freshness(node)
            similarity[node.path] = self._score_similarity(node, query)
            trust[node.path] = self._score_trust(node)

        # Rank by composite score
        def composite(path: str) -> float:
            return 0.3 * freshness[path] + 0.5 * similarity[path] + 0.2 * trust[path]

        ranked = sorted(unique, key=lambda n: composite(n.path), reverse=True)

        # Select within token budget
        selected: list[str] = []
        total_tokens = 0
        for node in ranked:
            content_len = len(node.content or "")
            tokens = self.estimate_tokens(node.content or "")
            if total_tokens + tokens > self._max_tokens and selected:
                break
            selected.append(node.path)
            total_tokens += tokens

        return ContextManifest(
            selected_paths=selected,
            total_tokens_estimate=total_tokens,
            freshness_scores={p: freshness[p] for p in selected},
            similarity_scores={p: similarity[p] for p in selected},
            trust_scores={p: trust[p] for p in selected},
            compression_ratio=total_tokens / max(self._max_tokens, 1),
        )

    def materialize(self, manifest: ContextManifest) -> str:
        """
        Read all selected paths from VFS, concatenate with section headers.
        Returns a string ready for LLM injection.
        """
        sections: list[str] = []
        for path in manifest.selected_paths:
            result = self._vfs.read(path)
            if result.success and result.data and result.data.content:
                header = f"### [{path}]"
                sections.append(f"{header}\n{result.data.content}")

        if not sections:
            return ""

        header = f"<!-- Context manifest: {len(manifest.selected_paths)} sources, "
        header += f"~{manifest.total_tokens_estimate} tokens -->"
        return header + "\n\n" + "\n\n---\n\n".join(sections)

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Rough estimate: ~4 chars per token."""
        return max(1, len(text) // 4)

    def _score_freshness(self, node: VFSNode) -> float:
        """Score 0-1: newer = higher. Memory entries decay slower."""
        if node.provenance is None:
            return 0.5
        age_seconds = (datetime.now(timezone.utc) - node.provenance.modified_at.replace(
            tzinfo=timezone.utc if node.provenance.modified_at.tzinfo is None else None
        )).total_seconds() if node.provenance.modified_at.tzinfo else (
            datetime.utcnow() - node.provenance.modified_at
        ).total_seconds()
        # Decay over 24 hours
        return max(0.0, 1.0 - age_seconds / 86400)

    def _score_similarity(self, node: VFSNode, query: str) -> float:
        """Score 0-1: keyword overlap between query and node content/name."""
        q_words = set(query.lower().split())
        target = ((node.content or "") + " " + node.name).lower()
        matches = sum(1 for w in q_words if w in target)
        return min(1.0, matches / max(len(q_words), 1))

    def _score_trust(self, node: VFSNode) -> float:
        """Score 0-1: from provenance.confidence, default 0.8 for docs, 0.6 for memory."""
        if node.provenance:
            return node.provenance.confidence
        if "/docs/" in node.path:
            return 0.8
        if "/memory/" in node.path:
            return 0.6
        return 0.7
