"""Controller storefront của cửa hàng."""

from flask import abort, redirect, request, session, url_for

from models import Catalog, Shop
from .common import page, patched, user_required


def register(app):
    @app.after_request
    def harden(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response


    @app.get("/health")
    def health():
        with Shop() as db:
            db.ping().fetchone()
        return {"status": "ok", "service": "meko-boutique", "team": app.config["TEAM_ID"]}


    @app.get("/")
    def home():
        return page("Trang chủ", hero=True)


    @app.get("/category/<category>")
    def category(category):
        return page(category, category=category)


    @app.get("/search")
    def search():
        return page("Tìm kiếm", q=request.args.get("q", ""))


    @app.get("/product/<int:product_id>")
    def product(product_id):
        with Shop() as db:
            item = db.find_product((product_id,)).fetchone()
        if not item:
            abort(404)
        return page(item["name"], item=item)


    @app.get("/collections")
    def collections():
        with Catalog() as db:
            rows = db.list_collections().fetchall()
        return page("Bộ sưu tập", collections=rows)


    @app.get("/collections/search")
    def collection_search():
        # Lọc bộ sưu tập theo tên.
        q = request.args.get("q", "")[:160]
        with Catalog() as catalog:
            rows = catalog.search(q, patched("collections"))
        return page("Tìm bộ sưu tập", collections=rows, q=q, searched=True)


    @app.route("/account/notes", methods=["GET", "POST"])
    @user_required
    def collection_notes():
        with Catalog() as db:
            if request.method == "POST":
                note = request.form.get("note", "").strip()
                collection_id = request.form.get("collection_id", type=int)
                if (not note or len(note) > 500 or not db.collection_exists((collection_id,)).fetchone()):
                    abort(400)
                cur = db.create_note((session["uid"], collection_id, note))
                return redirect(url_for("collection_note", note_id=cur.lastrowid))
            rows = db.list_customer_notes((session["uid"],)).fetchall()
            options = db.list_collection_options().fetchall()
        return page("Ghi chú bộ sưu tập", notes=rows, note_collections=options)


    @app.get("/account/notes/<int:note_id>")
    @user_required
    def collection_note(note_id):
        with Catalog() as db:
            note = db.find_note((note_id,)).fetchone()
        if not note:
            abort(404)
        if note["user_id"] != session["uid"]:
            abort(403)
        return page("Ghi chú bộ sưu tập", note=note)

