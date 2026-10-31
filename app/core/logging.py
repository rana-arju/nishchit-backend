import logging
import re
import sys

from app.core.middleware import get_request_id

_SENSITIVE_PATTERNS = [
    re.compile(r"(?i)(password|passwd|pwd)\s*[:=]\s*\S+"),
    re.compile(r"(?i)(api[_-]?key|token|secret)\s*[:=]\s*\S+"),
    re.compile(r"(?i)bearer\s+[a-z0-9\-._~+/]+=*"),
    re.compile(r"(?:\+?88)?01[3-9]\d{8}"),
]


def mask_sensitive(text: str) -> str:
    masked = text
    for pattern in _SENSITIVE_PATTERNS:
        masked = pattern.sub("[REDACTED]", masked)
    return masked


class RequestIdLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestIdLogFilter())
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | request_id=%(request_id)s | %(message)s"
        )
    )
    logging.basicConfig(level=level, handlers=[handler], force=True)
