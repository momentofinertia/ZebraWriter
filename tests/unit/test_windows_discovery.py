from thermal_app.infrastructure.printers.windows_discovery import WindowsPrinterDiscovery


class FakeWin32Print:
    PRINTER_ENUM_LOCAL = 2
    PRINTER_ENUM_CONNECTIONS = 4

    def EnumPrinters(self, flags: int, name: object, level: int) -> list[dict[str, object]]:
        assert flags == 6
        assert name is None
        assert level == 2
        return [
            {
                "pPrinterName": "Microsoft Print to PDF",
                "pDriverName": "Microsoft Print To PDF",
                "pPortName": "PORTPROMPT:",
            },
            {
                "pPrinterName": "ZDesigner GC420t",
                "pDriverName": "ZDesigner GC420t",
                "pPortName": "USB003",
            },
        ]


def test_discovery_returns_only_gc420t() -> None:
    profiles = WindowsPrinterDiscovery(FakeWin32Print()).discover()
    assert len(profiles) == 1
    assert profiles[0].spooler_name == "ZDesigner GC420t"
    assert profiles[0].port_name == "USB003"
