import asyncio
import json
from typing import List, Optional

# Simple in-process event bus for SSE broadcasting

_subscribers: List[asyncio.Queue] = []
# Capture the main application event loop when the first subscriber connects,
# so background threads (APScheduler) can thread-safely publish messages.
_loop: Optional[asyncio.AbstractEventLoop] = None

def subscribe() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _subscribers.append(q)
    global _loop
    try:
        # Record the current running loop (ASGI server loop)
        _loop = asyncio.get_event_loop()
    except RuntimeError:
        _loop = None
    return q

def unsubscribe(q: asyncio.Queue) -> None:
    try:
        _subscribers.remove(q)
    except ValueError:
        pass

def publish(message: dict) -> None:
    """Publish a message to all subscribers (thread-safe scheduling)."""
    loop = _loop
    if loop is None:
        # No active subscribers yet or loop not captured
        return
    for q in list(_subscribers):
        try:
            loop.call_soon_threadsafe(q.put_nowait, message)
        except Exception:
            # Skip broken subscribers
            continue
