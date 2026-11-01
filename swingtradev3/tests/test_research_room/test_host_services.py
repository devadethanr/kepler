from __future__ import annotations

import json
import socket
from pathlib import Path

import pytest

from ops.research_services import private_write, write_environment
from research_room.host_api import serve


def test_service_environment_preserves_literal_values_and_private_permissions(tmp_path):
    path = tmp_path / "worker.env"
    values = {
        "DATABASE_URL": "postgresql://dummy:p$a\\ss@127.0.0.1/test",
        "KEY": 'dummy"quoted-value',
        "PATH": "/usr/bin:/bin",
    }
    write_environment(path, values)
    actual = {
        key: json.loads(value)
        for line in path.read_text().splitlines()
        for key, value in [line.split("=", 1)]
    }
    assert actual == values
    assert path.stat().st_mode & 0o777 == 0o600
    path.chmod(0o644)
    private_write(path, "replacement\n")
    assert path.read_text() == "replacement\n" and path.stat().st_mode & 0o777 == 0o600


def test_host_api_refuses_to_replace_a_regular_file(tmp_path):
    path = tmp_path / "api.sock"
    path.write_text("operator file")
    with pytest.raises(RuntimeError, match="non-socket"):
        serve(path)
    assert path.read_text() == "operator file"


def test_host_api_refuses_an_existing_live_socket():
    import tempfile

    with tempfile.TemporaryDirectory(prefix="krr-owner-") as directory:
        path = Path(directory) / "api.sock"
        with socket.socket(socket.AF_UNIX) as listener:
            listener.bind(str(path))
            listener.listen(1)
            inode = path.stat().st_ino
            with pytest.raises(RuntimeError, match="live owner"):
                serve(path)
            assert path.stat().st_ino == inode
