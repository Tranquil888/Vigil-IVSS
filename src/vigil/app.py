"""Process entry point. Qt starts before any worker thread does."""

from __future__ import annotations

import logging
import multiprocessing
import sys
import traceback
from typing import Optional, Sequence

from .config.loader import ConfigError, load_config
from .core.app_context import AppContext
from .paths import log_dir
from .telemetry.logging_setup import prune_old_logs, setup_logging

log = logging.getLogger(__name__)


def install_exception_hook(logger: logging.Logger) -> None:
    def hook(exc_type, exc_value, exc_tb) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        logger.error(
            "unhandled exception",
            exc_info=(exc_type, exc_value, exc_tb),
            extra={"event": "app.unhandled"},
        )
        traceback.print_exception(exc_type, exc_value, exc_tb)

    sys.excepthook = hook


def main(argv: Optional[Sequence[str]] = None) -> int:
    multiprocessing.freeze_support()

    try:
        config = load_config()
    except ConfigError as err:
        print("Vigil: %s" % err, file=sys.stderr)
        return 2

    logger = setup_logging(log_dir(config), level=config.app.log_level, force=True)
    prune_old_logs(log_dir(config), config.storage.log_retention_days)
    install_exception_hook(logger)

    from PySide6.QtWidgets import QApplication

    from .gui.shell import MainWindow

    application = QApplication(list(argv) if argv is not None else sys.argv)
    application.setApplicationName("Vigil")

    context = AppContext(config)
    window = MainWindow(context, config)
    if not config.app.start_minimized:
        window.show()
        application.processEvents()
    context.start()

    try:
        return int(application.exec())
    finally:
        context.shutdown()


if __name__ == "__main__":  # pragma: no cover - process entry
    raise SystemExit(main())
