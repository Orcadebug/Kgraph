"""Tests for Sandbox path utilities."""
import pytest
from systemfs.sandbox import Sandbox


def test_normalize_simple():
    assert Sandbox.normalize("/docs/charges/create.md") == "/docs/charges/create.md"

def test_normalize_strips_leading_slash():
    assert Sandbox.normalize("docs/charges") == "/docs/charges"

def test_normalize_resolves_dotdot():
    assert Sandbox.normalize("/docs/../graph/nodes") == "/graph/nodes"

def test_normalize_root():
    assert Sandbox.normalize("/") == "/"

def test_normalize_prevents_traversal():
    # Can't go above root
    assert Sandbox.normalize("/docs/../../etc/passwd") == "/etc/passwd"
    # But root stays root
    assert Sandbox.normalize("/../..") == "/"

def test_validate_within_true():
    assert Sandbox.validate_within("/docs/charges/create.md", "/docs/") is True

def test_validate_within_false():
    assert Sandbox.validate_within("/graph/nodes/Charge", "/docs/") is False

def test_validate_within_exact_mount():
    assert Sandbox.validate_within("/docs/", "/docs/") is True

def test_relative_to_mount():
    assert Sandbox.relative_to_mount("/docs/charges/create.md", "/docs/") == "/charges/create.md"

def test_relative_to_mount_root():
    assert Sandbox.relative_to_mount("/docs/", "/docs/") == "/"

def test_relative_to_mount_nested():
    assert Sandbox.relative_to_mount("/context/memory/fact/key.json", "/context/memory/") == "/fact/key.json"
