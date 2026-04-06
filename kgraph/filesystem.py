"""
FileSystem — flat document operations (list, search, read).
"""
import re
from pathlib import Path
from typing import Any


class FileSystem:
    def __init__(self, docs_root: str | Path):
        self.root = Path(docs_root)

    def list_files(self) -> list[dict[str, str]]:
        """Return all markdown files with relative paths."""
        files = []
        for path in sorted(self.root.rglob("*.md")):
            files.append({
                "path": str(path.relative_to(self.root)),
                "name": path.stem,
                "title": self._extract_title(path),
            })
        return files

    def read_file(self, relative_path: str) -> str | None:
        """Read a doc file. Returns content or None if not found."""
        full = self.root / relative_path
        if not full.exists() or not full.is_file():
            return None
        return full.read_text()

    def search(self, query: str, max_results: int = 10) -> list[dict[str, Any]]:
        """Keyword search across all docs. Returns matches with context."""
        q = query.lower()
        results = []
        for path in sorted(self.root.rglob("*.md")):
            content = path.read_text()
            content_lower = content.lower()
            if q not in content_lower:
                continue
            # Find all match positions for context
            snippets = []
            for m in re.finditer(re.escape(q), content_lower):
                start = max(0, m.start() - 80)
                end = min(len(content), m.end() + 80)
                snippet = content[start:end].replace("\n", " ").strip()
                snippets.append(snippet)
                if len(snippets) >= 3:
                    break
            results.append({
                "path": str(path.relative_to(self.root)),
                "title": self._extract_title(path),
                "match_count": content_lower.count(q),
                "snippets": snippets,
            })
        results.sort(key=lambda x: x["match_count"], reverse=True)
        return results[:max_results]

    def _extract_title(self, path: Path) -> str:
        try:
            for line in path.read_text().splitlines():
                line = line.strip()
                if line.startswith("# "):
                    return line[2:]
        except Exception:
            pass
        return path.stem
