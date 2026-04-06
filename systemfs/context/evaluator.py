"""Context Evaluator — validates LLM output against VFS sources."""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

from ..models import ContextManifest, MemoryEntry

if TYPE_CHECKING:
    from ..vfs import SystemFS

CONFIDENCE_THRESHOLD = 0.7
NEEDS_REVIEW_TAG = "needs_review"


class ContextEvaluator:
    """
    Closes the feedback loop:
    - High-confidence facts -> /context/memory/fact/
    - Low-confidence outputs -> tagged "needs_review"
    """

    def __init__(self, vfs: "SystemFS"):
        self._vfs = vfs

    def evaluate(self, output: str, manifest: ContextManifest) -> list[MemoryEntry]:
        """
        Extract factual claims from output, score confidence against VFS sources,
        and write to memory. Returns list of MemoryEntry objects created.
        """
        # Read source material for verification
        sources: list[str] = []
        for path in manifest.selected_paths:
            r = self._vfs.read(path)
            if r.success and r.data and r.data.content:
                sources.append(r.data.content)

        claims = self._extract_claims(output)
        created: list[MemoryEntry] = []

        for i, claim in enumerate(claims):
            confidence = self._score_confidence(claim, sources)
            key = f"claim-{abs(hash(claim)) % 100000:05d}"
            memory_type = "fact" if confidence >= CONFIDENCE_THRESHOLD else "episodic"
            tags = [] if confidence >= CONFIDENCE_THRESHOLD else [NEEDS_REVIEW_TAG]

            # Write to VFS memory
            write_path = f"/{memory_type}/{key}"
            self._vfs.write(
                f"/context/memory{write_path}",
                claim,
                {
                    "confidence": confidence,
                    "source_paths": manifest.selected_paths,
                    "tags": tags,
                },
            )

            created.append(MemoryEntry(
                key=key,
                content=claim,
                memory_type=memory_type,
                confidence=confidence,
                source_paths=manifest.selected_paths,
                tags=tags,
            ))

        return created

    def _extract_claims(self, text: str) -> list[str]:
        """Extract factual sentences from text (simple heuristic)."""
        # Split on sentence boundaries
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        # Filter to likely factual claims (not questions, not very short)
        claims = [
            s.strip() for s in sentences
            if len(s.strip()) > 20 and not s.strip().endswith("?")
            and not s.strip().startswith("I ")
        ]
        return claims[:10]  # cap to prevent noise

    def _score_confidence(self, claim: str, sources: list[str]) -> float:
        """Score how well a claim is supported by source content (keyword overlap)."""
        if not sources:
            return 0.5

        claim_words = set(re.findall(r"\b\w{4,}\b", claim.lower()))
        if not claim_words:
            return 0.5

        max_overlap = 0.0
        for source in sources:
            source_words = set(re.findall(r"\b\w{4,}\b", source.lower()))
            if not source_words:
                continue
            overlap = len(claim_words & source_words) / len(claim_words)
            max_overlap = max(max_overlap, overlap)

        return min(1.0, max_overlap)
