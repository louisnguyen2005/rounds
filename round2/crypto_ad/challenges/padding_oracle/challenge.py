"""Request handlers for encrypted document records."""
import hashlib
import hmac
import secrets

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad
except ModuleNotFoundError:  # Debian's python3-pycryptodome uses this namespace.
    from Cryptodome.Cipher import AES
    from Cryptodome.Util.Padding import pad, unpad

OPERATIONS = ['targets', 'ciphertext', 'encrypt', 'decrypt']


def seal(service, plain, record):
    iv = secrets.token_bytes(16)
    raw = iv + AES.new(bytes.fromhex(service.keys['aes']), AES.MODE_CBC, iv).encrypt(pad(plain, 16))
    tag = hmac.new(bytes.fromhex(service.keys['mac']),
                   record.encode() + b'\0' + raw, hashlib.sha256).hexdigest()
    return {'ciphertext': raw.hex(), 'tag': tag if service.patched else ''}


def _fault_code(service, record, stage):
    key = bytes.fromhex(service.keys['mac'])
    material = b'padding-oracle-v2\0' + record.encode() + b'\0' + stage.encode()
    return 'fault_' + hmac.new(key, material, hashlib.sha256).hexdigest()[:10]


def dispatch(service, op, req):
    record = req.get('record', 'public')
    if not isinstance(record, str) or len(record) > 100:
        raise ValueError('record')
    if op == 'ciphertext':
        return {'ok': True, **seal(service, service.flag(record).encode(), record)}
    if op == 'encrypt':
        text = req['message']
        if not isinstance(text, str) or len(text) > 256:
            raise ValueError('message')
        return {'ok': True, **seal(service, b'public:' + text.encode(), record)}
    if op == 'decrypt':
        try:
            raw = bytes.fromhex(req['ciphertext'])
            if len(raw) < 32 or len(raw) > 1024 or len(raw) % 16:
                raise ValueError('length')
            if service.patched:
                expected = hmac.new(bytes.fromhex(service.keys['mac']),
                                    record.encode() + b'\0' + raw,
                                    hashlib.sha256).hexdigest()
                if not isinstance(req.get('tag'), str) or not hmac.compare_digest(expected, req['tag']):
                    return {'ok': False, 'error': 'invalid_request'}
            plain = unpad(AES.new(bytes.fromhex(service.keys['aes']), AES.MODE_CBC,
                                  raw[:16]).decrypt(raw[16:]), 16)
        except (ValueError, KeyError, TypeError):
            error = 'invalid_request' if service.patched else _fault_code(service, record, 'pad')
            return {'ok': False, 'error': error}
        if not plain.startswith(b'public:'):
            error = 'invalid_request' if service.patched else _fault_code(service, record, 'content')
            return {'ok': False, 'error': error}
        return {'ok': True, 'message': 'valid document'}
    return None
