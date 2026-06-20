"""
Lightweight, per-session rate limiting for Streamlit.

Streamlit reruns the entire script on every interaction, so the only
sensible place to throttle is at the point of action -- a button press or
form submission that's about to hit Supabase -- not the read-only render
pass itself (which already reruns on every interaction regardless).

`throttled(key)` is a plain boolean check meant to sit as the first branch
inside an `if st.button(...):` block; `rate_limited()` is a decorator for
wrapping a standalone handler function with the same check.
"""
import time
import streamlit as st

DEFAULT_COOLDOWN = 0.5


def throttled(action_key, cooldown=DEFAULT_COOLDOWN):
    """True if `action_key` was last triggered less than `cooldown` seconds
    ago for this session. Records the current time as a side effect when
    not throttled, so consecutive calls naturally space themselves out."""
    now = time.time()
    timestamps = st.session_state.setdefault('_rate_limit_timestamps', {})
    last = timestamps.get(action_key, 0)
    if now - last < cooldown:
        return True
    timestamps[action_key] = now
    return False


def rate_limited(cooldown=DEFAULT_COOLDOWN, key=None, message="⏳ Action throttled. Please slow down."):
    """Decorator version of throttled() for standalone handler functions."""
    def decorator(func):
        action_key = key or f"{func.__module__}.{func.__qualname__}"

        def wrapper(*args, **kwargs):
            if throttled(action_key, cooldown):
                st.warning(message)
                return None
            return func(*args, **kwargs)
        return wrapper
    return decorator
