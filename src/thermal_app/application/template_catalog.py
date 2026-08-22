from __future__ import annotations

from datetime import datetime

from thermal_app.config import project_root
from thermal_app.domain.models import TemplateDefinition
from thermal_app.domain.template_schema import validate_template_definition


class TemplateCatalog:
    def __init__(self, definitions: tuple[TemplateDefinition, ...]) -> None:
        self._definitions = {definition.id: definition for definition in definitions}
        if len(self._definitions) != len(definitions):
            raise ValueError("Template id değerleri benzersiz olmalıdır.")
        for definition in definitions:
            validate_template_definition(definition)

    def get(self, template_id: str) -> TemplateDefinition:
        try:
            return self._definitions[template_id]
        except KeyError as exc:
            raise KeyError(f"Template bulunamadı: {template_id}") from exc

    def list_all(self) -> list[TemplateDefinition]:
        return list(self._definitions.values())

    def register_custom(self, template: TemplateDefinition) -> None:
        validate_template_definition(template)
        self._definitions[template.id] = template

    def remove_custom(self, template_id: str) -> None:
        self._definitions.pop(template_id, None)


def custom_definition(template_id: str, name: str, category: str, blocks: list[dict[str, object]]) -> TemplateDefinition:
    return TemplateDefinition(
        template_id,
        1,
        name,
        category,
        {"blocks": {"type": "blocks", "label": "Bloklar", "default": blocks, "required": True}},
        {},
        "custom.blocks",
    )


