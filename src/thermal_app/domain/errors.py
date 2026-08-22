class ThermalAppError(Exception):
    """Base error safe to map to a user-facing message."""


class InvalidPaperProfileError(ThermalAppError):
    pass


class PrinterDiscoveryError(ThermalAppError):
    pass


class PrinterUnavailableError(ThermalAppError):
    pass


class PrinterWriteError(ThermalAppError):
    pass


class RenderingError(ThermalAppError):
    pass


class DocumentImportError(ThermalAppError):
    pass


class TemplateValidationError(ThermalAppError):
    pass


class StorageMigrationError(ThermalAppError):
    pass


class InvalidJobTransitionError(ThermalAppError):
    pass


class TodoistError(ThermalAppError):
    pass


class TodoistAuthError(TodoistError):
    pass


class TodoistRateLimitError(TodoistError):
    pass


class TodoistNetworkError(TodoistError):
    pass


class CredentialStoreError(ThermalAppError):
    pass
