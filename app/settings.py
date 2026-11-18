"""Cấu hình chức năng và hạng hội viên."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TASKS = ("collections", "invoices", "outfits", "membership", "operations")
PUBLIC_RANKS = {
    "basic": "Thành viên",
    "silver": "Bạc",
    "gold": "Vàng",
}
VIP_RANK = "c-nocturne"
