from __future__ import annotations

from thermal_app.rendering.primitives import Checkbox, Text
from thermal_app.rendering.template_builders import ShoppingBuilder


def test_shopping_categories_are_grouped_case_and_format_insensitively() -> None:
    elements = ShoppingBuilder().build(
        {
            "title": "Alışveriş",
            "items": [
                {"product": "Elma", "quantity": "5 kg", "category": "Manav"},
                {"product": "Un", "quantity": "2 kg", "category": ""},
                {"product": "Muz", "quantity": "5 adet", "category": " MANAV\u200b "},
            ],
            "show_checkboxes": True,
        }
    )

    headings = [element.value for element in elements if isinstance(element, Text) and element.style == "heading"]
    products = [element.label for element in elements if isinstance(element, Checkbox)]

    assert headings == ["MANAV", "DIĞER"]
    assert products == ["Elma", "Muz", "Un"]
