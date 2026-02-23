"""Standardized exception handling utilities - eliminates duplication across layers.

This module provides:
- Consistent exception translation between layers
- Standardized error context and messages
- Common exception handling patterns
- Logging integration for all exceptions
"""

import functools
import traceback
from typing import Any, Callable, Optional, TypeVar

from domain.base.exceptions import (
    ApplicationError,
    DomainException,
    InfrastructureError,
    ValidationError,
)
from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class ExceptionContext:
    """Context information for exception handling."""

    def __init__(
        self,
        operation: str,
        layer: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        additional_context: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize exception context.

        Args:
            operation: Operation being performed
            layer: Layer where exception occurred (domain/application/infrastructure)
            entity_type: Type of entity involved (optional)
            entity_id: ID of entity involved (optional)
            additional_context: Additional context information (optional)
        """
        self.operation = operation
        self.layer = layer
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.additional_context = additional_context or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert context to dictionary.

        Returns:
            Dictionary representation of context
        """
        context = {
            "operation": self.operation,
            "layer": self.layer,
        }

        if self.entity_type:
            context["entity_type"] = self.entity_type
        if self.entity_id:
            context["entity_id"] = self.entity_id
        if self.additional_context:
            context.update(self.additional_context)

        return context


class ExceptionTranslator:
    """Translates exceptions between layers with consistent patterns."""

    @staticmethod
    def to_infrastructure_error(
        exception: Exception,
        context: ExceptionContext,
        include_traceback: bool = False,
    ) -> InfrastructureError:
        """Translate any exception to InfrastructureError.

        Args:
            exception: Original exception
            context: Exception context
            include_traceback: Whether to include traceback in details

        Returns:
            InfrastructureError with context
        """
        message = f"{context.operation} failed: {exception!s}"

        details = context.to_dict()
        details["original_exception"] = type(exception).__name__

        if include_traceback:
            details["traceback"] = traceback.format_exc()

        return InfrastructureError(
            message=message,
            error_code=f"INFRA_{context.operation.upper()}_FAILED",
            details=details,
        )

    @staticmethod
    def to_application_error(
        exception: Exception,
        context: ExceptionContext,
        include_traceback: bool = False,
    ) -> ApplicationError:
        """Translate any exception to ApplicationError.

        Args:
            exception: Original exception
            context: Exception context
            include_traceback: Whether to include traceback in details

        Returns:
            ApplicationError with context
        """
        message = f"{context.operation} failed: {exception!s}"

        details = context.to_dict()
        details["original_exception"] = type(exception).__name__

        if include_traceback:
            details["traceback"] = traceback.format_exc()

        return ApplicationError(
            message=message,
            error_code=f"APP_{context.operation.upper()}_FAILED",
            details=details,
        )

    @staticmethod
    def preserve_domain_exception(
        exception: DomainException,
        context: ExceptionContext,
    ) -> DomainException:
        """Preserve domain exception while adding context.

        Args:
            exception: Domain exception to preserve
            context: Additional context to add

        Returns:
            Original exception with enhanced context
        """
        # Add context to existing details
        exception.details.update(context.to_dict())
        return exception


class ExceptionHandler:
    """Centralized exception handling with consistent logging and translation."""

    @staticmethod
    def handle_with_logging(
        exception: Exception,
        context: ExceptionContext,
        log_level: str = "error",
    ) -> None:
        """Handle exception with consistent logging.

        Args:
            exception: Exception to handle
            context: Exception context
            log_level: Logging level (debug/info/warning/error)
        """
        log_message = f"{context.layer}.{context.operation} failed: {exception!s}"
        log_extra = context.to_dict()

        if log_level == "debug":
            logger.debug(log_message, extra=log_extra)
        elif log_level == "info":
            logger.info(log_message, extra=log_extra)
        elif log_level == "warning":
            logger.warning(log_message, extra=log_extra)
        else:
            logger.error(log_message, extra=log_extra, exc_info=True)

    @staticmethod
    def handle_and_translate(
        exception: Exception,
        context: ExceptionContext,
        target_layer: str = "infrastructure",
        log_level: str = "error",
    ) -> DomainException:
        """Handle exception with logging and translation.

        Args:
            exception: Exception to handle
            context: Exception context
            target_layer: Target layer for translation (infrastructure/application)
            log_level: Logging level

        Returns:
            Translated exception
        """
        # Log the exception
        ExceptionHandler.handle_with_logging(exception, context, log_level)

        # Preserve domain exceptions
        if isinstance(exception, DomainException):
            return ExceptionTranslator.preserve_domain_exception(exception, context)

        # Translate to target layer
        if target_layer == "infrastructure":
            return ExceptionTranslator.to_infrastructure_error(exception, context)
        else:
            return ExceptionTranslator.to_application_error(exception, context)


def handle_exceptions(
    operation: str,
    layer: str,
    entity_type: Optional[str] = None,
    log_level: str = "error",
    translate_to: str = "infrastructure",
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for consistent exception handling across layers.

    Args:
        operation: Operation being performed
        layer: Layer where operation occurs
        entity_type: Type of entity involved (optional)
        log_level: Logging level for exceptions
        translate_to: Target layer for exception translation

    Returns:
        Decorator function
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # Extract entity_id if available
            entity_id = None
            if args and hasattr(args[0], "id"):
                entity_id = str(args[0].id)
            elif "entity_id" in kwargs:
                entity_id = str(kwargs["entity_id"])

            context = ExceptionContext(
                operation=operation,
                layer=layer,
                entity_type=entity_type,
                entity_id=entity_id,
            )

            try:
                return func(*args, **kwargs)
            except DomainException:
                # Re-raise domain exceptions without translation
                raise
            except Exception as e:
                # Handle and translate other exceptions
                translated = ExceptionHandler.handle_and_translate(
                    e, context, translate_to, log_level
                )
                raise translated from e

        return wrapper

    return decorator


def handle_repository_exceptions(
    operation: str,
    entity_type: str,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for repository exception handling.

    Args:
        operation: Repository operation (save/find/delete)
        entity_type: Type of entity

    Returns:
        Decorator function
    """
    return handle_exceptions(
        operation=f"repository_{operation}",
        layer="infrastructure",
        entity_type=entity_type,
        log_level="error",
        translate_to="infrastructure",
    )


def handle_service_exceptions(
    operation: str,
    entity_type: Optional[str] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for service exception handling.

    Args:
        operation: Service operation
        entity_type: Type of entity (optional)

    Returns:
        Decorator function
    """
    return handle_exceptions(
        operation=f"service_{operation}",
        layer="application",
        entity_type=entity_type,
        log_level="error",
        translate_to="application",
    )


def handle_domain_exceptions(
    operation: str,
    entity_type: str,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for domain exception handling.

    Args:
        operation: Domain operation
        entity_type: Type of entity

    Returns:
        Decorator function
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return func(*args, **kwargs)
            except DomainException:
                # Re-raise domain exceptions as-is
                raise
            except Exception as e:
                # Log unexpected exceptions in domain layer
                logger.error(
                    "Unexpected exception in domain.%s.%s: %s",
                    entity_type,
                    operation,
                    str(e),
                    exc_info=True,
                )
                raise

        return wrapper

    return decorator


class ValidationExceptionBuilder:
    """Builder for creating consistent validation exceptions."""

    def __init__(self, entity_type: str) -> None:
        """Initialize validation exception builder.

        Args:
            entity_type: Type of entity being validated
        """
        self.entity_type = entity_type
        self.errors: list[str] = []

    def add_error(self, field: str, message: str) -> "ValidationExceptionBuilder":
        """Add validation error.

        Args:
            field: Field that failed validation
            message: Error message

        Returns:
            Self for chaining
        """
        self.errors.append(f"{field}: {message}")
        return self

    def build(self) -> ValidationError:
        """Build validation exception.

        Returns:
            ValidationError with all accumulated errors
        """
        if not self.errors:
            raise ValueError("No validation errors added")

        message = f"{self.entity_type} validation failed: {'; '.join(self.errors)}"
        return ValidationError(
            message=message,
            error_code=f"{self.entity_type.upper()}_VALIDATION_FAILED",
            details={"errors": self.errors, "entity_type": self.entity_type},
        )

    def has_errors(self) -> bool:
        """Check if any errors have been added.

        Returns:
            True if errors exist, False otherwise
        """
        return len(self.errors) > 0
