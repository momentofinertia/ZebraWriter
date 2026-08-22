from pathlib import Path

from thermal_app.application.dto import RenderOptions
from thermal_app.application.template_catalog import TemplateCatalog, built_in_definitions
from thermal_app.domain.profiles import default_paper_profiles
from thermal_app.domain.template_schema import normalize_template_input
from thermal_app.rendering.pillow_document_renderer import PillowDocumentRenderer


def test_manual_templates_have_ready_to_render_examples() -> None:
    catalog = TemplateCatalog(built_in_definitions())

    for template_id in (
        "todo.basic",
        "shopping.basic",
        "recipe.basic",
        "note.quick",
        "photo.basic",
        "qr.basic",
    ):
        definition = catalog.get(template_id)
        defaults = {
            key: field.get("default")
            for key, field in definition.input_schema.items()
            if "default" in field
        }
        assert defaults
        assert normalize_template_input(definition, {}) == defaults

    shopping_items = catalog.get("shopping.basic").input_schema["items"]["default"]
    assert isinstance(shopping_items, list)
    assert len(shopping_items) >= 5

    recipe = catalog.get("recipe.basic")
    assert len(recipe.input_schema["ingredients"]["default"]) >= 5
    assert len(recipe.input_schema["steps"]["default"]) >= 5

    photo_path = Path(str(catalog.get("photo.basic").input_schema["image_path"]["default"]))
    assert photo_path.is_file()


def test_recipe_example_renders_as_a_full_length_receipt(
    font_paths: tuple[Path, Path],
) -> None:
    catalog = TemplateCatalog(built_in_definitions())
    recipe = catalog.get("recipe.basic")
    renderer = PillowDocumentRenderer(*font_paths)

    document = renderer.render(
        recipe,
        normalize_template_input(recipe, {}),
        default_paper_profiles()[0],
        RenderOptions(),
    )

    assert document.height_dots >= 900
