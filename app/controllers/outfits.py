"""Controller outfits của cửa hàng."""
import json
import re
from pathlib import Path

from flask import abort, request, session

from models import Shop
from models.outfits import OutfitStorage, StorageLimitReached
from .common import page, patched, user_required


def register(app):
    @app.route("/outfits/new", methods=["GET", "POST"])
    @user_required
    def outfit_new():
        if request.method == "GET":
            return page("Tạo bộ phối đồ", form="outfit")
        # Nhận manifest JSON mô tả bộ phối và tệp xem trước.
        upload = request.files.get("manifest")
        if not upload or not upload.filename or Path(upload.filename).suffix.lower() != ".json":
            abort(400)
        raw = upload.read(65537)
        if len(raw) > 65536:
            abort(413)
        try:
            manifest = json.loads(raw)
        except (ValueError, UnicodeError):
            abort(400)
        if not isinstance(manifest, dict) or not isinstance(manifest.get("preview_file"), str):
            abort(400)
        note = manifest.pop("stylist_note", None)
        if note is not None and (not isinstance(note, str) or not 1 <= len(note) <= 500):
            abort(400)
        storage = OutfitStorage()
        base = storage.designs.resolve()
        sandbox_root = storage.root.resolve()
        target = (base / manifest.get("preview_file", "")).resolve()
        if patched("outfits") and not target.is_relative_to(base):
            abort(400)
        # Tệp xem trước phải nằm trong vùng dữ liệu simulation.
        if not target.is_relative_to(sandbox_root) or not target.is_file():
            abort(400)
        name = str(manifest.get("name", "Bộ phối mới"))[:80]
        # Ghi chú stylist là dữ liệu riêng: không lưu vào designs hay bản manifest công khai.
        public_manifest = json.dumps(manifest, ensure_ascii=False)
        token = None
        try:
            storage.save_manifest(public_manifest)
            if note is not None:
                token = storage.save_note(session["uid"], name, note)
        except StorageLimitReached:
            abort(507)
        with Shop() as db:
            db.create_outfit((session["uid"], name, public_manifest))
        return page("Bản phối đã lưu", preview_text=target.read_text(encoding="utf-8"), outfit_token=token)


    @app.get("/outfits/<token>")
    @user_required
    def outfit_detail(token):
        path = OutfitStorage().note_path(token)
        if not re.fullmatch(r"[0-9a-f]{32}", token) or not path.is_file():
            abort(404)
        outfit = json.loads(path.read_text(encoding="utf-8"))
        if outfit["user_id"] != session["uid"]:
            abort(403)
        return page(outfit["name"], outfit=outfit)

