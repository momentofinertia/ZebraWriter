from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from thermal_app import __version__


def _arguments(argv: list[str]) -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--smoke-test", action="store_true")
    parser.add_argument("--data-dir", type=Path)
    return parser.parse_known_args(argv)


def main() -> int:
    arguments, qt_arguments = _arguments(sys.argv[1:])
    if arguments.smoke_test:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QMessageBox

    from thermal_app.bootstrap import build_context
    from thermal_app.config import AppPaths
    from thermal_app.infrastructure.storage.database import Database
    from thermal_app.logging_config import configure_logging
    from thermal_app.ui.main_window import MainWindow
    from thermal_app.ui.localization import set_language, tr
    from thermal_app.ui.theme import configure_application_font

    paths = AppPaths.under(arguments.data_dir) if arguments.data_dir else AppPaths.default()
    paths.ensure()
    configure_logging(paths.logs)
    logger = logging.getLogger("thermal_app.startup")
    app = QApplication([sys.argv[0], *qt_arguments])
    app.setApplicationName("ZebraWriter")
    app.setOrganizationName("ZebraWriter")
    app.setApplicationVersion(__version__)
    try:
        configure_application_font(app)
        context = build_context(paths)
        set_language(context.settings_service.language())
        window = MainWindow(context)
        window.show()
        schema_version = Database(paths.database).schema_version()
        logger.info("application_started version=%s schema=%s", __version__, schema_version)
    except Exception as exc:
        logger.exception("startup_failed error_type=%s", type(exc).__name__)
        if arguments.smoke_test:
            (paths.root / "smoke-result.json").write_text(
                json.dumps({"ok": False, "error_type": type(exc).__name__}),
                encoding="utf-8",
            )
        else:
            QMessageBox.critical(
                None,
                tr("ZebraWriter başlatılamadı"),
                tr("Uygulama başlatılamadı. Ayrıntılar güvenli log dosyasına yazıldı."),
            )
        return 1

    if arguments.smoke_test:
        def finish_smoke() -> None:
            from thermal_app.infrastructure.credentials import SystemKeyringCredentialStore

            keyring_module = SystemKeyringCredentialStore._keyring()
            keyring_backend = keyring_module.get_keyring()
            result = {
                "ok": True,
                "version": __version__,
                "schema_version": schema_version,
                "tabs": window._tabs.count(),
                "printers": window._printer_combo.count(),
                "templates": window._template_combo.count(),
                "font_family": app.font().family(),
                "credential_backend": f"{type(keyring_backend).__module__}.{type(keyring_backend).__name__}",
            }
            (paths.root / "smoke-result.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            logger.info("smoke_test_completed result=ok")
            app.exit(0)

        QTimer.singleShot(2200, finish_smoke)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
