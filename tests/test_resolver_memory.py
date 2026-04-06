"""Tests for MemoryResolver."""
import pytest
from pathlib import Path
from systemfs.resolvers.memory import MemoryResolver
from systemfs.models import VFSOperation


@pytest.fixture
def resolver(tmp_path):
    return MemoryResolver(tmp_path)


def test_write_and_read_fact(resolver):
    w = resolver.write("/fact/api-key-auth", "API keys are used for authentication",
                       {"confidence": 0.9, "tags": ["auth"]})
    assert w.success

    r = resolver.read("/fact/api-key-auth")
    assert r.success
    assert "API keys" in r.data.content


def test_write_episodic(resolver):
    r = resolver.write("/episodic/session-001",
                       "User asked about charge creation flow")
    assert r.success


def test_write_procedural(resolver):
    r = resolver.write("/procedural/create-charge",
                       "1. Authenticate. 2. POST /v1/charges. 3. Handle response.")
    assert r.success


def test_write_invalid_type(resolver):
    r = resolver.write("/unknown_type/key", "content")
    assert not r.success


def test_list_root(resolver):
    r = resolver.list("/")
    assert r.success
    names = {n.name for n in r.data}
    assert "fact" in names
    assert "episodic" in names
    assert "procedural" in names


def test_list_by_type(resolver):
    resolver.write("/fact/k1", "content 1")
    resolver.write("/fact/k2", "content 2")
    r = resolver.list("/fact/")
    assert r.success
    assert len(r.data) >= 2


def test_search(resolver):
    resolver.write("/fact/charge-info", "Charges represent payment transactions")
    r = resolver.search("payment")
    assert r.success
    assert len(r.data) >= 1


def test_persistence(tmp_path):
    r1 = MemoryResolver(tmp_path)
    r1.write("/fact/persistent-key", "This should persist across instances")

    r2 = MemoryResolver(tmp_path)
    r = r2.read("/fact/persistent-key")
    assert r.success
    assert "persist" in r.data.content


def test_access_count_increments(resolver):
    resolver.write("/fact/counter-test", "test content")
    resolver.read("/fact/counter-test")
    r = resolver.read("/fact/counter-test")
    import json
    data = json.loads(r.data.content)
    assert data["access_count"] >= 1
