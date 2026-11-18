"""Khởi tạo và chạy ứng dụng Meko Boutique."""
import os
from pathlib import Path

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from controllers import register_controllers
from models import initialize


def create_app(config=None):
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.update(
        DATA_DIR=Path(os.getenv("MEKO_DATA", "/var/lib/meko-boutique")),
        TEAM_ID=os.getenv("TEAM_ID", "team1"),
        STAFF_PASSWORD=os.getenv("MEKO_STAFF_PASSWORD", ""),
        MAX_CONTENT_LENGTH=256 * 1024,
    )
    app.config.update(config or {})
    # Apache is the only trusted reverse proxy in front of Waitress.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=0, x_host=0, x_port=0)
    initialize(app)
    register_controllers(app)
    return app


if __name__ == "__main__":
    from waitress import serve
    serve(
        create_app(),
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8080")),
        threads=8,
        connection_limit=24,
        channel_timeout=15,
        max_request_body_size=256 * 1024,
    )
