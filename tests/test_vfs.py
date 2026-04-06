"""Tests for SystemFS core dispatch engine."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from systemfs.vfs import SystemFS
from systemfs.base import BaseResolver
from systemfs.models import VFSNode, VFSResult, VFSOperation, NodeKind, Provenance


class DictResolver(BaseResolver):
    """Simple in-memory resolver for testing."""
    _name = "dict"
    _readonly = True

    def __init__(self, data: dict[str, str], name: str = "dict"):
        self._data = data
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def readonly(self) -> bool:
        return self._readonly

    def read(self, path: str) -> VFSResult:
        key = path.lstrip("/")
        if key in self._data:
            node = VFSNode(path=path, kind=NodeKind.FILE, name=key,
                           content=self._data[key], size=len(self._data[key]))
            return VFSResult(success=True, operation=VFSOperation.READ, path=path, data=node)
        return VFSResult(success=False, operation=VFSOperation.READ, path=path, error="not found")

    def write(self, path, content, metadata=None):
        return VFSResult(success=False, operation=VFSOperation.WRITE, path=path, error="read-only")

    def list(self, path: str) -> VFSResult:
        nodes = [VFSNode(path=f"/{k}", kind=NodeKind.FILE, name=k) for k in self._data]
        return VFSResult(success=True, operation=VFSOperation.LIST, path=path, data=nodes)

    def search(self, query, path="/", max_results=10) -> VFSResult:
        matches = [VFSNode(path=f"/{k}", kind=NodeKind.FILE, name=k, content=v)
                   for k, v in self._data.items() if query.lower() in v.lower()]
        return VFSResult(success=True, operation=VFSOperation.SEARCH, path=path, data=matches[:max_results])


class WritableDictResolver(DictResolver):
    _readonly = False

    def write(self, path, content, metadata=None):
        key = path.lstrip("/")
        self._data[key] = content
        node = VFSNode(path=path, kind=NodeKind.FILE, name=key, content=content)
        return VFSResult(success=True, operation=VFSOperation.WRITE, path=path, data=node)


def make_fs():
    fs = SystemFS()
    docs = DictResolver({"charges/create.md": "# Create Charge", "auth.md": "# Auth"}, "docs")
    graph = DictResolver({"nodes/Charge": '{"name": "Charge"}', "stats": "59 nodes"}, "graph")
    fs.mount("/docs/", docs)
    fs.mount("/graph/", graph)
    return fs


def test_mount_and_list_mounts():
    fs = make_fs()
    mounts = fs.list_mounts()
    assert "/docs/" in mounts
    assert "/graph/" in mounts

def test_list_root():
    fs = make_fs()
    result = fs.list("/")
    assert result.success
    names = {n.name for n in result.data}
    assert "docs" in names
    assert "graph" in names

def test_read_routed_correctly():
    fs = make_fs()
    r = fs.read("/docs/charges/create.md")
    assert r.success
    assert "Create Charge" in r.data.content

def test_read_graph_routed():
    fs = make_fs()
    r = fs.read("/graph/stats")
    assert r.success
    assert "59" in r.data.content

def test_read_unmounted_path():
    fs = make_fs()
    r = fs.read("/modules/github/issues")
    assert not r.success
    assert "No resolver" in r.error

def test_write_readonly_resolver():
    fs = make_fs()
    r = fs.write("/docs/new.md", "content")
    assert not r.success
    assert "read-only" in r.error

def test_write_writable_resolver():
    fs = SystemFS()
    store = WritableDictResolver({}, "memory")
    fs.mount("/mem/", store)
    r = fs.write("/mem/note.txt", "hello world")
    assert r.success
    r2 = fs.read("/mem/note.txt")
    assert r2.success
    assert r2.data.content == "hello world"

def test_search_root_merges_resolvers():
    fs = make_fs()
    r = fs.search("charge")
    assert r.success
    names = [n.name for n in r.data]
    assert any("charge" in n.lower() for n in names)

def test_unmount():
    fs = make_fs()
    fs.unmount("/docs/")
    assert "/docs/" not in fs.list_mounts()
    r = fs.read("/docs/auth.md")
    assert not r.success

def test_list_delegated():
    fs = make_fs()
    r = fs.list("/docs/")
    assert r.success
    assert isinstance(r.data, list)
