"""Tests for DocsResolver."""
import pytest
from pathlib import Path
from systemfs.resolvers.docs import DocsResolver
from systemfs.models import NodeKind, VFSOperation


@pytest.fixture
def docs_dir(tmp_path):
    (tmp_path / "charges").mkdir()
    (tmp_path / "charges" / "create.md").write_text("# Create Charge\nPOST /v1/charges")
    (tmp_path / "auth.md").write_text("# Authentication\nAPI keys required")
    return tmp_path


@pytest.fixture
def resolver(docs_dir):
    return DocsResolver(docs_dir)


def test_read_existing_file(resolver):
    r = resolver.read("/charges/create.md")
    assert r.success
    assert r.data.content == "# Create Charge\nPOST /v1/charges"
    assert r.data.kind == NodeKind.FILE
    assert r.data.provenance.source == "docs"


def test_read_missing_file(resolver):
    r = resolver.read("/nonexistent.md")
    assert not r.success
    assert "not found" in r.error.lower()


def test_write_is_rejected(resolver):
    r = resolver.write("/new.md", "content")
    assert not r.success
    assert "read-only" in r.error


def test_list_root(resolver):
    r = resolver.list("/")
    assert r.success
    names = {n.name for n in r.data}
    assert "charges" in names
    assert "auth.md" in names


def test_list_subdirectory(resolver):
    r = resolver.list("/charges/")
    assert r.success
    names = {n.name for n in r.data}
    assert "create.md" in names


def test_search_finds_match(resolver):
    r = resolver.search("POST")
    assert r.success
    assert len(r.data) >= 1
    assert any("create" in n.name.lower() or "charges" in n.path for n in r.data)


def test_search_no_match(resolver):
    r = resolver.search("xyznonexistent")
    assert r.success
    assert r.data == []
