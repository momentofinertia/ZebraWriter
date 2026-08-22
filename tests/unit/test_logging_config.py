from __future__ import annotations

import logging
from pathlib import Path

from thermal_app.logging_config import LOG_NAME, configure_logging, redact_text


def test_redact_text_masks_credentials() -> None:
    value = "Authorization: Bearer abc123 token=secret-token password=hunter2"
    redacted = redact_text(value)
    assert "abc123" not in redacted
    assert "secret-token" not in redacted
    assert "hunter2" not in redacted
    assert redacted.count("[REDACTED]") == 3


def test_configured_log_never_writes_token_plaintext(tmp_path: Path) -> None:
    configure_logging(tmp_path)
    logger = logging.getLogger("test.security")
    logger.error("Todoist token=%s", "do-not-store-this")
    for handler in logging.getLogger().handlers:
        handler.flush()
    payload = (tmp_path / LOG_NAME).read_text(encoding="utf-8")
    assert "do-not-store-this" not in payload
    assert "[REDACTED]" in payload
