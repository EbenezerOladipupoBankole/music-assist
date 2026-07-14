"""
Shared rate limiter for the endpoints that spend OpenAI API credits.

Limits are intentionally generous defaults for a low-traffic demo app; tune
via the `@limiter.limit(...)` decorator on each route if usage patterns change.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
