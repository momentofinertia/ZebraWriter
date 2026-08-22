from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractButton,
    QComboBox,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QTabWidget,
    QTableWidget,
    QWidget,
)


SUPPORTED_LANGUAGES = ("tr", "en")
_language = "tr"


_EN: dict[str, str] = {
    "Ayarlar": "Settings",
    "ZebraWriter görünümünü, editör davranışını ve yerel verileri yönetin.": "Manage ZebraWriter appearance, editor behavior, and local data.",
    "Görünüm ve editör": "Appearance and editor",
    "Tema": "Theme",
    "Sistem": "System",
    "Açık": "Light",
    "Koyu": "Dark",
    "Dil": "Language",
    "Türkçe": "Türkçe",
    "English": "English",
    "Yazdırma ekranında önizlemeyi göster": "Show preview on the print screen",
    "Editör yerleşimini varsayılana döndür": "Reset editor layout",
    "Veri ve artefaktlar": "Data and artifacts",
    "Presetler, özel şablonlar, geçmiş ve ayarlar yalnızca bu bilgisayarda tutulur.": "Presets, custom templates, history, and settings are stored only on this computer.",
    "Uygulama verileri": "Application data",
    "Baskı artefaktları": "Print artifacts",
    "Veri klasörünü aç": "Open data folder",
    "Artefakt klasörünü aç": "Open artifacts folder",
    "Yazdırma ve güvenlik": "Printing and security",
    "• Windows yazıcı kuyruğuna teslim edilen iş, fiziksel baskı garantisi anlamına gelmez.": "• A job accepted by the Windows print queue is not a guarantee of physical printing.",
    "• PNG, bitmap ve ZPL artefaktları geçmiş kaydıyla birlikte güvenli yerel klasörde tutulur.": "• PNG, bitmap, and ZPL artifacts are stored with history in a safe local folder.",
    "• Todoist tokenı veritabanına veya loglara yazılmaz; Windows kimlik bilgileri kasası kullanılır.": "• The Todoist token is never written to the database or logs; Windows Credential Locker is used.",
    "Uygulama": "Application",
    "Sürüm": "Version",
    "Sürüm: {version}": "Version: {version}",
    "geliştirme": "development",
    "Referans yazıcı: Zebra GC420t · RAW/ZPL · 203 DPI": "Reference printer: Zebra GC420t · RAW/ZPL · 203 DPI",
    "Destek: Windows 10/11 · Türkçe karakterli termal çıktılar": "Support: Windows 10/11 · thermal output with Turkish characters",
    "Dashboard": "Dashboard",
    "Yazdır": "Print",
    "Tasarımcı": "Designer",
    "Geçmiş": "History",
    "Todoist": "Todoist",
    "Baskı oluştur": "Create print",
    "Şablonu düzenleyin ve sonucu baskıdan önce kontrol edin.": "Edit the template and review the result before printing.",
    "1 · Yazıcı ve kağıt": "1 · Printer and paper",
    "Yazıcıyı yenile": "Refresh printer",
    "Kağıt profili": "Paper profile",
    "Yeni": "New",
    "Düzenle": "Edit",
    "Sil": "Delete",
    "2 · İçerik": "2 · Content",
    "Şablon": "Template",
    "Yapılacaklar": "Todo List",
    "Alışveriş Listesi": "Shopping List",
    "Tarif": "Recipe",
    "Hızlı Not": "Quick Note",
    "Fotoğraf": "Photo",
    "Baskı Kalibrasyonu": "Print Calibration",
    "Öncelikli görevler": "Priority tasks",
    "Diğer görevler": "Other tasks",
    "Not": "Note",
    "Notlar": "Notes",
    "Checkbox göster": "Show checkboxes",
    "Ürünler": "Products",
    "Ürün": "Product",
    "Miktar": "Quantity",
    "Tarif adı": "Recipe name",
    "Hazırlama süresi": "Preparation time",
    "Pişirme süresi": "Cooking time",
    "Porsiyon": "Servings",
    "Malzemeler": "Ingredients",
    "Adımlar": "Steps",
    "Tarih / saat": "Date / time",
    "Notu QR olarak ekle": "Include note as QR",
    "Açıklama": "Caption",
    "Yerleşim": "Layout",
    "Döndür": "Rotate",
    "Tür": "Type",
    "İçerik": "Content",
    "Wi-Fi adı": "Wi-Fi name",
    "Wi-Fi parolası": "Wi-Fi password",
    "Alt yazı": "Caption",
    "Ölçek başlangıcı (dot)": "Scale start (dots)",
    "Ölçek üst boşluğu (dot)": "Scale top spacing (dots)",
    "İçerik ve şablon düzenleme artık Tasarımcı sekmesinden yapılır.": "Content and template editing is handled in the Designer tab.",
    "Tasarımcıyı aç": "Open Designer",
    "3 · Görüntü ayarları": "3 · Image settings",
    "Fotoğraf ve grafiklerin termal baskı yoğunluğunu ayarlayın.": "Adjust thermal print density for photos and graphics.",
    "Tarama yöntemi": "Dithering method",
    "Görsel stil": "Visual style",
    "Sade": "Plain",
    "Grafikli": "Graphic",
    "Parlaklık": "Brightness",
    "Kontrast": "Contrast",
    "Siyah eşiği": "Black threshold",
    "Keskinleştir": "Sharpen",
    "Ters çevir": "Invert",
    "Yakınlaştırma": "Zoom",
    "Genişliğe sığdır": "Fit width",
    "Pencereye sığdır": "Fit window",
    "Önizle": "Preview",
    "Önizlemeyi gizle": "Hide preview",
    "Önizlemeyi göster": "Show preview",
    "Preset kaydet": "Save preset",
    "YAZDIR": "PRINT",
    "KALİBRASYON YAZDIR": "PRINT CALIBRATION",
    "GC420t aranıyor…": "Searching for GC420t…",
    "GC420t bulunamadı": "GC420t not found",
    "GC420t hazır": "GC420t ready",
    "Önizleme hazırlanmadı": "Preview not generated",
    "Baskı önizlemesi": "Print preview",
    "Bu görüntü encoder'a verilen 1-bit raster artefaktıdır.": "This image is the 1-bit raster artifact supplied to the encoder.",
    "Yatay baskı kalibrasyonu": "Horizontal print calibration",
    "Negatif değer sola, pozitif değer sağa taşır.": "Negative moves left; positive moves right.",
    "±12 dot dışındaki değerler 56 mm kağıtta içeriğin bir bölümünü sınır dışına taşıyabilir.": "Values beyond ±12 dots may move part of the content outside 56 mm paper.",
    "1 dot sola": "1 dot left",
    "1 dot sağa": "1 dot right",
    "Ofseti kağıt profiline kaydet": "Save offset to paper profile",
    "Dashboard — hazır örnekler ve kullanıcı presetleri": "Dashboard — ready-made examples and user presets",
    "Ad": "Name",
    "Kağıt": "Paper",
    "Yenile": "Refresh",
    "Tek tık yazdır": "One-click print",
    "Editörde aç": "Open in editor",
    "Baskı geçmişi — ‘gönderildi’ fiziksel baskı garantisi değildir.": "Print history — ‘submitted’ is not a guarantee of physical printing.",
    "Tarih": "Date",
    "Durum": "Status",
    "Kuyruk işi": "Queue job",
    "Kaynak": "Source",
    "Tekrar yazdır / retry": "Reprint / retry",
    "Kopyala ve düzenle": "Copy and edit",
    "Kuyruktan iptal et": "Cancel from queue",
    "Geçmişten sil": "Delete from history",
    "Başlangıç YYYY-AA-GG": "Start YYYY-MM-DD",
    "Bitiş YYYY-AA-GG": "End YYYY-MM-DD",
    "Tüm durumlar": "All statuses",
    "Hazır": "Ready",
    "Kuyruğa gönderiliyor": "Submitting",
    "Gönderildi": "Submitted",
    "Başarısız": "Failed",
    "İptal edildi": "Cancelled",
    "Filtrele": "Filter",
    "Filtreli geçmişi sil": "Delete filtered history",
    "Tüm geçmişi sil": "Delete all history",
    "0 kayıt": "0 records",
    "Todoist kişisel token bağlantısı": "Todoist personal token connection",
    "Kişisel API tokenı — yalnızca keyring’e kaydedilir": "Personal API token — stored only in the keyring",
    "Bağlan ve doğrula": "Connect and verify",
    "Bağlantıyı kaldır": "Disconnect",
    "Filtre": "Filter",
    "Proje": "Project",
    "Filtre değeri": "Filter value",
    "Bugün": "Today",
    "Geciken": "Overdue",
    "Bugün + geciken": "Today + overdue",
    "Yaklaşan 7 gün": "Next 7 days",
    "Etiket": "Label",
    "Öncelik": "Priority",
    "Özel filtre": "Custom filter",
    "Etiket, 1-4 öncelik veya Todoist filtre sorgusu": "Label, priority 1-4, or Todoist filter query",
    "Senkronize et": "Sync",
    "Todoist bağlı değil": "Todoist not connected",
    "Todoist bağlı": "Todoist connected",
    "Görev": "Task",
    "Saat": "Time",
    "Todo şablonuna aktar": "Send to todo template",
    "Alışveriş şablonuna aktar": "Send to shopping template",
    "Belge aktar": "Import document",
    "Kaydet": "Save",
    "Yazdırma ekranına geç": "Open print screen",
    "Preset olarak kaydet": "Save as preset",
    "Kategori": "Category",
    "Özel": "Custom",
    "Bloklar": "Blocks",
    "Blok ekle": "Add block",
    "Çoğalt": "Duplicate",
    "Yukarı": "Move up",
    "Aşağı": "Move down",
    "Seçili blok": "Selected block",
    "Tip": "Type",
    "Değer / metin": "Value / text",
    "İkincil değer": "Secondary value",
    "Metin stili": "Text style",
    "Hizalama": "Alignment",
    "Boşluk / kalınlık (dot)": "Spacing / thickness (dots)",
    "Checkbox": "Checkbox",
    "İşaretli": "Checked",
    "Metin": "Text",
    "Başlık": "Heading",
    "Ayraç": "Divider",
    "Boşluk": "Spacer",
    "Bölüm bandı": "Section band",
    "Anahtar / değer": "Key / value",
    "Checkbox satırı": "Checkbox row",
    "Görsel": "Image",
    "Yeni bir özel şablon oluşturun veya belge aktarın.": "Create a custom template or import a document.",
    "Yeni fiş": "New receipt",
    "İçeriğinizi buraya yazın.": "Write your content here.",
    "Yeni metin": "New text",
    "Seç…": "Browse…",
    "Fotoğraf seç": "Choose photo",
    "Görseller (*.png *.jpg *.jpeg *.bmp *.webp)": "Images (*.png *.jpg *.jpeg *.bmp *.webp)",
    "Satır ekle": "Add row",
    "Seçili satırı sil": "Delete selected row",
    "Her satıra bir öğe": "One item per line",
    "Özel kağıt profili": "Custom paper profile",
    "Özel kağıt": "Custom paper",
    "Fiziksel genişlik": "Physical width",
    "Printable width": "Printable width",
    "Sol marj": "Left margin",
    "Sağ marj": "Right margin",
    "Üst marj": "Top margin",
    "Alt marj": "Bottom margin",
    "Negatif değer içeriği sola, pozitif değer sağa taşır.": "Negative moves content left; positive moves it right.",
    "Yatay ofset (- sola / + sağa)": "Horizontal offset (- left / + right)",
    "Uzunluk modu": "Length mode",
    "Sabit uzunluk": "Fixed length",
    "Eksik seçim": "Missing selection",
    "GC420t ve kağıt profili seçilmelidir.": "Select a GC420t and paper profile.",
    "GC420t, kağıt ve şablon seçilmelidir.": "Select a GC420t, paper profile, and template.",
    "GC420t gerekli": "GC420t required",
    "Önce Zebra GC420t kuyruğu bulunmalıdır.": "Locate the Zebra GC420t queue first.",
    "Kağıt profilini sil": "Delete paper profile",
    "Preset kaydet": "Save preset",
    "Preset adı": "Preset name",
    "Preset sil": "Delete preset",
    "Seçili preset silinsin mi?": "Delete the selected preset?",
    "Preset yazdırılamadı": "Preset could not be printed",
    "Yazıcı veya kağıt profili bulunamadı.": "Printer or paper profile not found.",
    "Geçersiz tarih": "Invalid date",
    "Tarihleri YYYY-AA-GG biçiminde girin.": "Enter dates in YYYY-MM-DD format.",
    "Geçersiz aralık": "Invalid range",
    "Başlangıç tarihi bitiş tarihinden sonra olamaz.": "The start date cannot be after the end date.",
    "Önizleme yok": "No preview",
    "Bu baskı işinin önizleme artefaktı bulunamadı.": "No preview artifact exists for this print job.",
    "Geçmiş kaydını sil": "Delete history record",
    "Kayıt ve ilişkili PNG/bitmap/ZPL artefaktları silinsin mi?": "Delete the record and its PNG/bitmap/ZPL artifacts?",
    "İş aktif": "Job active",
    "Gönderim devam eden iş silinmedi.": "The job being submitted was not deleted.",
    "Geçmiş boş": "History is empty",
    "Bu filtrelerle silinecek kayıt yok.": "There are no records to delete with these filters.",
    "Silinecek geçmiş kaydı yok.": "There are no history records to delete.",
    "Aktif işler korunuyor": "Active jobs are protected",
    "Todoist tokenı doğrulanıyor…": "Verifying Todoist token…",
    "Todoist bağlantısı doğrulandı": "Todoist connection verified",
    "Todoist bağlı — API v1": "Todoist connected — API v1",
    "Todoist senkronize ediliyor…": "Syncing Todoist…",
    "Kimlik doğrulama süresi doldu veya token geçersiz": "Authentication expired or the token is invalid",
    "İstek sınırına ulaşıldı": "Rate limit reached",
    "Çevrimdışı — uygun cache varsa ayrıca gösterilir": "Offline — an available cache is shown separately",
    "Todoist API hatası": "Todoist API error",
    "Editör yerleşimi varsayılana döndürüldü": "Editor layout reset",
    "Önizleme hazırlanıyor…": "Generating preview…",
    "Önizleme oluşturulamadı": "Preview could not be generated",
    "Önizleme oluşturulamadı.": "Preview could not be generated.",
    "Belge kuyruğa gönderiliyor…": "Submitting document to the queue…",
    "Beklenmeyen bir hata oluştu.": "An unexpected error occurred.",
    "İşlem tamamlanamadı": "Operation could not be completed",
    "Belge aktarılamadı": "Document could not be imported",
    "Belge": "Document",
    "Belgeler (*.pdf *.epub *.docx)": "Documents (*.pdf *.epub *.docx)",
    "ESKİ CACHE": "STALE CACHE",
    "Güncel": "Current",
    "aktif iş silinmedi.": "active job(s) were not deleted.",
    "Preset için Todoist senkronize ediliyor…": "Syncing Todoist for preset…",
    "Todoist sonucu alınamadı": "Todoist result could not be retrieved",
    "Preset için yalnızca eski Todoist cache’i bulundu": "Only stale Todoist cache was available for the preset",
    "Eski Todoist cache’i": "Stale Todoist cache",
    "Preset kuyruğa gönderiliyor…": "Submitting preset to the queue…",
    "Geçmiş işi yeniden hazırlanıyor…": "Rebuilding history job…",
    "Kuyruk işi iptal edildi": "Queue job cancelled",
    "İş artık kuyrukta değil": "The job is no longer queued",
    "Kuyruk işi iptal ediliyor…": "Cancelling queue job…",
    "Eksik ad": "Missing name",
    "Özel şablon adı boş olamaz.": "The custom template name cannot be empty.",
    "Blok yok": "No blocks",
    "En az bir blok ekleyin.": "Add at least one block.",
    "Özel şablonu sil": "Delete custom template",
    "Bu özel şablon silinsin mi?": "Delete this custom template?",
    "Geçersiz kağıt profili": "Invalid paper profile",
    "Uygulama dili değiştirildi.": "Application language changed.",
    "ZebraWriter başlatılamadı": "ZebraWriter could not start",
    "Uygulama başlatılamadı. Ayrıntılar güvenli log dosyasına yazıldı.": "The application could not start. Details were written to the secure log file.",
    "ready": "Ready",
    "submitting": "Submitting",
    "submitted": "Submitted",
    "failed": "Failed",
    "cancelled": "Cancelled",
}

