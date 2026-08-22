from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from thermal_app import __version__


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("package", type=Path)
    parser.add_argument("smoke_result", type=Path)
    arguments = parser.parse_args()
    package = arguments.package.resolve()
    smoke_path = arguments.smoke_result.resolve()
    required = (
        package / "ZebraWriter.exe",
        package / "README.md",
        package / "LICENSE",
        package / "THIRD_PARTY_NOTICES.md",
        package / "_internal" / "assets" / "fonts" / "Vera.ttf",
        package / "_internal" / "assets" / "fonts" / "VeraBd.ttf",
        package / "_internal" / "assets" / "licenses" / "bitstream-vera-license.txt",
        package / "_internal" / "PySide6" / "plugins" / "platforms" / "qwindows.dll",
    )
    missing = [str(path.relative_to(package)) for path in required if not path.is_file()]
    if missing:
        raise SystemExit(f"Eksik paket dosyaları: {', '.join(missing)}")
    smoke = json.loads(smoke_path.read_text(encoding="utf-8"))
    expected_smoke = {
        "ok": True,
        "version": __version__,
        "schema_version": 6,
        "tabs": 6,
    }
    for key, expected in expected_smoke.items():
        if smoke.get(key) != expected:
            raise SystemExit(
                f"Smoke doğrulaması başarısız: {key}={smoke.get(key)!r}, beklenen={expected!r}"
            )
    if int(smoke.get("templates", 0)) < 8:
        raise SystemExit("Paket içindeki test sayfası ve built-in şablonlar yüklenmedi.")
    if smoke.get("credential_backend") != "keyring.backends.Windows.WinVaultKeyring":
        raise SystemExit(
            f"Windows keyring backend yüklenmedi: {smoke.get('credential_backend')!r}"
        )

    manifest_path = package / "RELEASE-MANIFEST.json"
    files = []
    for path in sorted(item for item in package.rglob("*") if item.is_file() and item != manifest_path):
        files.append(
            {
                "path": path.relative_to(package).as_posix(),
                "size": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    manifest_path.write_text(
        json.dumps(
            {
                "product": "ZebraWriter",
                "version": __version__,
                "format": "windows-x64-onedir",
                "schema_version": smoke["schema_version"],
                "smoke": smoke,
                "files": files,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"verified_files={len(files)} version={__version__} manifest={manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
