"""Shared transport, flag storage, and service bootstrap for Round 2 crypto challenges.

Challenge-specific code lives in challenges/<service>/challenge.py. This is an
educational lab model, not vulnerable Windows CryptoAPI or OpenSSL.
"""
import argparse
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import socketserver
import sqlite3
import sys
import threading
from protocol import G, N, MAX_LINE, SERVICES
from challenges.curveball import challenge as curveball
from challenges.padding_oracle import challenge as padding_oracle
from challenges.ecdsa_nonce import challenge as ecdsa_nonce

CHALLENGES = {
    'curveball': curveball,
    'padding_oracle': padding_oracle,
    'ecdsa_nonce': ecdsa_nonce,
}

SQLITE_MAX_PAGES = 8192  # 32 MiB per challenge database.
MAX_FLAGS = 8192
MAX_REQUESTS_PER_CONNECTION = 100
MAX_CONNECTIONS_PER_SOURCE = 8


class Service:
    def __init__(self, name, config):
        if name not in SERVICES:
            raise ValueError('unknown service')
        self.name = name
        self.config = config
        self.patched = str(os.environ.get('PATCHED', config.get('patched', '0'))) == '1'
        self.path = Path(config['data_dir']) / (name + '.sqlite')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS secrets (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS flags (id TEXT PRIMARY KEY, value TEXT NOT NULL, tick INTEGER NOT NULL);''')
            for key in ('private', 'nonce', 'aes', 'mac'):
                db.execute('INSERT OR IGNORE INTO secrets VALUES (?, ?)', (key, secrets.token_hex(32)))
            self.keys = dict(db.execute('SELECT key,value FROM secrets'))
        self.private = int(self.keys['private'], 16) % (N - 1) + 1
        self.nonce = int(self.keys['nonce'], 16) % (N - 1) + 1
        self.public = G * self.private

    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.execute('PRAGMA journal_mode=WAL')
        db.execute(f'PRAGMA max_page_count={SQLITE_MAX_PAGES}')
        db.execute('PRAGMA busy_timeout=15000')
        return db

    def flag(self, record):
        if not isinstance(record, str) or len(record) > 100:
            raise ValueError('record')
        with self.connect() as db:
            row = db.execute('SELECT value FROM flags WHERE id=?', (record,)).fetchone()
        if not row:
            raise ValueError('record')
        return row[0]

    def dispatch(self, req):
        op = req.get('op')
        if op == 'info':
            return {'ok': True, 'service': self.name, 'protocol': 'line-json-v1',
                    'patched': self.patched,
                    'operations': CHALLENGES[self.name].OPERATIONS}
        if op in ('put', 'get', 'prune'):
            token = req.get('token', '')
            if not isinstance(token, str) or not hmac.compare_digest(token, self.config['admin_token']):
                return {'ok': False, 'error': 'unauthorized'}
            if op == 'get':
                return {'ok': True, 'flag': self.flag(req['record'])}
            if op == 'prune':
                before_tick = int(req['before_tick'])
                if not 0 <= before_tick <= 1000000:
                    raise ValueError('before_tick')
                with self.connect() as db:
                    db.execute('DELETE FROM flags WHERE tick < ?', (before_tick,))
                return {'ok': True}
            record, flag, tick = req['record'], req['flag'], int(req['tick'])
            if not isinstance(record, str) or not re.fullmatch(r'[a-f0-9]{24}', record):
                raise ValueError('record')
            if not isinstance(flag, str) or not re.fullmatch(r'MekoDataCTF\{[a-f0-9]{32}\}', flag):
                raise ValueError('flag')
            if not 0 <= tick <= 1000000:
                raise ValueError('tick')
            with self.connect() as db:
                existing = db.execute('SELECT value,tick FROM flags WHERE id=?', (record,)).fetchone()
                if existing and existing != (flag, tick):
                    return {'ok': False, 'error': 'record_conflict'}
                if not existing and db.execute('SELECT count(*) FROM flags').fetchone()[0] >= MAX_FLAGS:
                    return {'ok': False, 'error': 'storage_limit'}
                db.execute('INSERT OR IGNORE INTO flags VALUES (?,?,?)', (record, flag, tick))
            return {'ok': True, 'record': record}
        if op == 'targets':
            with self.connect() as db:
                rows = db.execute('SELECT id,tick FROM flags ORDER BY tick DESC,id LIMIT 30').fetchall()
            return {'ok': True, 'targets': [{'record': r, 'tick': t} for r, t in rows]}
        result = CHALLENGES[self.name].dispatch(self, op, req)
        return result if result is not None else {'ok': False, 'error': 'unknown_operation'}

    def handle(self, req):
        if not isinstance(req, dict):
            return {'ok': False, 'error': 'invalid_request'}
        try:
            return self.dispatch(req)
        except (ValueError, KeyError, TypeError, AssertionError, OverflowError,
                RecursionError, sqlite3.Error):
            return {'ok': False, 'error': 'invalid_request'}


def serve_stream(service, source, output):
    requests = 0
    while True:
        line = source.readline(MAX_LINE + 1)
        if not line:
            return
        if len(line) > MAX_LINE or not line.endswith(b'\n'):
            output.write(b'{"ok":false,"error":"line_too_long"}\n')
            output.flush()
            return
        try:
            result = service.handle(json.loads(line))
        except (ValueError, UnicodeError, RecursionError):
            result = {'ok': False, 'error': 'invalid_json'}
        output.write(json.dumps(result, separators=(',', ':')).encode() + b'\n')
        output.flush()
        requests += 1
        if requests >= MAX_REQUESTS_PER_CONNECTION:
            return


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--service', required=True, choices=SERVICES)
    parser.add_argument('--config', required=True)
    parser.add_argument('--stdio', action='store_true', help='ncat --exec transport')
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--port', type=int)
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text())
    app = Service(args.service, config)
    if args.stdio:
        serve_stream(app, sys.stdin.buffer, sys.stdout.buffer)
        return
    slots = threading.BoundedSemaphore(24)
    source_lock = threading.Lock()
    source_connections = {}

    def release_source(source):
        with source_lock:
            active = source_connections.get(source, 0) - 1
            if active > 0:
                source_connections[source] = active
            else:
                source_connections.pop(source, None)

    class Handler(socketserver.StreamRequestHandler):
        def handle(self):
            self.request.settimeout(25)
            try:
                serve_stream(app, self.rfile, self.wfile)
            except (OSError, ValueError):
                pass

    class Server(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

        def process_request(self, request, address):
            source = address[0]
            with source_lock:
                if source_connections.get(source, 0) >= MAX_CONNECTIONS_PER_SOURCE:
                    request.close()
                    return
                source_connections[source] = source_connections.get(source, 0) + 1
            if not slots.acquire(blocking=False):
                release_source(source)
                request.close()
                return
            try:
                super().process_request(request, address)
            except Exception:
                slots.release()
                release_source(source)
                raise

        def process_request_thread(self, request, address):
            try:
                super().process_request_thread(request, address)
            finally:
                slots.release()
                release_source(address[0])

    with Server((args.host, args.port or SERVICES[args.service]), Handler) as server:
        print(f'{args.service} line-JSON listening on {args.host}:{server.server_address[1]}', flush=True)
        server.serve_forever()


if __name__ == '__main__':
    main()
