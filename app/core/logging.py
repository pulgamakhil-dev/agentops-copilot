import contextvars
import logging
import sys
from logging.config import dictConfig

from app.core.config import get_settings


# Stores the current request ID for the active execution context.
request_id_context: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id",
    default="-",
)


class RequestIdFilter(logging.Filter):
    """
    Inject the current request ID into every log record.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_context.get()
        return True


def set_request_id(request_id: str) -> None:
    """
    Set the request ID for the current execution context.
    """

    request_id_context.set(request_id)


def clear_request_id() -> None:
    """
    Reset the request ID after request processing completes.
    """

    request_id_context.set("-")


def configure_logging() -> None:
    settings = get_settings()

    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,

        "filters": {
            "request_id": {
                "()": RequestIdFilter,
            }
        },

        "formatters": {
            "standard": {
                "format": (
                    "%(asctime)s | %(levelname)s | "
                    "%(name)s | request_id=%(request_id)s | "
                    "%(message)s"
                )
            }
        },

        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "filters": ["request_id"],
                "stream": sys.stdout,
            }
        },

        "root": {
            "handlers": ["console"],
            "level": settings.log_level,
        },
    }

    dictConfig(logging_config)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)