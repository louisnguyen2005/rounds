"""Controller operations của cửa hàng."""
import hmac
import secrets

from flask import abort, redirect, request, session, url_for

from models import Shop
from settings import VIP_RANK
from security import auth_failed, auth_succeeded, is_auth_limited
from .common import page, patched, staff_required


def register(app):
    @app.get("/exports/operations.sql")
    def operations_export():
        # Xuất các bản ghi đối soát vận hành.
        if patched("operations") and session.get("staff") is not True:
            abort(404)
        with Shop() as db:
            rows = db.list_reconciliations().fetchall()
        lines = ["-- Meko Boutique — ban xuat doi soat van hanh (du lieu gia lap)",
                 "-- Sinh tu quy trinh backup noi bo, khong danh cho khach hang."]
        for row in rows:
            ref, value = (row[key].replace("'", "''") for key in ("ref", "value"))
            lines.append("INSERT INTO reconciliation_notes(ref,value) VALUES ('" + ref + "','" + value + "');")
        return "\n".join(lines) + "\n", 200, {"Content-Type": "text/plain; charset=utf-8"}


    @app.get("/robots.txt")
    def robots():
        lines = ["User-agent: *", "Disallow: /staff", "Disallow: /exports/"]
        return "\n".join(lines) + "\n", 200, {"Content-Type": "text/plain; charset=utf-8"}


    @app.route("/staff/login", methods=["GET", "POST"])
    def staff_login():
        if request.method == "GET":
            return page("Đăng nhập nhân viên", form="staff-login")
        client = request.remote_addr or "unknown"
        if is_auth_limited(client):
            return page("Đăng nhập nhân viên", form="staff-login", error="Thử lại sau ít phút."), 429, {"Retry-After": "900"}
        if not app.config["STAFF_PASSWORD"] or not hmac.compare_digest(
                request.form.get("password", ""), app.config["STAFF_PASSWORD"]):
            auth_failed(client)
            return page("Đăng nhập nhân viên", form="staff-login", error="Không thể xác thực nhân viên."), 401
        auth_succeeded(client)
        session["staff"] = True
        return redirect(url_for("staff"))


    @app.get("/staff")
    @staff_required
    def staff():
        with Shop() as db:
            all_orders = db.list_orders().fetchall()
        return page("Vận hành cửa hàng", staff=True, orders=all_orders)


    @app.get("/staff/products")
    @staff_required
    def staff_products():
        with Shop() as db:
            items = db.list_products().fetchall()
        return page("Quản lý sản phẩm", staff=True, staff_products=items)


    @app.post("/staff/products")
    @staff_required
    def staff_add_product():
        name = request.form.get("name", "").strip()[:100]
        price = request.form.get("price", type=int)
        cat = request.form.get("category", "").strip()[:60]
        if not name or not cat or not price or price < 1:
            abort(400)
        with Shop() as db:
            db.create_product((name, cat, price, request.form.get("description", "")[:240]))
        return redirect(url_for("staff_products"))


    @app.post("/staff/orders/<int:order_id>/status")
    @staff_required
    def staff_update_order(order_id):
        status = request.form.get("status", "")
        if status not in ("Đang xử lý", "Đang giao", "Đã giao", "Đã hủy"):
            abort(400)
        with Shop() as db:
            db.update_order_status((status, order_id))
        return redirect(url_for("staff"))


    @app.route("/staff/vip", methods=["GET", "POST"])
    @staff_required
    def staff_vip():
        with Shop() as db:
            if request.method == "POST":
                code = request.form.get("code", "").strip()
                if not 1 <= len(code) <= 160:
                    abort(400)
                cur = db.create_offer((code,))
                return redirect(url_for("staff_vip_offer", offer_id=cur.lastrowid))
            offers = db.list_offers().fetchall()
        return page("Ưu đãi C-Nocturne", staff=True, staff_offers=offers)


    @app.get("/staff/vip/offers/<int:offer_id>")
    @staff_required
    def staff_vip_offer(offer_id):
        with Shop() as db:
            offer = db.find_offer((offer_id,)).fetchone()
        if not offer:
            abort(404)
        return page("Ưu đãi C-Nocturne", staff=True, staff_offers=[], staff_offer=offer)


    @app.post("/staff/vip/members")
    @staff_required
    def staff_vip_member():
        with Shop() as db:
            changed = db.grant_membership((VIP_RANK, request.form.get("username", ""))).rowcount
        if not changed:
            abort(404)
        return redirect(url_for("staff_vip"))


    @app.route("/staff/reconciliation", methods=["GET", "POST"])
    @staff_required
    def staff_reconciliation():
        with Shop() as db:
            if request.method == "POST":
                value = request.form.get("value", "").strip()
                if not 1 <= len(value) <= 160:
                    abort(400)
                ref = "RC-" + secrets.token_hex(6)
                db.create_reconciliation((ref, value))
                return redirect(url_for("staff_reconciliation", ref=ref))
            rows = db.list_reconciliation_refs().fetchall()
        return page("Đối soát vận hành", staff=True, staff_reconciliations=rows)

