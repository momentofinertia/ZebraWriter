from __future__ import annotations

import argparse

from thermal_app.application.dto import RenderOptions
from thermal_app.bootstrap import build_context
from thermal_app.config import AppPaths, project_root


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--only",
        choices=("system.calibration", "photo.basic", "qr.basic"),
        help="Yalnızca seçilen kabul baskısını gönderir.",
    )
    args = parser.parse_args()
    context = build_context(AppPaths.under(project_root() / "output" / "phase3-calibrated"))
    printers = context.printer_service.discover_gc420t()
    if len(printers) != 1:
        raise RuntimeError(f"Bir GC420t bekleniyordu; bulunan: {len(printers)}")
    printer = printers[0]
    paper = next(profile for profile in context.paper_service.list_profiles() if profile.id == "paper-56mm")
    if paper.horizontal_content_offset_dots != -7:
        raise RuntimeError("56 mm profilinin yatay içerik konumu -7 dot değil.")

    jobs = (
        (
            "system.calibration",
            {"left_offset_dots": "0", "top_offset_dots": "0"},
            RenderOptions(),
        ),
        (
            "photo.basic",
            {
                "image_path": str(project_root() / "output" / "phase3-acceptance" / "thermal-photo.png"),
                "caption": "7 dot sola kalibre edilmiş fotoğraf",
                "fit": "fit_width",
                "rotation": "0",
            },
            RenderOptions(dithering="atkinson", sharpen=True),
        ),
        (
            "qr.basic",
            {
                "title": "ZebraWriter QR",
                "kind": "URL",
                "payload": "https://example.com/zebrawriter",
                "ssid": "",
                "password": "",
                "caption": "7 dot sola kalibre edildi",
            },
            RenderOptions(),
        ),
    )
    results: list[tuple[str, str]] = []
    for template_id, data, options in jobs:
        if args.only and template_id != args.only:
            continue
        prepared = context.print_service.prepare(
            printer,
            paper,
            template_id,
            data=data,
            options=options,
            source="phase3-calibrated-hardware-acceptance",
        )
        submitted = context.print_service.submit(prepared.id)
        results.append((template_id, submitted.transport_job_id or ""))
    print(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
