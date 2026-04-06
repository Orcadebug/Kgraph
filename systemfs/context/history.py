"""History layer — append-only JSONL interaction log."""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from ..models import HistoryEntry


class HistoryLayer:
    """
    Append-only JSON-lines log of all VFS interactions.
    One file per session: data/history/{date}_{session_id}.jsonl
    """

    def __init__(self, data_root: str | Path):
        self._root = Path(data_root) / "history"
        self._root.mkdir(parents=True, exist_ok=True)
        self._session_id: str = ""
        self._current_file: Path | None = None

    def start_session(self) -> str:
        """Open a new log file for this session. Returns session_id."""
        self._session_id = str(uuid.uuid4())[:8]
        date_str = datetime.utcnow().strftime("%Y%m%d")
        fname = f"{date_str}_{self._session_id}.jsonl"
        self._current_file = self._root / fname
        self.log("session_start", "system", data={"session_id": self._session_id})
        return self._session_id

    @property
    def session_id(self) -> str:
        return self._session_id

    def log(self, event_type: str, actor: str, path: str | None = None,
            data: dict[str, Any] | None = None) -> None:
        """Append a HistoryEntry as a JSON line."""
        if not self._session_id:
            self.start_session()
        entry = HistoryEntry(
            event_type=event_type, actor=actor, path=path,
            data=data or {}, session_id=self._session_id,
        )
        self._write_entry(entry)

    def query_history(
        self,
        session_id: str | None = None,
        event_type: str | None = None,
        limit: int = 100,
    ) -> list[HistoryEntry]:
        """Read back history entries with optional filters."""
        entries: list[HistoryEntry] = []
        files = sorted(self._root.glob("*.jsonl"), reverse=True)
        for file in files:
            if session_id and session_id not in file.name:
                continue
            try:
                for line in file.read_text().splitlines():
                    if not line.strip():
                        continue
                    try:
                        raw = json.loads(line)
                        entry = HistoryEntry(**raw)
                        if event_type and entry.event_type != event_type:
                            continue
                        if session_id and entry.session_id != session_id:
                            continue
                        entries.append(entry)
                        if len(entries) >= limit:
                            return entries
                    except Exception:
                        pass
            except Exception:
                pass
        return entries

    def _write_entry(self, entry: HistoryEntry) -> None:
        if self._current_file is None:
            return
        line = json.dumps(entry.model_dump(), default=str) + "\n"
        with self._current_file.open("a") as f:
            f.write(line)
