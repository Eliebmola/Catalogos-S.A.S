"""Autenticación: verificación local de JWT emitidos por Supabase Auth.

- Claves asimétricas (ES256/RS256): se valida con la clave pública del endpoint JWKS (sin secretos).
- Clave legacy HS256: se valida con SUPABASE_JWT_SECRET si está configurado.
El algoritmo se elige de una lista cerrada; jamás se confía ciegamente en el header del token."""

import logging
from dataclasses import dataclass
from typing import Annotated, Any
from uuid import UUID

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from app.core.config import Settings
from app.core.database import DbSession
from app.core.exceptions import AuthenticationException, PrivacyConsentRequiredException

logger = logging.getLogger(__name__)

_ASYMMETRIC_ALGORITHMS = frozenset({"ES256", "RS256"})


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    id: UUID
    email: str | None = None
    full_name: str | None = None


class SupabaseJWTVerifier:
    def __init__(self, settings: Settings) -> None:
        self._issuer = settings.jwt_issuer
        self._audience = settings.supabase_jwt_audience
        self._hs_secret = (
            settings.supabase_jwt_secret.get_secret_value() if settings.supabase_jwt_secret else None
        )
        # Cachea el JWKS 10 min; si llega un `kid` desconocido (rotación) se vuelve a consultar.
        self._jwks = PyJWKClient(settings.jwks_url, cache_jwk_set=True, lifespan=600, timeout=5)

    def verify(self, token: str) -> dict[str, Any]:
        try:
            algorithm = jwt.get_unverified_header(token).get("alg")
            if algorithm == "HS256" and self._hs_secret:
                key: Any = self._hs_secret
            elif algorithm in _ASYMMETRIC_ALGORITHMS:
                key = self._jwks.get_signing_key_from_jwt(token).key
            else:
                raise AuthenticationException("Token inválido.")
            return jwt.decode(
                token,
                key=key,
                algorithms=[algorithm],
                audience=self._audience,
                issuer=self._issuer,
                options={"require": ["exp", "sub", "aud", "iss"]},
                leeway=10,  # tolerancia a desfase de reloj
            )
        except jwt.PyJWTError as exc:
            logger.info("JWT rechazado: %s", type(exc).__name__)
            raise AuthenticationException("Token inválido o expirado.") from exc


_bearer_scheme = HTTPBearer(auto_error=False, description="JWT de Supabase Auth")


def get_jwt_verifier(request: Request) -> SupabaseJWTVerifier:
    return request.app.state.jwt_verifier


# `def` (no `async def`) a propósito: PyJWKClient hace I/O bloqueante al refrescar el JWKS y
# FastAPI ejecuta las dependencias síncronas en un threadpool, sin bloquear el event loop.
def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    verifier: Annotated[SupabaseJWTVerifier, Depends(get_jwt_verifier)],
) -> AuthenticatedUser:
    if credentials is None:
        raise AuthenticationException("Se requiere autenticación.")

    claims = verifier.verify(credentials.credentials)

    if claims.get("role") != "authenticated" or claims.get("is_anonymous"):
        raise AuthenticationException("Se requiere una cuenta registrada.")
    try:
        user_id = UUID(str(claims["sub"]))
    except ValueError as exc:
        raise AuthenticationException("Token inválido.") from exc

    metadata = claims.get("user_metadata")
    metadata_name = metadata.get("full_name") if isinstance(metadata, dict) else None
    full_name = metadata_name or claims.get("name")
    if isinstance(full_name, str):
        full_name = full_name.strip()[:120] or None
    else:
        full_name = None
    return AuthenticatedUser(id=user_id, email=claims.get("email"), full_name=full_name)


VerifiedUser = Annotated[AuthenticatedUser, Depends(get_current_user)]


async def require_privacy_consent(
    user: VerifiedUser, request: Request, session: DbSession
) -> AuthenticatedUser:
    """Bloquea los endpoints privados si la cuenta no aceptó la versión vigente."""
    from sqlalchemy import select

    from app.modules.privacy.models import PrivacyConsent

    consent = await session.scalar(
        select(PrivacyConsent.accepted_at).where(
            PrivacyConsent.user_id == user.id,
            PrivacyConsent.policy_version == request.app.state.settings.privacy_policy_version,
        )
    )
    if consent is None:
        raise PrivacyConsentRequiredException()
    return user


CurrentUser = Annotated[AuthenticatedUser, Depends(require_privacy_consent)]


def require_admin(user: CurrentUser, request: Request) -> AuthenticatedUser:
    """El panel de administración se asigna por allowlist de correos verificados en el backend."""
    settings: Settings = request.app.state.settings
    if not user.email or user.email.strip().lower() not in settings.admin_emails:
        from app.core.exceptions import UnauthorizedActionException

        raise UnauthorizedActionException("No tienes permisos de administrador.")
    return user


AdminUser = Annotated[AuthenticatedUser, Depends(require_admin)]
