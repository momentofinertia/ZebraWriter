# Third-party notices

ZebraWriter is licensed under GPL-3.0-only. The Windows onedir package also contains third-party components under their own licenses. Those licenses continue to apply to the respective components.

## Bitstream Vera fonts

`assets/fonts/Vera.ttf` and `assets/fonts/VeraBd.ttf` are Copyright (c) 2003 Bitstream, Inc. and are distributed under the Bitstream Vera Font License. The complete notice is included at `assets/licenses/bitstream-vera-license.txt` and is bundled with every Windows package.

## Runtime dependencies

The release candidate is built with these direct runtime dependencies:

- Pillow — MIT-CMU
- pypdf — BSD-3-Clause
- PySide6, PySide6 Essentials and Shiboken6 — LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only; ZebraWriter is distributed under GPL-3.0-only
- pywin32 — PSF License
- qrcode — BSD
- keyring — MIT

The authoritative license texts and source locations are provided by each upstream project and its installed package metadata. The package keeps Qt/PySide shared libraries as separate files in the onedir layout; they are not statically linked into `ZebraWriter.exe`.

Upstream references:

- Qt for Python: https://doc.qt.io/qtforpython-6/
- Pillow: https://python-pillow.github.io/
- pypdf: https://pypdf.readthedocs.io/
- pywin32: https://github.com/mhammond/pywin32
- qrcode: https://github.com/lincolnloop/python-qrcode
- keyring: https://github.com/jaraco/keyring
