"""VFS Resolvers."""
from .docs import DocsResolver
from .graph import GraphResolver
from .memory import MemoryResolver
from .module import ModuleResolver

__all__ = ["DocsResolver", "GraphResolver", "MemoryResolver", "ModuleResolver"]
