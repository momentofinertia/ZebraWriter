from __future__ import annotations

from thermal_app.application.ports.storage import PaperProfileRepository
from thermal_app.domain.models import PaperProfile, PrinterProfile, validate_paper_for_printer


class PaperService:
    def __init__(self, repository: PaperProfileRepository) -> None:
        self._repository = repository

    def list_profiles(self) -> list[PaperProfile]:
        return self._repository.list_all()

    def save_profile(self, profile: PaperProfile, printer: PrinterProfile) -> None:
        validate_paper_for_printer(profile, printer)
        self._repository.save(profile)

    def delete_profile(self, profile_id: str) -> bool:
        if len(self._repository.list_all()) <= 1:
            raise ValueError("Son kağıt profili silinemez.")
        return self._repository.delete(profile_id)
