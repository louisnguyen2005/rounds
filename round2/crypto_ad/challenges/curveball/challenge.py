"""Request handlers for the Curveball service."""
from protocol import G, N, certificate_message, pack_point, sign, unpack_point, verify

OPERATIONS = ['targets', 'ca', 'sample', 'read']


def dispatch(service, op, req):
    if op == 'ca':
        return {'ok': True, 'curve': 'P-256', 'G': pack_point(G),
                'Q': pack_point(service.public), 'n': format(N, 'x')}
    if op == 'sample':
        message = certificate_message(req['record'], 'guest')
        return {'ok': True, 'G': pack_point(G), 'role': 'guest',
                'signature': sign(message, service.private)}
    if op == 'read':
        generator = unpack_point(req['G'])
        if service.patched and generator != G:
            return {'ok': False, 'error': 'untrusted_generator'}
        role, record = req['role'], req['record']
        if not verify(certificate_message(record, role), req['signature'],
                      service.public, generator):
            return {'ok': False, 'error': 'bad_certificate'}
        if role != 'admin':
            return {'ok': False, 'error': 'forbidden'}
        return {'ok': True, 'flag': service.flag(record)}
    return None
