"""Request handlers for the ECDSA signing service."""
import hashlib
import hmac

from protocol import N, pack_point, sign, verify

OPERATIONS = ['targets', 'pubkey', 'sign', 'unlock']


def vulnerable_nonce(service, message):
    stem = message[:-3] if len(message) > 3 else message
    key = int(service.nonce).to_bytes(32, 'big')
    digest = hmac.new(key, b'ecdsa-context-v2\0' + stem.encode(), hashlib.sha256).digest()
    return int.from_bytes(digest, 'big') % (N - 1) + 1


def dispatch(service, op, req):
    if op == 'pubkey':
        return {'ok': True, 'Q': pack_point(service.public), 'n': format(N, 'x')}
    if op == 'sign':
        message = req['message']
        if not isinstance(message, str) or len(message) > 256 or message.startswith('unlock:'):
            return {'ok': False, 'error': 'forbidden_message'}
        nonce = None if service.patched else vulnerable_nonce(service, message)
        return {'ok': True, 'message': message,
                'signature': sign(message, service.private, nonce=nonce)}
    if op == 'unlock':
        if verify('unlock:' + req['record'], req['signature'], service.public):
            return {'ok': True, 'flag': service.flag(req['record'])}
        return {'ok': False, 'error': 'bad_signature'}
    return None
