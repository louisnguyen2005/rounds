"""Controller account của cửa hàng."""
import hmac
import json
import re
import sqlite3
import time

from flask import abort, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from models import Shop
from security import auth_failed, auth_succeeded, is_auth_limited
from settings import PUBLIC_RANKS, VIP_RANK
from .common import b64, current_user, page, user_required


def register(app):
    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "GET":
            return page("Tạo tài khoản", form="register")
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not re.fullmatch(r"[a-zA-Z0-9_-]{3,32}", username) or len(password) < 10:
            return page("Tạo tài khoản", form="register",
                        error="Tên tài khoản từ 3–32 ký tự (chữ, số, _ hoặc -); mật khẩu tối thiểu 10 ký tự."), 400
        try:
            with Shop() as db:
                db.create_customer((username, generate_password_hash(password),
                            request.form.get("name", username)[:80],
                            request.form.get("email", "")[:120], "Chưa cập nhật"))
        except sqlite3.IntegrityError:
            return page("Tạo tài khoản", form="register", error="Tên tài khoản đã được sử dụng."), 409
        return redirect(url_for("login"))


    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "GET":
            return page("Đăng nhập", form="login")
        client = request.remote_addr or "unknown"
        if is_auth_limited(client):
            return page("Đăng nhập", form="login", error="Thử lại sau ít phút."), 429, {"Retry-After": "900"}
        with Shop() as db:
            user = db.find_customer_by_username((request.form.get("username", ""),)).fetchone()
        if not user or not check_password_hash(user["password"], request.form.get("password", "")):
            auth_failed(client)
            return page("Đăng nhập", form="login", error="Thông tin đăng nhập chưa đúng."), 401
        auth_succeeded(client)
        session.clear()
        session["uid"] = user["id"]
        session["name"] = user["name"]
        # Cấp thẻ hội viên dạng JWT HS256. Hạng lấy từ hồ sơ khách; c-nocturne chỉ do nhân viên cấp.
        rank = user["rank"] if user["rank"] in PUBLIC_RANKS or user["rank"] == VIP_RANK else "basic"
        head = b64(b'{"alg":"HS256","typ":"JWT"}')
        body = b64(json.dumps({"sub": str(user["id"]), "rank": rank, "exp": int(time.time()) + 3600}).encode())
        signing = head + "." + body
        token = signing + "." + b64(hmac.digest(app.extensions["boutique"]["state"]["jwt_secret"].encode(), signing.encode(), "sha256"))
        # Keep post-login navigation on this host; an attacker-controlled
        # absolute URL must not turn the login endpoint into an open redirect.
        destination = request.args.get("next", "")
        if not destination.startswith("/") or destination.startswith("//") or "\\" in destination:
            destination = url_for("home")
        response = redirect(destination)
        response.set_cookie("meko_member", token, httponly=True, samesite="Lax")
        return response


    @app.post("/logout")
    def logout():
        session.clear()
        response = redirect(url_for("home"))
        response.delete_cookie("meko_member")
        return response


    @app.get("/account")
    @user_required
    def account():
        with Shop() as db:
            user = current_user(db)
        return page("Tài khoản", form="account", profile=user)


    @app.post("/account/update")
    @user_required
    def update_account():
        with Shop() as db:
            db.update_customer((request.form.get("name", "")[:80], request.form.get("email", "")[:120],
                        request.form.get("address", "")[:160], session["uid"]))
        session["name"] = request.form.get("name", "")[:80]
        return redirect(url_for("account"))


    @app.get("/account/collection")
    @user_required
    def personal_collection():
        with Shop() as db:
            items = db.list_saved_products((session["uid"],)).fetchall()
        return page("Bộ sưu tập cá nhân", personal_items=items)


    @app.post("/account/collection/add/<int:product_id>")
    @user_required
    def save_product(product_id):
        with Shop() as db:
            if not db.product_exists((product_id,)).fetchone():
                abort(404)
            db.save_product((session["uid"], product_id))
        return redirect(url_for("personal_collection"))

