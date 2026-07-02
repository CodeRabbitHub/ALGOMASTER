from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request

limiter = Limiter(key_func=get_remote_address)


def key_func_user_or_ip(request: Request) -> str:
    """
    Rate-limit key that prefers the caller's bearer token (i.e. their user
    identity) over their IP address. Several AlgoMaster users can share one
    IP (same LAN, same self-hosted box), which would otherwise let them
    share — and blow through — a single IP-keyed quota. Falls back to the
    remote address for unauthenticated requests.
    """
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return f"user:{auth[7:]}"
    return get_remote_address(request)
