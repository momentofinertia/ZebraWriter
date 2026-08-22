from __future__ import annotations

import re
import subprocess
from pathlib import Path


PATTERNS = (
    ("private-key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("aws-access-key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("github-fine-grained-token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{40,}\b")),
    ("openai-key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{24,}\b")),
    ("google-api-key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
    (
        "assigned-secret",
        re.compile(
            r"(?i)\b(?:api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret|password)"
            r"\s*[:=]\s*['\"][A-Za-z0-9_./+=-]{24,}['\"]"
        ),
    ),
    ("credential-url", re.compile(r"https?://[^\s/:]+:[^\s/@]+@[^\s]+")),
)


def tracked_files() -> list[Path]:
    safe_directory = Path.cwd().resolve().as_posix()
    output = subprocess.check_output(
        ("git", "-c", f"safe.directory={safe_directory}", "ls-files", "-z")
    )
    return [Path(item.decode("utf-8")) for item in output.split(b"\0") if item]


def scan() -> list[tuple[Path, int, str]]:
    findings: list[tuple[Path, int, str]] = []
    for path in tracked_files():
        try:
            payload = path.read_bytes()
        except OSError:
            continue
        if b"\0" in payload:
            continue
        text = payload.decode("utf-8", errors="replace")
        for line_number, line in enumerate(text.splitlines(), 1):
            for name, pattern in PATTERNS:
                if pattern.search(line):
                    findings.append((path, line_number, name))
    return findings


def main() -> int:
    findings = scan()
    if findings:
        for path, line_number, name in findings:
            print(f"SECRET_SCAN_FAIL {path}:{line_number} pattern={name}")
        return 1
    print(f"SECRET_SCAN_OK tracked_files={len(tracked_files())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
