"""Fail closed before destructive fixtures; no graph connection at import time."""

from __future__ import annotations

import ipaddress
import os
import socket
from urllib.parse import urlsplit


class UnsafeGraphTarget(RuntimeError):
    pass


def validate_target(
    uri: str, database: str, expected: str, expected_database: str, acknowledgement: str
) -> None:
    parsed = urlsplit(uri)
    if (
        acknowledgement != "kepler-disposable-only"
        or uri != expected
        or parsed.scheme != "bolt"
        or parsed.hostname != "memgraph-test"
        or parsed.port != 7687
        or parsed.username
        or parsed.password
        or parsed.path
        or parsed.query
        or parsed.fragment
        or not expected_database
        or database != expected_database
    ):
        raise UnsafeGraphTarget("Destructive graph tests require the explicit disposable target")


def validate_address(address: tuple[str, int], expected_ips: set[str]) -> None:
    host, port = address
    if (
        port != 7687
        or host not in expected_ips
        or not expected_ips
        or any(ipaddress.ip_address(ip).is_loopback for ip in expected_ips)
    ):
        raise UnsafeGraphTarget("Connected graph endpoint differs from disposable test service")


def guard(repo) -> set[str]:
    validate_target(
        repo.uri,
        repo.database,
        os.getenv("MEMGRAPH_TEST_TARGET", ""),
        os.getenv("MEMGRAPH_TEST_DATABASE", ""),
        os.getenv("MEMGRAPH_TEST_ACK", ""),
    )
    ips = {x[4][0] for x in socket.getaddrinfo("memgraph-test", 7687, type=socket.SOCK_STREAM)}
    expected = os.getenv("MEMGRAPH_TEST_EXPECTED_ADDRESS", "")
    try:
        expected_ip, expected_port = expected.rsplit(":", 1)
        address = ipaddress.ip_address(expected_ip)
        if expected_port != "7687" or expected_ip not in ips or not address.is_private:
            raise ValueError("unexpected disposable endpoint")
    except ValueError as exc:
        raise UnsafeGraphTarget(
            "Test launcher must inject the independently inspected disposable service address"
        ) from exc
    # Check the actual driver endpoint, not just the configured string.
    info = repo._client().get_server_info()
    validate_address(tuple(info.address), {expected_ip})
    return {expected_ip}


def wipe_disposable_graph(repo) -> None:
    ips = guard(repo)
    with repo._driver.session(database=repo.database) as session:
        summary = session.run("RETURN 1").consume()
        validate_address(tuple(summary.server.address), ips)
        session.run("MATCH (n) DETACH DELETE n").consume()
