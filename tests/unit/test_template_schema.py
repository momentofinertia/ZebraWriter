import pytest

from thermal_app.application.template_catalog import TemplateCatalog, built_in_definitions
from thermal_app.domain.errors import TemplateValidationError
from thermal_app.domain.template_schema import normalize_template_input


def test_catalog_contains_six_user_templates_and_calibration() -> None:
    catalog = TemplateCatalog(built_in_definitions())
    assert [item.id for item in catalog.list_all()] == [
        "todo.basic",
        "shopping.basic",
        "recipe.basic",
        "note.quick",
        "photo.basic",
        "qr.basic",
        "system.calibration",
    ]


def test_schema_normalizes_table_rows_and_drops_empty_rows() -> None:
    definition = TemplateCatalog(built_in_definitions()).get("shopping.basic")
    data = normalize_template_input(
        definition,
        {
            "title": "Market",
            "date": "",
            "items": [
                {"product": "Süt", "quantity": "2", "category": "Süt"},
                {"product": "", "quantity": "", "category": ""},
            ],
            "show_checkboxes": True,
        },
    )
    assert data["items"] == [{"product": "Süt", "quantity": "2", "category": "Süt"}]


def test_required_field_is_rejected() -> None:
    definition = TemplateCatalog(built_in_definitions()).get("note.quick")
    with pytest.raises(TemplateValidationError, match="Zorunlu"):
        normalize_template_input(
            definition,
            {"title": "", "text": "", "date_time": "", "include_qr": False},
        )


def test_unknown_field_is_rejected() -> None:
    definition = TemplateCatalog(built_in_definitions()).get("todo.basic")
    with pytest.raises(TemplateValidationError, match="Bilinmeyen"):
        normalize_template_input(definition, {"unknown": "value"})
