"""Tests for HistoryLayer."""
import pytest
from pathlib import Path
from systemfs.context.history import HistoryLayer


@pytest.fixture
def history(tmp_path):
    return HistoryLayer(tmp_path)


def test_start_session_creates_file(history, tmp_path):
    session_id = history.start_session()
    assert session_id
    files = list((tmp_path / "history").glob("*.jsonl"))
    assert len(files) == 1


def test_log_entry(history):
    history.start_session()
    history.log("query", "user", path="/docs/auth.md", data={"q": "auth methods"})
    entries = history.query_history()
    assert any(e.event_type == "query" for e in entries)


def test_query_history_by_event_type(history):
    history.start_session()
    history.log("read", "system", path="/docs/auth.md")
    history.log("write", "agent", path="/context/memory/fact/k1")
    history.log("read", "system", path="/graph/nodes/Charge")

    read_entries = history.query_history(event_type="read")
    assert all(e.event_type == "read" for e in read_entries)
    assert len(read_entries) >= 2


def test_query_history_by_session(tmp_path):
    h = HistoryLayer(tmp_path)
    sid1 = h.start_session()
    h.log("event1", "user")
    sid2 = h.start_session()
    h.log("event2", "user")

    entries1 = h.query_history(session_id=sid1)
    entries2 = h.query_history(session_id=sid2)
    assert all(e.session_id == sid1 for e in entries1)
    assert all(e.session_id == sid2 for e in entries2)


def test_auto_start_session_on_first_log(history):
    # No explicit start_session call
    history.log("implicit", "system")
    assert history.session_id != ""
    entries = history.query_history()
    assert len(entries) >= 1


def test_jsonl_format(history, tmp_path):
    history.start_session()
    history.log("test_event", "user", data={"key": "value"})
    files = list((tmp_path / "history").glob("*.jsonl"))
    lines = files[0].read_text().strip().splitlines()
    import json
    for line in lines:
        obj = json.loads(line)
        assert "event_type" in obj
        assert "timestamp" in obj
