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


def has_console() -> bool:
    """True when the process owns a console window, as in a terminal launch.

    Autostart entries and shortcuts usually run without a console. A terminal
    launch is an explicit request to see the app, so it should not be silent.
    """
    if sys.platform == "win32":
        try:
            import ctypes

            get_console_window = ctypes.windll.kernel32.GetConsoleWindow
            get_console_window.restype = ctypes.c_void_p
            return bool(get_console_window())
        except Exception:
            return False
    try:
        return bool(sys.stdout is not None and sys.stdout.isatty())
    except Exception:
        return False


def should_show_window(
    start_minimized: bool, console_attached: bool, tray_available: bool
) -> bool:
    """Decide whether the main window opens at startup.

    ``start_minimized`` only has a safe meaning when there is a tray icon to
    restore the window from, and an explicit console launch always wins. A
    hidden window with no way back looks exactly like a failed launch.
    """
    if not start_minimized:
        return True
    return bool(console_attached or not tray_available)


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
    console = has_console()
    if should_show_window(
        config.app.start_minimized, console, window.tray.available
    ):
        if config.app.start_minimized:
            logger.info(
                "start_minimized ignored (console=%s, tray=%s)"
                % (console, window.tray.available),
                extra={"event": "app.start_minimized_ignored"},
            )
        window.show()
        application.processEvents()
    else:
        logger.info(
            "starting minimized to the tray",
            extra={"event": "app.start_minimized"},
        )
    context.start()

    try:
        return int(application.exec())
    finally:
        context.shutdown()


if __name__ == "__main__":  # pragma: no cover - process entry
    raise SystemExit(main())
