from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

from thermal_app.application.dto import RenderOptions
from thermal_app.application.template_catalog import TemplateCatalog
from thermal_app.domain.models import Preset
from thermal_app.domain.template_schema import normalize_template_input


BUILT_IN_PRESET_PREFIX = "builtin.example."


def built_in_example_presets(
    catalog: TemplateCatalog,
    *,
    now: datetime | None = None,
) -> tuple[Preset, ...]:
    created_at = now or datetime.now().astimezone()
    today = created_at.strftime("%d.%m.%Y")
    definitions = (
        ("todo", "Örnek — Günlük Yapılacaklar", "todo.basic", {}),
        ("shopping", "Örnek — Market Alışverişi", "shopping.basic", {}),
        ("recipe", "Örnek — Mercimek Çorbası", "recipe.basic", {}),
        ("note", "Örnek — Hatırlatma Notu", "note.quick", {}),
        ("photo", "Örnek — Termal Fotoğraf Testi", "photo.basic", {}),
        ("qr", "Örnek — Web Sitesi QR", "qr.basic", {}),
        (
            "agenda",
            "Örnek — Toplantı Gündemi",
            "todo.basic",
            {
                "title": "Toplantı Gündemi",
                "priority_tasks": ["Gündem maddelerini onayla", "Karar sahiplerini belirle"],
                "tasks": [
                    {"title": "Satış sonuçlarını incele", "due_time": "09:30", "category": "İş"},
                    {"title": "Yeni sprint planını paylaş", "due_time": "10:15", "category": "Proje"},
                ],
                "note": "Toplantı sonunda aksiyonları ve sorumluları not et.",
            },
        ),
        (
            "medication",
            "Örnek — İlaç Takibi",
            "note.quick",
            {
                "title": "İlaç Takibi",
                "text": "08:00 — Sabah ilacı\n13:00 — Su iç\n20:00 — Akşam ilacı",
                "date_time": today,
            },
        ),
        (
            "breakfast",
            "Örnek — Kahvaltı Listesi",
            "shopping.basic",
            {
                "title": "Kahvaltı Listesi",
                "items": [
                    {"product": "Yumurta", "quantity": "10 adet", "category": "Soğuk"},
                    {"product": "Beyaz peynir", "quantity": "500 g", "category": "Soğuk"},
                    {"product": "Domates", "quantity": "1 kg", "category": "Manav"},
                    {"product": "Çay", "quantity": "1 paket", "category": "Kiler"},
                ],
            },
        ),
        (
            "contact",
            "Örnek — Acil İletişim QR",
            "qr.basic",
            {
                "title": "Acil İletişim",
                "kind": "Phone",
                "payload": "+905551112233",
                "caption": "Telefon etmek için tarayın",
            },
        ),
    )
    render_options = asdict(RenderOptions())
    return tuple(
        Preset(
            id=f"{BUILT_IN_PRESET_PREFIX}{preset_key}",
            name=name,
            template_id=template_id,
            paper_profile_id="paper-56mm",
            printer_profile_id=None,
            integration_profile_id=None,
            filter_spec={},
            sort_spec={},
            input_data=normalized,
            render_options=render_options,
            pinned=False,
            created_at=created_at,
            updated_at=created_at,
        )
        for preset_key, name, template_id, overrides in definitions
        for normalized in (normalize_template_input(catalog.get(template_id), overrides),)
    )


def is_built_in_preset_id(preset_id: str) -> bool:
    return preset_id.startswith(BUILT_IN_PRESET_PREFIX)
