import multiprocessing
import threading
import time

import pytest

from research_room import browser
from research_room import tools


def slow_fetch(pipe, url, domains, deadline):
    time.sleep(30)


def test_cancel_kills_owned_fetch_process(monkeypatch):
    # Spawn a real child that hangs in the fetch phase, then cancel it.
    monkeypatch.setattr(browser, "_fetch_child", slow_fetch)
    stop = threading.Event()
    timer = threading.Timer(0.25, stop.set)
    before = {p.pid for p in multiprocessing.active_children()}
    timer.start()
    started = time.monotonic()
    try:
        with pytest.raises(TimeoutError, match="cancelled"):
            browser._supervised_fetch("https://example.test", ["example.test"], started + 10, stop)
    finally:
        timer.cancel()
    assert time.monotonic() - started < 3
    assert {p.pid for p in multiprocessing.active_children()} <= before


def test_deadline_kills_owned_fetch_process(monkeypatch):
    monkeypatch.setattr(browser, "_fetch_child", slow_fetch)
    before = {p.pid for p in multiprocessing.active_children()}
    started = time.monotonic()
    with pytest.raises(TimeoutError, match="exceeded"):
        browser._supervised_fetch("https://example.test", ["example.test"], started + 0.25, None)
    assert time.monotonic() - started < 3
    assert {p.pid for p in multiprocessing.active_children()} <= before


def slow_graph(pipe, name, value):
    time.sleep(30)


def test_cancel_kills_owned_blocked_graph_process(monkeypatch):
    monkeypatch.setattr(tools, "_graph_child", slow_graph)
    stop = threading.Event()
    timer = threading.Timer(0.25, stop.set)
    before = {p.pid for p in multiprocessing.active_children()}
    timer.start()
    started = time.monotonic()
    try:
        with pytest.raises(TimeoutError, match="cancelled"):
            tools._supervised_graph("graph_lookup", "ACME", started + 10, stop)
    finally:
        timer.cancel()
    assert time.monotonic() - started < 3
    assert {p.pid for p in multiprocessing.active_children()} <= before
