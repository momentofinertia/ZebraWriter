from __future__ import annotations

from datetime import datetime
from typing import Any

from thermal_app.application.dto import TransportReceipt
from thermal_app.domain.errors import PrinterUnavailableError, PrinterWriteError
from thermal_app.domain.models import PrinterProfile

try:
    import win32print as _win32print
except ImportError:  # pragma: no cover - Windows dependency is injected in tests
    _win32print = None


class WindowsRawTransport:
    def __init__(self, api: Any | None = None) -> None:
        self._api = api if api is not None else _win32print

    def _require_api(self) -> Any:
        if self._api is None:
            raise PrinterUnavailableError("pywin32 kurulu olmadığı için yazıcıya erişilemiyor.")
        return self._api

    def is_available(self, printer: PrinterProfile) -> bool:
        api = self._require_api()
        handle = None
        try:
            handle = api.OpenPrinter(printer.spooler_name)
            return True
        except Exception:
            return False
        finally:
            if handle is not None:
                api.ClosePrinter(handle)

    def submit(
        self,
        printer: PrinterProfile,
        payload: bytes,
        document_name: str,
    ) -> TransportReceipt:
        api = self._require_api()
        handle = None
        document_started = False
        page_started = False
        job_id: int | None = None
        try:
            handle = api.OpenPrinter(printer.spooler_name)
            job_id = int(api.StartDocPrinter(handle, 1, (document_name, None, "RAW")))
            document_started = True
            api.StartPagePrinter(handle)
            page_started = True
            written = int(api.WritePrinter(handle, payload))
            if written != len(payload):
                raise PrinterWriteError(
                    f"Windows spooler payload’ın yalnızca {written}/{len(payload)} byte bölümünü kabul etti."
                )
            api.EndPagePrinter(handle)
            page_started = False
            api.EndDocPrinter(handle)
            document_started = False
            return TransportReceipt(
                transport_job_id=str(job_id),
                accepted_at=datetime.now().astimezone(),
                accepted_by_queue=True,
            )
        except PrinterWriteError:
            self._abort(api, handle, page_started, document_started)
            raise
        except Exception as exc:
            self._abort(api, handle, page_started, document_started)
            raise PrinterWriteError("RAW baskı işi Windows spooler’a gönderilemedi.") from exc
        finally:
            if handle is not None:
                api.ClosePrinter(handle)

    @staticmethod
    def _abort(api: Any, handle: Any, page_started: bool, document_started: bool) -> None:
        if handle is None:
            return
        try:
            if hasattr(api, "AbortPrinter"):
                api.AbortPrinter(handle)
                return
            if page_started:
                api.EndPagePrinter(handle)
            if document_started:
                api.EndDocPrinter(handle)
        except Exception:
            pass

    def cancel(self, printer: PrinterProfile, transport_job_id: str) -> bool:
        api = self._require_api()
        handle = None
        try:
            handle = api.OpenPrinter(printer.spooler_name)
            api.SetJob(handle, int(transport_job_id), 0, None, api.JOB_CONTROL_CANCEL)
            return True
        except Exception:
            return False
        finally:
            if handle is not None:
                api.ClosePrinter(handle)
