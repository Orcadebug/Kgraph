"""Context Updater — streams context into LLM message window."""
from __future__ import annotations

from typing import TYPE_CHECKING

from .constructor import ContextConstructor
from ..models import ContextManifest

if TYPE_CHECKING:
    from .history import HistoryLayer


_CONTEXT_ROLE_MARKER = "__vfs_context__"


class ContextUpdater:
    """
    Injects the context manifest into an LLM messages list and
    logs all injections as auditable history events.
    """

    def __init__(self, history: "HistoryLayer | None" = None):
        self._history = history

    def inject_context(
        self, messages: list[dict], manifest: ContextManifest, materialized: str
    ) -> list[dict]:
        """
        Insert (or replace) a system context message in messages.
        Returns a new messages list with context injected.
        """
        context_msg = {
            "role": "system",
            "content": materialized,
            "_marker": _CONTEXT_ROLE_MARKER,
        }

        # Replace existing context message if present
        updated = [m for m in messages if m.get("_marker") != _CONTEXT_ROLE_MARKER]
        # Insert after first system message (or at position 1)
        insert_pos = 1
        for i, m in enumerate(updated):
            if m.get("role") == "system":
                insert_pos = i + 1
                break
        updated.insert(insert_pos, context_msg)

        if self._history:
            self._history.log(
                "context_injection", "system",
                data={
                    "num_sources": len(manifest.selected_paths),
                    "tokens": manifest.total_tokens_estimate,
                    "paths": manifest.selected_paths,
                },
            )

        return updated

    def refresh_context(
        self,
        messages: list[dict],
        query: str,
        constructor: ContextConstructor,
        hints: list[str] | None = None,
    ) -> tuple[list[dict], ContextManifest]:
        """Rebuild context for a new query and replace in messages."""
        manifest = constructor.build_context(query, hints)
        materialized = constructor.materialize(manifest)
        updated = self.inject_context(messages, manifest, materialized)
        return updated, manifest