def built_in_definitions() -> tuple[TemplateDefinition, ...]:
    now = datetime.now().astimezone()
    today = now.strftime("%d.%m.%Y")
    return (
        TemplateDefinition(
            "todo.basic", 1, "Yapılacaklar", "Üretkenlik",
            {
                "title": {"type": "text", "label": "Başlık", "default": "Bugünün İşleri", "required": True},
                "date": {"type": "text", "label": "Tarih", "default": today},
                "priority_tasks": {
                    "type": "list",
                    "label": "Öncelikli görevler",
                    "default": ["Raporu tamamla", "Kargoyu teslim al", "Doktor randevusunu ara"],
                },
                "tasks": {
                    "type": "table", "label": "Diğer görevler",
                    "default": [
                        {"title": "Market alışverişi", "due_time": "18:00", "category": "Ev"},
                        {"title": "E-postaları yanıtla", "due_time": "", "category": "İş"},
                        {"title": "20 dakika yürüyüş", "due_time": "20:30", "category": "Kişisel"},
                    ],
                    "columns": [
                        {"key": "title", "label": "Görev"},
                        {"key": "due_time", "label": "Saat"},
                        {"key": "category", "label": "Kategori"},
                    ],
                },
                "note": {"type": "multiline", "label": "Not", "default": "Önce öncelikli görevleri tamamla."},
                "show_checkboxes": {"type": "boolean", "label": "Checkbox göster", "default": True},
            }, {}, "todo",
        ),
        TemplateDefinition(
            "shopping.basic", 1, "Alışveriş Listesi", "Günlük",
            {
                "title": {"type": "text", "label": "Başlık", "default": "Alışveriş Listesi", "required": True},
                "date": {"type": "text", "label": "Tarih", "default": today},
                "items": {
                    "type": "table", "label": "Ürünler",
                    "default": [
                        {"product": "Elma", "quantity": "1 kg", "category": "Manav"},
                        {"product": "Süt", "quantity": "2 adet", "category": "Süt Ürünleri"},
                        {"product": "Muz", "quantity": "5 adet", "category": "MANAV"},
                        {"product": "Ekmek", "quantity": "1 adet", "category": "Fırın"},
                        {"product": "Un", "quantity": "2 kg", "category": ""},
                    ],
                    "columns": [
                        {"key": "product", "label": "Ürün"},
                        {"key": "quantity", "label": "Miktar"},
                        {"key": "category", "label": "Kategori"},
                    ],
                },
                "show_checkboxes": {"type": "boolean", "label": "Checkbox göster", "default": True},
            }, {}, "shopping",
        ),
        TemplateDefinition(
            "recipe.basic", 1, "Tarif", "Mutfak",
            {
                "name": {"type": "text", "label": "Tarif adı", "required": True, "default": "Mercimek Çorbası"},
                "prep_time": {"type": "text", "label": "Hazırlama süresi", "default": "10 dk"},
                "cook_time": {"type": "text", "label": "Pişirme süresi", "default": "30 dk"},
                "servings": {"type": "text", "label": "Porsiyon", "default": "4"},
                "ingredients": {
                    "type": "list",
                    "label": "Malzemeler",
                    "default": [
                        "1 su bardağı kırmızı mercimek",
                        "1 adet kuru soğan",
                        "1 adet havuç",
                        "1 yemek kaşığı tereyağı",
                        "6 su bardağı sıcak su",
                        "1 yemek kaşığı un",
                        "1 çay kaşığı kırmızı toz biber",
                        "Tuz, karabiber ve kimyon",
                    ],
                },
                "steps": {
                    "type": "list",
                    "label": "Adımlar",
                    "default": [
                        "Soğanı ve havucu küçük küçük doğrayın.",
                        "Tereyağında sebzeleri 4-5 dakika kavurun.",
                        "Yıkanmış mercimeği ve sıcak suyu ekleyin.",
                        "Mercimekler yumuşayana kadar yaklaşık 25 dakika pişirin.",
                        "Blenderdan geçirip baharatları ekleyin.",
                        "Kıvam koyuysa azar azar sıcak su ilave edin.",
                        "Bir taşım daha kaynatıp ocağı kapatın.",
                        "Kaselere alıp sıcak servis edin.",
                    ],
                },
                "notes": {"type": "multiline", "label": "Notlar", "default": "Servis ederken limon ve pul biber ekleyebilirsiniz."},
            }, {}, "recipe",
        ),
        TemplateDefinition(
            "note.quick", 1, "Hızlı Not", "Notlar",
            {
                "title": {"type": "text", "label": "Başlık", "default": "Hatırlatma"},
                "text": {"type": "multiline", "label": "Not", "required": True, "default": "Kargoyu teslim al ve dönüşte marketten süt al."},
                "date_time": {"type": "text", "label": "Tarih / saat", "default": now.strftime("%d.%m.%Y %H:%M")},
                "include_qr": {"type": "boolean", "label": "Notu QR olarak ekle", "default": False},
            }, {}, "quick-note",
        ),
        TemplateDefinition(
            "photo.basic", 1, "Fotoğraf", "Görsel",
            {
                "image_path": {
                    "type": "image",
                    "label": "JPG / PNG",
                    "default": str(project_root() / "assets" / "samples" / "thermal-photo.png"),
                },
                "caption": {"type": "text", "label": "Açıklama", "default": "Termal fotoğraf ton testi"},
                "fit": {"type": "choice", "label": "Yerleşim", "choices": ["fit_width", "actual"], "default": "fit_width"},
                "rotation": {"type": "choice", "label": "Döndür", "choices": ["0", "90", "180", "270"], "default": "0"},
            }, {}, "photo",
        ),
        TemplateDefinition(
            "qr.basic", 1, "QR", "Kodlar",
            {
                "title": {"type": "text", "label": "Başlık", "default": "ZebraWriter QR"},
                "kind": {"type": "choice", "label": "Tür", "choices": ["URL", "Text", "Wi-Fi", "Phone", "Email", "Contact", "Custom"], "default": "URL"},
                "payload": {"type": "multiline", "label": "İçerik", "required": True, "default": "https://example.com"},
                "ssid": {"type": "text", "label": "Wi-Fi adı", "default": ""},
                "password": {"type": "text", "label": "Wi-Fi parolası", "default": ""},
                "caption": {"type": "text", "label": "Alt yazı", "default": "Telefonunuzla tarayın"},
            }, {}, "qr",
        ),
        TemplateDefinition(
            "system.calibration", 1, "Baskı Kalibrasyonu", "Sistem",
            {
                "left_offset_dots": {"type": "text", "label": "Ölçek başlangıcı (dot)", "default": "0"},
                "top_offset_dots": {"type": "text", "label": "Ölçek üst boşluğu (dot)", "default": "0"},
            }, {}, "calibration",
        ),
    )
