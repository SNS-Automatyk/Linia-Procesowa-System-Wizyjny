import logging
from collections import deque
from datetime import datetime
from typing import Deque, Dict, List, Optional


class InMemoryLogHandler(logging.Handler):
    """A logging handler that stores recent log records in memory.

    Use get_logs() to retrieve logs in a JSON-serializable form.
    """

    def __init__(self, maxlen: int = 100):
        super().__init__()
        self.records: Deque[logging.LogRecord] = deque(maxlen=maxlen)

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)

    def get_logs(
        self, limit: Optional[int] = None, level: Optional[int] = None
    ) -> List[Dict]:
        items = list(self.records)
        if level is not None:
            items = [r for r in items if r.levelno >= level]
        if limit is not None:
            items = items[-limit:]
        return [self._serialize(r) for r in items]

    @staticmethod
    def _serialize(record: logging.LogRecord) -> Dict:
        message = record.getMessage()
        exc_text = None
        if record.exc_info:
            try:
                exc_text = logging.Formatter().formatException(record.exc_info)
            except Exception:
                exc_text = str(record.exc_info)
        return {
            "time": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": message,
            "module": record.module,
            "funcName": record.funcName,
            "line": record.lineno,
            "exception": exc_text,
        }


def setup_in_memory_logging(
    logger_name: str = "system_wizyjny", level: int = logging.INFO, maxlen: int = 100
) -> InMemoryLogHandler:
    """Attach an in-memory handler to the specified logger and return it."""
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)

    # Avoid duplicate handlers if called multiple times
    for h in logger.handlers:
        if isinstance(h, InMemoryLogHandler):
            return h

    handler = InMemoryLogHandler(maxlen=maxlen)
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return handler
