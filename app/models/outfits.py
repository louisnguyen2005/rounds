"""Lưu manifest và ghi chú riêng của bộ phối đồ."""
import json
import secrets
import threading
from pathlib import Path

from flask import current_app

MAX_STORAGE_BYTES = 64 * 1024 * 1024
MAX_STORAGE_FILES = 4096
_storage_lock = threading.Lock()


class StorageLimitReached(Exception):
    """The bounded preview store has reached its per-service disk budget."""


def _write_bounded(path, content):
    encoded = content.encode("utf-8")
    with _storage_lock:
        files = [p for folder in (path.parent.parent / "designs", path.parent.parent / "private")
                 for p in folder.iterdir() if p.is_file()]
        used = sum(p.stat().st_size for p in files)
        if len(files) >= MAX_STORAGE_FILES or used + len(encoded) > MAX_STORAGE_BYTES:
            raise StorageLimitReached
        with path.open("x", encoding="utf-8") as stream:
            stream.write(content)


class OutfitStorage:
    def __init__(self):
        self.root = Path(current_app.config["DATA_DIR"]) / "simulation"
        self.designs = self.root / "designs"
        self.private = self.root / "private"

    def save_manifest(self, content):
        _write_bounded(self.designs / (secrets.token_hex(12) + ".json"), content)

    def save_note(self, user_id, name, note):
        token = secrets.token_hex(16)
        _write_bounded(self.private / (token + ".json"),
                       json.dumps({"user_id": user_id, "name": name, "stylist_note": note},
                                  ensure_ascii=False))
        return token

    def note_path(self, token):
        return self.private / (token + ".json")
