"""Host API bound to an owner-only Unix socket shared with the normal Docker API."""

from __future__ import annotations

import socket
import sys
from pathlib import Path

import uvicorn


def serve(path: Path):
    if path.exists():
        if not path.is_socket():
            raise RuntimeError("Refusing to replace a non-socket research path")
        with socket.socket(socket.AF_UNIX) as check:
            if check.connect_ex(str(path)) == 0:
                raise RuntimeError("Research socket already has a live owner")
        path.unlink()
    with socket.socket(socket.AF_UNIX) as listener:
        listener.bind(str(path))
        path.chmod(0o600)
        inode = path.stat().st_ino
        listener.listen(128)
        try:
            uvicorn.run("research_room.server:app", fd=listener.fileno())
        finally:
            if path.exists() and path.is_socket() and path.stat().st_ino == inode:
                path.unlink()


if __name__ == "__main__":
    serve(Path(sys.argv[1]))
