import os
import time
from collections import defaultdict
from typing import Optional

from fastapi import Request
from itsdangerous import TimestampSigner, SignatureExpired, BadSignature


class NotAuthenticated(Exception):
    """Raised when an admin route is accessed without a valid session."""

SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "shopnest2024")

SESSION_COOKIE = "shopnest_admin"
SESSION_MAX_AGE = 8 * 3600  # 8 hours

_signer = TimestampSigner(SECRET_KEY)

# In-memory rate limiter: {ip: [timestamp, ...]}
_login_attempts: dict = defaultdict(list)
MAX_ATTEMPTS = 5
WINDOW = 60  # seconds


def create_session(username: str) -> str:
    return _signer.sign(username).decode()


def verify_session(token: str) -> Optional[str]:
    try:
        username = _signer.unsign(token, max_age=SESSION_MAX_AGE).decode()
        return username
    except (SignatureExpired, BadSignature):
        return None


def check_rate_limit(ip: str) -> bool:
    """Returns True if the IP is allowed (under rate limit)."""
    now = time.time()
    attempts = _login_attempts[ip]
    # Remove attempts outside window
    _login_attempts[ip] = [t for t in attempts if now - t < WINDOW]
    return len(_login_attempts[ip]) < MAX_ATTEMPTS


def record_login_attempt(ip: str):
    _login_attempts[ip].append(time.time())


def get_admin_user(request: Request) -> Optional[str]:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    return verify_session(token)


def require_admin(request: Request) -> str:
    user = get_admin_user(request)
    if not user:
        raise NotAuthenticated()
    return user


def authenticate(username: str, password: str) -> bool:
    return username == ADMIN_USER and password == ADMIN_PASS
