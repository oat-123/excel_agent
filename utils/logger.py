"""
utils/logger.py — Global live-log bus for J.A.R.V.I.S.

All backend modules call push_log(msg) to stream realtime process
steps to the frontend via the /logs SSE-style polling endpoint.
"""
from queue import Queue
from datetime import datetime

LIVE_LOGS: Queue = Queue()

# Maximum messages kept in queue before oldest are dropped
_MAX_QUEUE = 200


def push_log(msg: str, level: str = "info") -> None:
    """
    Push a log message to the live queue and stdout.

    level: "info" | "success" | "warning" | "error"
    The frontend uses the prefix tag (e.g. [DB], [Excel]) for colour coding,
    so level is optional metadata only.
    """
    ts = datetime.now().strftime("%H:%M:%S")
    formatted = f"[{ts}] {msg}"
    print(formatted)

    # Drop oldest if queue is full to prevent memory leak on long sessions
    if LIVE_LOGS.qsize() >= _MAX_QUEUE:
        try:
            LIVE_LOGS.get_nowait()
        except Exception:
            pass

    LIVE_LOGS.put(formatted)
