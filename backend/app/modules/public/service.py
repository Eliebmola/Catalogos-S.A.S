from datetime import date

from app.core.exceptions import ResourceNotFoundException
from app.modules.public.repository import PublicCatalogRepository
from app.modules.public.schemas import PublicCatalog


class PublicCatalogService:
    def __init__(self, repository: PublicCatalogRepository, today: date, grace_days: int) -> None:
        self._repository = repository
        self._today = today
        self._grace_days = grace_days

    async def get_catalog(self, slug: str) -> PublicCatalog:
        store = await self._repository.get_published_by_slug(slug, self._today, self._grace_days)
        if store is None:
            # Misma respuesta para "no existe" y "no publicada": no revela tiendas en borrador.
            raise ResourceNotFoundException("Catálogo no encontrado.")
        return PublicCatalog.model_validate(store)
from datetime import date

