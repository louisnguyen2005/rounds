"""Kết nối và khởi tạo dữ liệu bền vững của cửa hàng."""
import json
import secrets
import sqlite3
from pathlib import Path

from flask import current_app
from werkzeug.security import generate_password_hash

from settings import ROOT, TASKS

SQLITE_MAX_PAGES = 32768  # 128 MiB per database at SQLite's default 4 KiB page size.


def connect(path):
    con = sqlite3.connect(path, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute(f"PRAGMA max_page_count={SQLITE_MAX_PAGES}")
    con.execute("PRAGMA busy_timeout=10000")
    return con


class Repository:
    database = "shop.sqlite3"

    def __enter__(self):
        self.connection = connect(Path(current_app.config["DATA_DIR"]) / self.database)
        self.connection.__enter__()
        return self

    def __exit__(self, *exc):
        try:
            return self.connection.__exit__(*exc)
        finally:
            self.connection.close()


def initialize(app):
    data = Path(app.config["DATA_DIR"])
    data.mkdir(parents=True, exist_ok=True)
    app.config["DATA_DIR"] = data

    state_file = data / "state.json"
    app.config["STATE_FILE"] = state_file
    if not state_file.exists():
        state_file.write_text(json.dumps({
            "team": app.config["TEAM_ID"],
            "secret": secrets.token_hex(32),
            "jwt_secret": secrets.token_hex(32),
        }), encoding="utf-8")
        try:
            state_file.chmod(0o600)
        except OSError:
            pass
    state = json.loads(state_file.read_text(encoding="utf-8"))
    if state["team"] != app.config["TEAM_ID"]:
        raise ValueError("DATA_DIR đã thuộc đội khác; hãy dùng vùng dữ liệu riêng cho mỗi đội")

    app.secret_key = state["secret"]

    patches_path = data / "patches.json"
    patches = json.loads(patches_path.read_text(encoding="utf-8")) if patches_path.exists() else {}
    app.config["PATCHED"] = {t: bool(patches.get(t, False)) for t in TASKS}

    db_path = data / "shop.sqlite3"
    # Catalog bộ sưu tập dùng cơ sở dữ liệu riêng.
    catalog_path = data / "catalog.sqlite3"
    seed = json.loads((ROOT / "data" / "seed.json").read_text(encoding="utf-8"))
    simulation = data / "simulation"
    designs = simulation / "designs"
    private_outfits = simulation / "private"
    designs.mkdir(parents=True, exist_ok=True)
    private_outfits.mkdir(parents=True, exist_ok=True)
    # Bản xem trước hợp lệ nằm trong vùng thiết kế công khai.
    (designs / "lookbook.txt").write_text(
        "Gợi ý phối: áo khoác linen cùng phụ kiện tông đất, giày lười trung tính.\n",
        encoding="utf-8")

    with connect(db_path) as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS customers(id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, name TEXT, email TEXT, address TEXT, rank TEXT DEFAULT 'basic');
            CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY, name TEXT, category TEXT, price INTEGER, image TEXT, description TEXT);
            CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY, code TEXT, user_id INTEGER, total INTEGER, status TEXT, created TEXT, memo TEXT);
            CREATE TABLE IF NOT EXISTS order_items(order_id INTEGER, product_id INTEGER, quantity INTEGER, price INTEGER);
            CREATE TABLE IF NOT EXISTS outfits(id INTEGER PRIMARY KEY, user_id INTEGER, name TEXT, manifest TEXT);
            CREATE TABLE IF NOT EXISTS saved_collection(user_id INTEGER, product_id INTEGER, PRIMARY KEY(user_id, product_id));
            CREATE TABLE IF NOT EXISTS coupons(code TEXT PRIMARY KEY, discount INTEGER, note TEXT);
            CREATE TABLE IF NOT EXISTS vip_offers(id INTEGER PRIMARY KEY, code TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS reconciliation_notes(id INTEGER PRIMARY KEY, ref TEXT UNIQUE NOT NULL, value TEXT NOT NULL);
            """
        )
        if not db.execute("SELECT 1 FROM products LIMIT 1").fetchone():
            db.executemany("INSERT INTO products VALUES(?,?,?,?,?,?)",
                           [(p["id"], p["name"], p["category"], p["price"], p["image"], p["description"]) for p in seed["products"]])
            db.executemany("INSERT INTO coupons VALUES(?,?,?)",
                           [(c["code"], c["discount"], c["note"]) for c in seed["coupons"]])
            # Hồ sơ khách hàng giả lập và một đơn hàng mẫu để thí sinh thử hóa đơn của người khác.
            db.execute("INSERT INTO customers(id,username,password,name,email,address,rank) VALUES(900,?,?,?,?,?,?)",
                       ("khach-than-thiet", generate_password_hash(secrets.token_urlsafe()),
                        "An Nhiên", "annhien@example.test", "Hồ sơ giả lập · Đà Nẵng", "gold"))
            db.execute("INSERT INTO orders VALUES(9001,'DH-2026-09001',900,1290000,'Đang giao','04/11/2026',?)",
                       ("Giao trong giờ hành chính",))
            db.execute("INSERT INTO order_items VALUES(9001,2,1,1290000)")

    with connect(catalog_path) as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS collections(id INTEGER PRIMARY KEY, title TEXT, description TEXT, season TEXT);
            CREATE TABLE IF NOT EXISTS collection_notes(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, collection_id INTEGER NOT NULL, note TEXT NOT NULL);
            """
        )
        if not db.execute("SELECT 1 FROM collections LIMIT 1").fetchone():
            db.executemany("INSERT INTO collections VALUES(?,?,?,?)",
                           [(c["id"], c["title"], c["description"], c["season"]) for c in seed["collections"]])
    app.extensions["boutique"] = {"state": state}
