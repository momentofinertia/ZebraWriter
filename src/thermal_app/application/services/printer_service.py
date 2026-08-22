from __future__ import annotations

from thermal_app.application.ports.printing import PrinterDiscovery
from thermal_app.application.ports.storage import PrinterProfileRepository
from thermal_app.domain.models import PrinterProfile


class PrinterService:
    def __init__(self, discovery: PrinterDiscovery, repository: PrinterProfileRepository) -> None:
        self._discovery = discovery
        self._repository = repository

    def discover_gc420t(self) -> list[PrinterProfile]:
        profiles = self._discovery.discover()
        for profile in profiles:
            self._repository.save(profile)
        return profiles
