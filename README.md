# ZebraWriter

ZebraWriter is a local Windows 10/11 desktop application for Zebra GC420t thermal printers, ZPL, 203 DPI output, and the Windows RAW print spooler.

Version `0.5.0` includes GC420t discovery and calibration, PDF/EPUB/DOCX text import, a block-based custom template designer, filtered history and artifact cleanup, ten ready-made examples in the Dashboard, a resizable live-preview editor, plain and graphic thermal styles, ZPL `^GFA` encoding, Windows RAW submission, print history, user presets, light/dark themes, Turkish and English interface options, and a Todoist API v1 integration backed by the operating system keyring.

ZebraWriter is an independent community project. It is not affiliated with, endorsed by, or sponsored by Zebra Technologies. Zebra and related product names are trademarks of their respective owners.

The Todoist token is never written to SQLite, settings files, or application logs. After validation in the Todoist tab, it is stored in Windows Credential Locker through the system keyring. When the network is unavailable, the last successful cache is explicitly marked as stale and one-click printing from stale Todoist data requires user confirmation.

## Features

- Zebra GC420t discovery through the Windows print spooler
- Configurable paper profiles and horizontal print calibration
- Deterministic 1-bit PNG previews and ZPL `^GFA` output
- Block-based custom templates with text, headings, dividers, images, and QR codes
- PDF, EPUB, and DOCX text import into editable receipt blocks
- Plain and thermal-safe graphic template styles
- Presets, local print history, and safe artifact cleanup
- Todoist personal-token integration using the Windows keyring
- Turkish and English user interface
- Light, dark, and system themes

## Requirements

- Windows 10 or Windows 11
- Python 3.12 or newer for development
- A Zebra GC420t printer for hardware acceptance

## Printer compatibility

The current application automatically discovers only the Zebra GC420t and uses a built-in 203 DPI GC420t profile. Its lower-level print path sends full-width 1-bit raster data as ZPL `^GFA` through the Windows RAW spooler. This makes the following 203 DPI, ZPL-capable Zebra printers reasonable candidates for future validation, but it does not make them officially supported yet.

| Printer or family | Current code-level status | Hardware validation |
| --- | --- | --- |
| Zebra GC420t | Built-in profile, automatic discovery, calibration, preview, ZPL encoding, and Windows RAW submission | Reference printer tested |
| Zebra GK420d / GK420t | Uses the same expected 203 DPI ZPL/RAW path; requires a dedicated profile and discovery rule | Not tested yet |
| Zebra GX420d / GX420t | Uses the same expected 203 DPI ZPL/RAW path; requires a dedicated profile and discovery rule | Not tested yet |
| Zebra ZD220 / ZD230 in ZPL mode | Candidate for the raster ZPL/RAW path; requires a dedicated profile and discovery rule | Not tested yet |
| Zebra ZD410 / ZD420 / ZD421 203 DPI variants | Candidate for the raster ZPL/RAW path; printable width and media settings must be profiled | Not tested yet |
| Zebra ZD620 / ZD621 203 DPI variants | Candidate for the raster ZPL/RAW path; printable width and media settings must be profiled | Not tested yet |

Models listed as `Not tested yet` are compatibility candidates, not a hardware-support promise. They are not currently returned by automatic printer discovery. Printer DPI, maximum printable width, media tracking, margins, and calibration must be represented by a model-specific profile and verified on real hardware before support is declared. ESC/POS-only printers, GDI-only printers, and non-ZPL devices are not supported by the current print path.

## Development

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m thermal_app
```

A job accepted by the Windows spooler is not proof that the label or receipt was physically printed. ZebraWriter reports this state as “Submitted to the printer queue.”

## Building the Windows onedir package

```powershell
.\scripts\build_release.ps1
```

The script runs the test suite, builds `dist\<version>\ZebraWriter\ZebraWriter.exe`, executes the packaged smoke test, verifies the release contents, and creates a ZIP archive with `SHA256SUMS.txt` under `release`.

Version-specific staging prevents DLL locks from an older running copy from affecting a new build. User data is stored under `%LOCALAPPDATA%\ZebraWriter`, outside the packaged application directory.

The Windows package is not code-signed and does not include an installer. Clean-machine acceptance on a separate Windows 10/11 computer without Python remains a release validation requirement.

## Security and privacy

- Credentials are stored through the operating system keyring and are not included in the repository.
- Runtime databases, logs, artifacts, build output, and local environment files are excluded from Git.
- CI scans tracked files for common high-confidence secret formats before running tests.
- Print artifacts and imported document paths remain local unless the user explicitly shares them.

If you discover a security issue, do not open a public issue containing credentials or private data. Revoke any exposed credential first, then report the issue without including the secret value.

## License

Copyright (C) 2026 Emre Harmandal.

ZebraWriter is released under the [GNU General Public License v3.0](LICENSE). Bundled font licensing and third-party dependency notices are listed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
