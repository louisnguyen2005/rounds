"""Controller membership của cửa hàng."""

from flask import abort

from models import Shop
from .common import is_vip, page, user_required, vip_denied


def register(app):
    @app.get("/member/benefits")
    @user_required
    def benefits():
        if not is_vip():
            return vip_denied()
        with Shop() as db:
            offers = db.list_offers().fetchall()
        return page("Đặc quyền C-Nocturne", vip_offers=offers)


    @app.get("/member/offers/<int:offer_id>")
    @user_required
    def member_offer(offer_id):
        if not is_vip():
            return vip_denied()
        with Shop() as db:
            offer = db.find_offer((offer_id,)).fetchone()
        if not offer:
            abort(404)
        return page("Đặc quyền C-Nocturne", vip_offer=offer)

