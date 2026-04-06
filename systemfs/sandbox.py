"""Path validation and sandboxing for SystemFS."""
from pathlib import PurePosixPath


class Sandbox:
    @staticmethod
    def normalize(path: str) -> str:
        """Normalize a VFS path: resolve .., ensure leading /."""
        parts = []
        for part in PurePosixPath("/" + path.strip("/")).parts:
            if part == "..":
                if len(parts) > 1:
                    parts.pop()
            elif part != ".":
                parts.append(part)
        if not parts:
            return "/"
        result = str(PurePosixPath(*parts))
        return result if result.startswith("/") else "/" + result

    @staticmethod
    def validate_within(path: str, mount_point: str) -> bool:
        """Check that path is within mount_point boundaries."""
        norm_path = Sandbox.normalize(path)
        norm_mount = Sandbox.normalize(mount_point).rstrip("/") + "/"
        return norm_path.startswith(norm_mount) or norm_path == norm_mount.rstrip("/")

    @staticmethod
    def relative_to_mount(path: str, mount_point: str) -> str:
        """Strip mount prefix, returning the resolver-local path."""
        norm_path = Sandbox.normalize(path)
        norm_mount = Sandbox.normalize(mount_point).rstrip("/")
        if norm_path == norm_mount:
            return "/"
        rel = norm_path[len(norm_mount):]
        return rel if rel.startswith("/") else "/" + rel
