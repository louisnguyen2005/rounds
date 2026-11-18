"""Đăng ký controller, giữ nguyên tên endpoint và đường dẫn HTTP."""
from . import account, membership, operations, orders, outfits, storefront


def register_controllers(app):
    for controller in (storefront, account, orders, outfits, membership, operations):
        controller.register(app)
