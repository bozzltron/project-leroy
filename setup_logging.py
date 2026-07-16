"""Centralized logging setup for Project Leroy.

All entry points (leroy.py, classify.py, visitation.py) call setup_logging()
early in their main(). Library modules (visitations.py, photo.py, etc.) just
import logging and use logging.getLogger(__name__) — they never configure.

The function is idempotent: calling it multiple times (e.g., from a test
that imports multiple entry points) won't double-add handlers.
"""
import logging
import sys
from pathlib import Path


_LOG_FORMAT = '%(asctime)s-%(name)s-%(levelname)s-%(message)s'
_LOG_FILE = 'storage/results.log'


def setup_logging(log_file=_LOG_FILE, level=logging.INFO):
    """Configure root logger with file + stderr handlers.

    Idempotent: if the root logger already has our FileHandler on the given
    path attached, this is a no-op. Safe to call from multiple entry points in
    the same process.
    """
    root = logging.getLogger()

    # Idempotency check: look for our FileHandler on the given path.
    for handler in root.handlers:
        if isinstance(handler, logging.FileHandler):
            try:
                if Path(handler.baseFilename).resolve() == Path(log_file).resolve():
                    return root
            except (AttributeError, OSError):
                pass

    # Ensure the log directory exists.
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(_LOG_FORMAT)

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(formatter)
    root.addHandler(stderr_handler)

    root.setLevel(level)
    return root
