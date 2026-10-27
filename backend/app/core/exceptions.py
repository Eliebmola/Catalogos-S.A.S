"""Excepciones de negocio. Los servicios las lanzan; el manejador global las traduce a HTTP."""

from typing import Any


class AppException(Exception):
    status_code: int = 500
    error_type: str = "internal_error"
    default_message: str = "Ocurrió un error inesperado. Inténtalo de nuevo más tarde."

    def __init__(
        self,
        message: str | None = None,
        *,
        details: Any = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.details = details
        self.headers = headers
        super().__init__(self.message)


class AuthenticationException(AppException):
    status_code = 401
    error_type = "authentication_required"
    default_message = "Credenciales ausentes o inválidas."

    def __init__(self, message: str | None = None, **kwargs: Any) -> None:
        kwargs.setdefault("headers", {"WWW-Authenticate": "Bearer"})
        super().__init__(message, **kwargs)


class UnauthorizedActionException(AppException):
    status_code = 403
    error_type = "forbidden"
    default_message = "No tienes permiso para realizar esta acción."


class PrivacyConsentRequiredException(AppException):
    status_code = 403
    error_type = "privacy_consent_required"
    default_message = "Debes aceptar el aviso de privacidad vigente para continuar."


class ResourceNotFoundException(AppException):
    status_code = 404
    error_type = "resource_not_found"
    default_message = "El recurso solicitado no existe."


class ConflictException(AppException):
    status_code = 409
    error_type = "conflict"
    default_message = "El recurso ya existe o entra en conflicto con otro."


class BusinessRuleViolationException(AppException):
    status_code = 422
    error_type = "business_rule_violation"
    default_message = "La operación incumple una regla de negocio."


class ExternalServiceException(AppException):
    status_code = 502
    error_type = "external_service_error"
    default_message = "Un servicio externo no respondió correctamente."
