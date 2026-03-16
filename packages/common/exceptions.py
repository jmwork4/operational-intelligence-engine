class OIEBaseException(Exception):
    def __init__(self, message: str = "", code: str | None = None):
        self.message = message
        self.code = code
        super().__init__(self.message)


class TenantNotFoundError(OIEBaseException):
    def __init__(self, tenant_id: str | None = None):
        super().__init__(
            message=f"Tenant not found: {tenant_id}" if tenant_id else "Tenant not found",
            code="TENANT_NOT_FOUND",
        )


class TenantAccessDeniedError(OIEBaseException):
    def __init__(self, message: str = "Access denied for this tenant"):
        super().__init__(message=message, code="TENANT_ACCESS_DENIED")


class ResourceNotFoundError(OIEBaseException):
    def __init__(self, resource_type: str = "Resource", resource_id: str | None = None):
        msg = f"{resource_type} not found"
        if resource_id:
            msg = f"{resource_type} not found: {resource_id}"
        super().__init__(message=msg, code="RESOURCE_NOT_FOUND")


class ValidationError(OIEBaseException):
    def __init__(self, message: str = "Validation error"):
        super().__init__(message=message, code="VALIDATION_ERROR")


class RateLimitExceededError(OIEBaseException):
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message=message, code="RATE_LIMIT_EXCEEDED")


class AIServiceError(OIEBaseException):
    def __init__(self, message: str = "AI service error"):
        super().__init__(message=message, code="AI_SERVICE_ERROR")


class PolicyViolationError(OIEBaseException):
    def __init__(self, message: str = "Policy violation detected", violation_type: str | None = None):
        self.violation_type = violation_type
        super().__init__(message=message, code="POLICY_VIOLATION")


class StorageError(OIEBaseException):
    def __init__(self, message: str = "Storage operation failed"):
        super().__init__(message=message, code="STORAGE_ERROR")
