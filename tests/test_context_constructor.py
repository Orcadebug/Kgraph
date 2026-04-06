"""Tests for ContextConstructor."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from systemfs.vfs import SystemFS
from systemfs.base import BaseResolver
from systemfs.models import VFSNode, VFSResult, VFSOperation, NodeKind, Provenance
from systemfs.context.constructor import ContextConstructor


class StubResolver(BaseResolver):
    _name = "stub"

    def __init__(self, data: dict[str, str], name="stub", mount_prefix="/docs/"):
        self._data = data
        self._name = name
        self._mount_prefix = mount_prefix.rstrip("/")

    @property
    def name(self):
        return self._name

    def _vfs_path(self, key: str) -> str:
        return f"{self._mount_prefix}/{key}"

    def read(self, path):
        key = path.lstrip("/")
        if key in self._data:
            node = VFSNode(path=self._vfs_path(key), kind=NodeKind.FILE, name=key,
                           content=self._data[key],
                           provenance=Provenance(source="stub", origin_path=key))
            return VFSResult(success=True, operation=VFSOperation.READ, path=path, data=node)
        return VFSResult(success=False, operation=VFSOperation.READ, path=path, error="not found")

    def write(self, path, content, metadata=None):
        return VFSResult(success=False, operation=VFSOperation.WRITE, path=path, error="read-only")

    def list(self, path):
        nodes = [VFSNode(path=self._vfs_path(k), kind=NodeKind.FILE, name=k) for k in self._data]
        return VFSResult(success=True, operation=VFSOperation.LIST, path=path, data=nodes)

    def search(self, query, path="/", max_results=10):
        q_words = set(query.lower().split())
        matches = [
            VFSNode(path=self._vfs_path(k), kind=NodeKind.FILE, name=k, content=v,
                    provenance=Provenance(source="stub", origin_path=k))
            for k, v in self._data.items()
            if any(w in v.lower() or w in k.lower() for w in q_words)
        ]
        return VFSResult(success=True, operation=VFSOperation.SEARCH, path=path, data=matches[:max_results])


@pytest.fixture
def vfs():
    fs = SystemFS()
    resolver = StubResolver({
        "auth.md": "Authentication uses API keys for all requests",
        "charges.md": "Charges represent payment transactions. POST /v1/charges to create.",
        "webhooks.md": "Webhooks deliver event notifications to your server",
    })
    fs.mount("/docs/", resolver)
    return fs


def test_build_context_returns_manifest(vfs):
    constructor = ContextConstructor(vfs, max_tokens=2000)
    manifest = constructor.build_context("charge payment")
    assert len(manifest.selected_paths) >= 1
    assert manifest.total_tokens_estimate > 0


def test_build_context_relevance(vfs):
    constructor = ContextConstructor(vfs, max_tokens=2000)
    manifest = constructor.build_context("authentication API keys")
    # auth.md should rank highly
    assert any("auth" in p for p in manifest.selected_paths)


def test_estimate_tokens():
    assert ContextConstructor.estimate_tokens("hello") == 1
    assert ContextConstructor.estimate_tokens("a" * 400) == 100


def test_materialize_produces_string(vfs):
    constructor = ContextConstructor(vfs, max_tokens=2000)
    manifest = constructor.build_context("charge")
    text = constructor.materialize(manifest)
    assert isinstance(text, str)
    assert len(text) > 0


def test_token_budget_respected(vfs):
    constructor = ContextConstructor(vfs, max_tokens=50)
    manifest = constructor.build_context("authentication")
    assert manifest.total_tokens_estimate <= 50 or len(manifest.selected_paths) == 1


def test_hints_included_in_context(vfs):
    constructor = ContextConstructor(vfs, max_tokens=2000)
    manifest = constructor.build_context("general query", hints=["/docs/webhooks.md"])
    assert "/docs/webhooks.md" in manifest.selected_paths
