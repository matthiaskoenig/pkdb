"""ULIDs for review items: 48 bits of milliseconds and 80 random bits.

Within a process the identifiers strictly increase, also within one
millisecond and when the clock goes back, so new items sort last.
"""

import os
import threading
import time

ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_lock = threading.Lock()
_last = (0, 0)


def _encode(value: int, length: int) -> str:
    characters = []
    for _ in range(length):
        value, index = divmod(value, 32)
        characters.append(ALPHABET[index])
    return "".join(reversed(characters))


def new_ulid(now_ms: int | None = None) -> str:
    global _last
    with _lock:
        milliseconds = int(time.time() * 1000) if now_ms is None else now_ms
        last_milliseconds, last_random = _last
        if milliseconds <= last_milliseconds:
            milliseconds, random = last_milliseconds, last_random + 1
            if random >= 1 << 80:
                milliseconds, random = milliseconds + 1, 0
        else:
            random = int.from_bytes(os.urandom(10))
        _last = (milliseconds, random)
    return _encode(milliseconds, 10) + _encode(random, 16)
