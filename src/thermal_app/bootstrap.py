from __future__ import annotations

from dataclasses import dataclass

from thermal_app.application.services.paper_service import PaperService
from thermal_app.application.services.custom_template_service import CustomTemplateService
from thermal_app.application.services.document_import_service import DocumentImportService
from thermal_app.application.services.preset_service import PresetService
from thermal_app.application.services.print_service import PrintService
from thermal_app.application.services.printer_service import PrinterService
from thermal_app.application.services.settings_service import SettingsService
from thermal_app.application.services.todoist_service import TodoistService
from thermal_app.application.preset_catalog import built_in_example_presets
from thermal_app.application.template_catalog import TemplateCatalog, built_in_definitions, custom_definition
from thermal_app.config import AppPaths, project_root
from thermal_app.domain.profiles import default_paper_profiles
from thermal_app.infrastructure.artifacts.local_artifact_store import LocalArtifactStore
from thermal_app.infrastructure.credentials import SystemKeyringCredentialStore
from thermal_app.infrastructure.document_importers import (
    DocxDocumentImporter,
    EpubDocumentImporter,
    PdfDocumentImporter,
)
from thermal_app.infrastructure.encoders.zpl_gfa import ZplGfaEncoder
from thermal_app.infrastructure.printers.windows_discovery import WindowsPrinterDiscovery
from thermal_app.infrastructure.printers.windows_raw_transport import WindowsRawTransport
from thermal_app.infrastructure.storage.database import Database
from thermal_app.infrastructure.storage.repositories import (
    SqliteIntegrationProfileRepository,
    SqlitePaperProfileRepository,
    SqlitePresetRepository,
    SqlitePrinterProfileRepository,
    SqlitePrintJobRepository,
    SqliteSettingsRepository,
    SqliteTodoistCacheRepository,
    SqliteCustomTemplateRepository,
)
from thermal_app.infrastructure.todoist_client import TodoistApiV1Client
from thermal_app.rendering.pillow_document_renderer import PillowDocumentRenderer


@dataclass(frozen=True, slots=True)
class ApplicationContext:
    paths: AppPaths
    printer_service: PrinterService
    paper_service: PaperService
    print_service: PrintService
    template_catalog: TemplateCatalog
    preset_service: PresetService
    settings_service: SettingsService
    todoist_service: TodoistService
    custom_template_service: CustomTemplateService
    renderer: PillowDocumentRenderer
    document_import_service: DocumentImportService


def build_context(paths: AppPaths | None = None) -> ApplicationContext:
    paths = paths or AppPaths.default()
    paths.ensure()
    database = Database(paths.database)
    database.initialize()
    printer_repository = SqlitePrinterProfileRepository(database)
    paper_repository = SqlitePaperProfileRepository(database)
    job_repository = SqlitePrintJobRepository(database)
    integration_repository = SqliteIntegrationProfileRepository(database)
    todoist_cache_repository = SqliteTodoistCacheRepository(database)
    preset_repository = SqlitePresetRepository(database)
    custom_template_repository = SqliteCustomTemplateRepository(database)
    settings_repository = SqliteSettingsRepository(database)
    if not paper_repository.list_all():
        for profile in default_paper_profiles():
            paper_repository.save(profile)

    font_root = project_root() / "assets" / "fonts"
    renderer = PillowDocumentRenderer(font_root / "Vera.ttf", font_root / "VeraBd.ttf")
    template_catalog = TemplateCatalog(built_in_definitions())
    custom_template_service = CustomTemplateService(custom_template_repository)
    for custom in custom_template_service.list_all():
        template_catalog.register_custom(custom_definition(custom.id, custom.name, custom.category, list(custom.blocks)))
    preset_service = PresetService(preset_repository)
    preset_service.install_built_ins(built_in_example_presets(template_catalog))
    discovery = WindowsPrinterDiscovery()
    transport = WindowsRawTransport()
    artifacts = LocalArtifactStore(paths)
    return ApplicationContext(
        paths=paths,
        printer_service=PrinterService(discovery, printer_repository),
        paper_service=PaperService(paper_repository),
        print_service=PrintService(
            renderer,
            ZplGfaEncoder(),
            transport,
            artifacts,
            printer_repository,
            paper_repository,
            job_repository,
            template_catalog,
        ),
        template_catalog=template_catalog,
        preset_service=preset_service,
        settings_service=SettingsService(settings_repository),
        todoist_service=TodoistService(
            TodoistApiV1Client(),
            SystemKeyringCredentialStore(),
            integration_repository,
            todoist_cache_repository,
        ),
        custom_template_service=custom_template_service,
        renderer=renderer,
        document_import_service=DocumentImportService({
            "pdf": PdfDocumentImporter(),
            "epub": EpubDocumentImporter(),
            "docx": DocxDocumentImporter(),
        }),
    )
