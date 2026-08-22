from datetime import datetime

import pytest

from thermal_app.domain.errors import PrinterWriteError
from thermal_app.infrastructure.printers.windows_raw_transport import WindowsRawTransport


class FakeWin32Print:
    JOB_CONTROL_CANCEL = 3

    def __init__(self, partial: bool = False) -> None:
        self.partial = partial
        self.calls: list[object] = []

    def OpenPrinter(self, name: str) -> str:
        self.calls.append(("open", name))
        return "handle"

    def ClosePrinter(self, handle: str) -> None:
        self.calls.append(("close", handle))

    def StartDocPrinter(self, handle: str, level: int, info: tuple) -> int:
        self.calls.append(("start_doc", info))
        return 42

    def StartPagePrinter(self, handle: str) -> None:
        self.calls.append("start_page")

    def WritePrinter(self, handle: str, payload: bytes) -> int:
        self.calls.append(("write", payload))
        return len(payload) - 1 if self.partial else len(payload)

    def EndPagePrinter(self, handle: str) -> None:
        self.calls.append("end_page")

    def EndDocPrinter(self, handle: str) -> None:
        self.calls.append("end_doc")

    def AbortPrinter(self, handle: str) -> None:
        self.calls.append("abort")

    def SetJob(self, handle: str, job_id: int, level: int, info: object, command: int) -> None:
        self.calls.append(("cancel", job_id, command))


def test_raw_transport_returns_spooler_job_id(printer: object) -> None:
    api = FakeWin32Print()
    receipt = WindowsRawTransport(api).submit(printer, b"^XA^XZ", "Test")
    assert receipt.transport_job_id == "42"
    assert receipt.accepted_by_queue is True
    assert isinstance(receipt.accepted_at, datetime)
    assert "abort" not in api.calls


def test_partial_write_aborts_job(printer: object) -> None:
    api = FakeWin32Print(partial=True)
    with pytest.raises(PrinterWriteError, match="yalnızca"):
        WindowsRawTransport(api).submit(printer, b"^XA^XZ", "Test")
    assert "abort" in api.calls
