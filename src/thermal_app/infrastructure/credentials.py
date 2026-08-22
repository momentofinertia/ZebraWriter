from __future__ import annotations

from thermal_app.domain.errors import CredentialStoreError


class SystemKeyringCredentialStore:
    def __init__(self, service_name: str = "ZebraWriter") -> None:
        self._service_name = service_name

    @staticmethod
    def _keyring():
        try:
            import keyring
        except ImportError as exc:
            raise CredentialStoreError("Güvenli kimlik bilgisi deposu kurulmamış.") from exc
        return keyring

    def save(self, reference: str, secret: str) -> None:
        if not secret.strip():
            raise CredentialStoreError("Todoist tokenı boş olamaz.")
        try:
            self._keyring().set_password(self._service_name, reference, secret)
        except Exception as exc:
            raise CredentialStoreError("Token Windows güvenli deposuna kaydedilemedi.") from exc

    def get(self, reference: str) -> str | None:
        try:
            return self._keyring().get_password(self._service_name, reference)
        except Exception as exc:
            raise CredentialStoreError("Token Windows güvenli deposundan okunamadı.") from exc

    def delete(self, reference: str) -> None:
        try:
            keyring = self._keyring()
            if keyring.get_password(self._service_name, reference) is not None:
                keyring.delete_password(self._service_name, reference)
        except Exception as exc:
            raise CredentialStoreError("Token Windows güvenli deposundan silinemedi.") from exc
