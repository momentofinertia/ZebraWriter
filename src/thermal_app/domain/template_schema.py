from __future__ import annotations

from collections.abc import Mapping, Sequence

from thermal_app.domain.errors import TemplateValidationError
from thermal_app.domain.models import TemplateDefinition


SUPPORTED_FIELD_TYPES = {
    "text",
    "multiline",
    "boolean",
    "choice",
    "list",
    "table",
    "image",
    "blocks",
}


def validate_template_definition(definition: TemplateDefinition) -> None:
    if not definition.id or definition.version < 1 or not definition.renderer_key:
        raise TemplateValidationError("Template metadata eksik veya geçersiz.")
    for key, raw_spec in definition.input_schema.items():
        if not isinstance(key, str) or not isinstance(raw_spec, Mapping):
            raise TemplateValidationError("Template alan şeması mapping olmalıdır.")
        field_type = raw_spec.get("type")
        if field_type not in SUPPORTED_FIELD_TYPES:
            raise TemplateValidationError(f"Desteklenmeyen alan tipi: {field_type}")
        if field_type == "choice" and not raw_spec.get("choices"):
            raise TemplateValidationError(f"Choice alanında seçenek yok: {key}")
        if field_type == "table" and not raw_spec.get("columns"):
            raise TemplateValidationError(f"Table alanında kolon yok: {key}")
        if field_type == "blocks" and not isinstance(raw_spec.get("default", []), Sequence):
            raise TemplateValidationError(f"Blocks alanı liste olmalıdır: {key}")


def normalize_template_input(
    definition: TemplateDefinition,
    data: Mapping[str, object],
) -> dict[str, object]:
    validate_template_definition(definition)
    normalized: dict[str, object] = {}
    unknown = set(data) - set(definition.input_schema)
    if unknown:
        raise TemplateValidationError(f"Bilinmeyen template alanları: {', '.join(sorted(unknown))}")

    for key, raw_spec in definition.input_schema.items():
        spec = dict(raw_spec)
        value = data.get(key, spec.get("default"))
        if spec.get("required") and _is_empty(value):
            raise TemplateValidationError(f"Zorunlu alan boş: {spec.get('label', key)}")
        if value is None:
            normalized[key] = None
            continue
        field_type = str(spec["type"])
        normalized[key] = _normalize_value(key, field_type, value, spec)
    return normalized


def _normalize_value(key: str, field_type: str, value: object, spec: Mapping[str, object]) -> object:
    if field_type in {"text", "multiline", "image"}:
        if not isinstance(value, str):
            raise TemplateValidationError(f"{key} metin olmalıdır.")
        return value.strip()
    if field_type == "boolean":
        if not isinstance(value, bool):
            raise TemplateValidationError(f"{key} true/false olmalıdır.")
        return value
    if field_type == "choice":
        if value not in spec.get("choices", ()):
            raise TemplateValidationError(f"{key} geçerli seçeneklerden biri olmalıdır.")
        return value
    if field_type == "list":
        if isinstance(value, str) or not isinstance(value, Sequence):
            raise TemplateValidationError(f"{key} liste olmalıdır.")
        return [str(item).strip() for item in value if str(item).strip()]
    if field_type == "table":
        if isinstance(value, str) or not isinstance(value, Sequence):
            raise TemplateValidationError(f"{key} satır listesi olmalıdır.")
        columns = [str(column["key"]) for column in spec.get("columns", ())]
        rows: list[dict[str, str]] = []
        for row in value:
            if not isinstance(row, Mapping):
                raise TemplateValidationError(f"{key} satırları mapping olmalıdır.")
            normalized_row = {column: str(row.get(column, "")).strip() for column in columns}
            if any(normalized_row.values()):
                rows.append(normalized_row)
        return rows
    if field_type == "blocks":
        if isinstance(value, str) or not isinstance(value, Sequence):
            raise TemplateValidationError(f"{key} blok listesi olmalıdır.")
        allowed = {"text", "heading", "divider", "spacer", "section_band", "key_value", "checklist", "image", "qr"}
        blocks: list[dict[str, object]] = []
        for block in value:
            if not isinstance(block, Mapping) or str(block.get("type", "")) not in allowed:
                raise TemplateValidationError(f"{key} içinde geçersiz blok tipi var.")
            blocks.append(dict(block))
        if not blocks:
            raise TemplateValidationError(f"{key} en az bir blok içermelidir.")
        return blocks
    raise TemplateValidationError(f"Desteklenmeyen alan tipi: {field_type}")


def _is_empty(value: object) -> bool:
    return value is None or value == "" or value == [] or value == ()
