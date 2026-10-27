from urllib.parse import quote
import logging

import httpx

from app.core.config import Settings
from app.core.exceptions import ExternalServiceException

logger = logging.getLogger(__name__)


class SupabaseStorage:
    def __init__(self, settings: Settings) -> None:
        if settings.supabase_service_role_key is None:
            raise ExternalServiceException(
                "No se pudo subir la imagen en este momento. Estamos revisando el servicio para solucionarlo pronto."
            )
        self._base = settings.supabase_base_url
        self._bucket = settings.supabase_storage_bucket
        self._key = settings.supabase_service_role_key.get_secret_value()

    def public_url(self, path: str) -> str:
        encoded = "/".join(quote(part, safe="") for part in path.split("/"))
        return f"{self._base}/storage/v1/object/public/{quote(self._bucket, safe='')}/{encoded}"

    def _headers(self, content_type: str | None = None) -> dict[str, str]:
        # Las nuevas secret keys de Supabase no son JWT: deben enviarse solo como apikey.
        # Las service_role legacy sí son JWT y también necesitan Authorization: Bearer.
        headers = {"apikey": self._key}
        if not self._key.startswith("sb_secret_"):
            headers["Authorization"] = f"Bearer {self._key}"
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    async def upload(self, path: str, content: bytes, content_type: str) -> str:
        encoded = "/".join(quote(part, safe="") for part in path.split("/"))
        url = f"{self._base}/storage/v1/object/{quote(self._bucket, safe='')}/{encoded}"
        headers = {**self._headers(content_type), "x-upsert": "false"}
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(url, content=content, headers=headers)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ExternalServiceException(
                "No se pudo subir la imagen en este momento. Estamos revisando el servicio para solucionarlo pronto."
            ) from exc
        return self.public_url(path)

    async def remove(self, path: str, *, best_effort: bool = False) -> None:
        url = f"{self._base}/storage/v1/object/{quote(self._bucket, safe='')}"
        headers = self._headers()
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.delete(url, json={"prefixes": [path]}, headers=headers)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return
            if best_effort:
                logger.warning("storage_object_delete_failed")
                return
            raise ExternalServiceException(
                "No se pudo quitar la imagen en este momento. Inténtalo de nuevo pronto."
            ) from exc
        except httpx.HTTPError as exc:
            if best_effort:
                logger.warning("storage_object_delete_failed")
                return
            raise ExternalServiceException(
                "No se pudo quitar la imagen en este momento. Inténtalo de nuevo pronto."
            ) from exc
