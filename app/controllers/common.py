"""Xử lý dùng chung cho các controller."""
import base64
import functools
import hmac
import json
import time

from flask import current_app as app, redirect, request, session, url_for

from models import Shop
from settings import VIP_RANK
from views import render_page


def b64(data):
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def patched(task):
    return app.config["PATCHED"].get(task, False)


def current_user(db):
    if not session.get("uid"):
        return None
    return db.find_customer((session["uid"],)).fetchone()


def user_required(fn):
    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("uid"):
            return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)
    return wrapped


def staff_required(fn):
    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        if session.get("staff") is not True:
            return redirect(url_for("staff_login"))
        return fn(*args, **kwargs)
    return wrapped


def page(title, **kwargs):
    with Shop() as db:
        products = db.list_products().fetchall()
    return render_page(title, products, **kwargs)


def _cart_items(cart):
    with Shop() as db:
        result = []
        for pid, qty in cart.items():
            p = db.find_product((int(pid),)).fetchone()
            if p:
                result.append(dict(p) | {"quantity": qty})
        return result


def is_vip():
    # Đọc hạng hội viên từ cookie meko_member.
    token = request.cookies.get("meko_member", "")
    member = {}
    try:
        head, body, sig = token.split(".")
        header = json.loads(base64.urlsafe_b64decode(head + "=" * (-len(head) % 4)))
        claims = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        signing = head + "." + body
        expected = b64(hmac.digest(app.extensions["boutique"]["state"]["jwt_secret"].encode(), signing.encode(), "sha256"))
        valid = ((header.get("alg") == "none" and sig == "" and not patched("membership"))
                 or (header.get("alg") == "HS256" and hmac.compare_digest(expected, sig)))
        if valid and claims.get("exp", 0) > time.time() and claims.get("sub") == str(session["uid"]):
            member = claims
    except (ValueError, TypeError, UnicodeError, AttributeError):
        pass
    return member.get("rank") in (VIP_RANK, VIP_RANK + "-plus")


def vip_denied():
    return page("Đặc quyền hội viên", vip_locked=True,
                error="Khu vực ưu đãi riêng dành cho hạng C-Nocturne."), 403

