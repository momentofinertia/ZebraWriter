from __future__ import annotations

from typing import Any

from thermal_app.domain.errors import PrinterDiscoveryError
from thermal_app.domain.models import PrinterProfile
from thermal_app.domain.profiles import gc420t_profile

try:
    import win32print as _win32print
except ImportError:  # pragma: no cover - Windows dependency is injected in tests
    _win32print = None


class WindowsPrinterDiscovery:
    def __init__(self, api: Any | None = None) -> None:
        self._api = api if api is not None else _win32print

    def discover(self) -> list[PrinterProfile]:
        if self._api is None:
            raise PrinterDiscoveryError("pywin32 kurulu olmadığı için Windows yazıcıları okunamadı.")
        flags = self._api.PRINTER_ENUM_LOCAL | self._api.PRINTER_ENUM_CONNECTIONS
        try:
            queues = self._api.EnumPrinters(flags, None, 2)
        except Exception as exc:
            raise PrinterDiscoveryError("Windows yazıcı kuyruğu okunamadı.") from exc

        profiles: list[PrinterProfile] = []
        for queue in queues:
            name = str(queue.get("pPrinterName") or "")
            driver = str(queue.get("pDriverName") or "")
            if "gc420t" not in f"{name} {driver}".casefold():
                continue
            profiles.append(
                gc420t_profile(
                    spooler_name=name,
                    driver_name=driver,
                    port_name=str(queue.get("pPortName") or ""),
                )
            )
        return profiles
