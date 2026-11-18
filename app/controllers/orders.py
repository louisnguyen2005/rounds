"""Controller orders của cửa hàng."""
import secrets

from flask import abort, redirect, request, session, url_for

from models import Shop
from .common import page, patched, user_required, _cart_items


def register(app):
    @app.post("/cart/add/<int:product_id>")
    @user_required
    def cart_add(product_id):
        with Shop() as db:
            item = db.find_product_id((product_id,)).fetchone()
        if not item:
            abort(404)
        cart = session.get("cart", {})
        qty = max(1, min(5, int(request.form.get("quantity", 1) or 1)))
        cart[str(product_id)] = min(20, int(cart.get(str(product_id), 0)) + qty)
        session["cart"] = cart
        return redirect(url_for("cart"))


    @app.get("/cart")
    @user_required
    def cart():
        with Shop() as db:
            coupons = db.list_coupons().fetchall()
        return page("Giỏ hàng", cart_items=_cart_items(session.get("cart", {})), coupons=coupons)


    @app.post("/checkout")
    @user_required
    def checkout():
        items = _cart_items(session.get("cart", {}))
        if not items:
            return redirect(url_for("cart"))
        total = sum(x["price"] * x["quantity"] for x in items)
        coupon = request.form.get("coupon", "").upper()
        memo = request.form.get("memo", "").strip()[:160]
        with Shop() as db:
            discount = db.find_discount((coupon,)).fetchone()
            if discount:
                total = total * (100 - discount[0]) // 100
            code = "DH-" + str(secrets.randbelow(900000) + 100000)
            cur = db.create_order((code, session["uid"], total, memo))
            oid = cur.lastrowid
            db.create_order_items([(oid, x["id"], x["quantity"], x["price"]) for x in items])
        session["cart"] = {}
        return redirect(url_for("invoice", order_id=oid))


    @app.get("/account/orders")
    @user_required
    def orders():
        with Shop() as db:
            rows = db.list_customer_orders((session["uid"],)).fetchall()
        return page("Đơn hàng của tôi", orders=rows)


    @app.get("/account/orders/<int:order_id>/invoice")
    @user_required
    def invoice(order_id):
        # Tra cứu hóa đơn và các mặt hàng trong đơn.
        with Shop() as db:
            order = db.find_order((order_id,)).fetchone()
            if not order:
                abort(404)
            if patched("invoices") and order["user_id"] != session["uid"]:
                abort(403)
            lines = db.list_order_items((order_id,)).fetchall()
        return page("Hóa đơn", invoice=order, invoice_items=lines)

