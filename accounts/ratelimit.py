"""Pembatas percobaan masuk: LOGIN_MAX_ATTEMPTS kegagalan per (email, IP) dalam LOGIN_BLOCK_SECONDS -> diblokir."""
from django.conf import settings
from django.core.cache import cache


def _key(email, ip):
    return f"login-fail:{(email or '').strip().lower()}:{ip}"


def is_blocked(email, ip):
    return cache.get(_key(email, ip), 0) >= settings.LOGIN_MAX_ATTEMPTS


def register_failure(email, ip):
    key = _key(email, ip)
    cache.add(key, 0, settings.LOGIN_BLOCK_SECONDS)
    cache.incr(key)


def reset(email, ip):
    cache.delete(_key(email, ip))
