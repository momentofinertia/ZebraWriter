from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from pathlib import Path
from shutil import copyfile

from thermal_app.application.dto import RenderOptions
from thermal_app.application.preset_catalog import built_in_example_presets
from thermal_app.bootstrap import build_context
from thermal_app.config import AppPaths
from thermal_app.domain.profiles import gc420t_profile


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    output = root / "output" / "graphic-output-smoke"
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    context = build_context(AppPaths.under(output / f"app-data-{stamp}"))
    printer = gc420t_profile("ZDesigner GC420t", "ZDesigner GC420t", "USB003")
    paper = next(item for item in context.paper_service.list_profiles() if item.id == "paper-56mm")
    paper = replace(paper, horizontal_content_offset_dots=0)
    presets = built_in_example_presets(context.template_catalog)
    generated: list[str] = []

    for index, preset in enumerate(presets, start=1):
        job = context.print_service.prepare(
            printer,
            paper,
            preset.template_id,
            data=preset.input_data,
            options=RenderOptions(visual_style="graphic"),
            source="graphic-smoke",
        )
        assert job.preview_artifact_path is not None
        target = output / f"{index:02d}-{preset.id.replace('.', '-')}.png"
        copyfile(job.preview_artifact_path, target)
        generated.append(f"{preset.template_id}={job.canvas_width}x{job.canvas_height}:{target}")

    print("\n".join(generated))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
