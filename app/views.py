"""Dựng giao diện từ dữ liệu controller cung cấp."""
from flask import render_template, session

from settings import PUBLIC_RANKS, VIP_RANK


def render_page(title, products, **kwargs):
    return render_template("shop.html", title=title, products=products,
                           customer=session.get("name"),
                           ranks=PUBLIC_RANKS | {VIP_RANK: "C-Nocturne"}, year=2026, **kwargs)
