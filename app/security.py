"""Small in-process throttles for authentication endpoints."""
from collections import OrderedDict
import threading
import time

WINDOW_SECONDS = 300
BLOCK_SECONDS = 900
MAX_FAILURES = 10
MAX_TRACKED_CLIENTS = 10000
_lock = threading.Lock()
_clients = OrderedDict()


def _entry(client, now):
    state = _clients.get(client)
    if (state is None or
            (state["blocked_until"] and now >= state["blocked_until"]) or
            (not state["blocked_until"] and now - state["started"] >= WINDOW_SECONDS)):
        state = {"started": now, "failures": 0, "blocked_until": 0.0}
        _clients[client] = state
    _clients.move_to_end(client)
    while len(_clients) > MAX_TRACKED_CLIENTS:
        _clients.popitem(last=False)
    return state


def is_auth_limited(client):
    now = time.monotonic()
    with _lock:
        return _entry(client, now)["blocked_until"] > now


def auth_failed(client):
    now = time.monotonic()
    with _lock:
        state = _entry(client, now)
        state["failures"] += 1
        if state["failures"] >= MAX_FAILURES:
            state["blocked_until"] = now + BLOCK_SECONDS


def auth_succeeded(client):
    with _lock:
        _clients.pop(client, None)