_EN_PREFIXES: tuple[tuple[str, str], ...] = (
    ("Sürüm: ", "Version: "),
    ("Hazır — ", "Ready — "),
    ("Önizleme hatası: ", "Preview error: "),
    ("Kaydedildi: ", "Saved: "),
)


def set_language(language: str) -> None:
    global _language
    _language = language if language in SUPPORTED_LANGUAGES else "tr"


def current_language() -> str:
    return _language


def _translate_en(source: str) -> str:
    translated = _EN.get(source, source)
    if translated == source:
        for source_prefix, translated_prefix in _EN_PREFIXES:
            if source.startswith(source_prefix):
                return translated_prefix + source[len(source_prefix):]
    return translated


def tr(source: str, **values: object) -> str:
    translated = _translate_en(source) if _language == "en" else source
    return translated.format(**values) if values else translated


def _translated_source(widget: QWidget, property_name: str, current: str) -> str:
    source = widget.property(property_name)
    if not isinstance(source, str) or current not in {source, _translate_en(source)}:
        source = current
        widget.setProperty(property_name, source)
    return source


def localize_widget_tree(root: QWidget) -> None:
    widgets = [root, *root.findChildren(QWidget)]
    item_source_role = int(Qt.UserRole) + 41
    header_source_role = int(Qt.UserRole) + 42

    for widget in widgets:
        title = widget.windowTitle()
        if title:
            source = _translated_source(widget, "i18n_window_title", title)
            widget.setWindowTitle(tr(source))
        tooltip = widget.toolTip()
        if tooltip:
            source = _translated_source(widget, "i18n_tooltip", tooltip)
            widget.setToolTip(tr(source))
        if isinstance(widget, QLabel):
            source = _translated_source(widget, "i18n_text", widget.text())
            widget.setText(tr(source))
        elif isinstance(widget, QAbstractButton):
            source = _translated_source(widget, "i18n_text", widget.text())
            widget.setText(tr(source))
        elif isinstance(widget, QGroupBox):
            source = _translated_source(widget, "i18n_title", widget.title())
            widget.setTitle(tr(source))
        if isinstance(widget, (QLineEdit, QPlainTextEdit)):
            placeholder = widget.placeholderText()
            if placeholder:
                source = _translated_source(widget, "i18n_placeholder", placeholder)
                widget.setPlaceholderText(tr(source))
        if isinstance(widget, QComboBox):
            for index in range(widget.count()):
                current = widget.itemText(index)
                source = widget.itemData(index, item_source_role)
                if not isinstance(source, str) or current not in {source, _translate_en(source)}:
                    source = current
                    widget.setItemData(index, source, item_source_role)
                widget.setItemText(index, tr(source))
        if isinstance(widget, QTabWidget):
            for index in range(widget.count()):
                page = widget.widget(index)
                current = widget.tabText(index)
                source = page.property("i18n_tab_text")
                if not isinstance(source, str) or current not in {source, _translate_en(source)}:
                    source = current
                    page.setProperty("i18n_tab_text", source)
                widget.setTabText(index, tr(source))
        if isinstance(widget, QTableWidget):
            for column in range(widget.columnCount()):
                item = widget.horizontalHeaderItem(column)
                if item is None:
                    continue
                current = item.text()
                source = item.data(header_source_role)
                if not isinstance(source, str) or current not in {source, _translate_en(source)}:
                    source = current
                    item.setData(header_source_role, source)
                item.setText(tr(source))
