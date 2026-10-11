"""Rate limiter (slowapi) compatible avec un déploiement derrière le gateway.

Derrière un reverse-proxy, `request.client.host` est l'IP du gateway ; on
privilégie donc le header `X-Forwarded-For` transmis par celui-ci.
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from starlette.requests import Request


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=client_ip)
rate_limit_exceeded_handler = _rate_limit_exceeded_handler
