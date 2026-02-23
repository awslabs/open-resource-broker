"""Tests for exception handling utilities."""

import pytest

from domain.base.exceptions import (
    ApplicationError,
    InfrastructureError,
    ValidationError,
)
from infrastructure.utilities.exception_utils import (
    ExceptionContext,
    ExceptionHandler,
    ExceptionTranslator,
    ValidationExceptionBuilder,
    handle_exceptions,
    handle_repository_exceptions,
)


class TestExceptionContext:
    """Tests for ExceptionContext."""

    def test_basic_context(self):
        """Test creating basic exception context."""
        context = ExceptionContext(
            operation="save",
            layer="infrastructure",
        )
        assert context.operation == "save"
        assert context.layer == "infrastructure"
        assert context.entity_type is None
        assert context.entity_id is None

    def test_full_context(self):
        """Test creating full exception context."""
        context = ExceptionContext(
            operation="save",
            layer="infrastructure",
            entity_type="Template",
            entity_id="template-123",
            additional_context={"provider": "aws"},
        )
        assert context.entity_type == "Template"
        assert context.entity_id == "template-123"
        assert context.additional_context == {"provider": "aws"}

    def test_to_dict(self):
        """Test converting context to dictionary."""
        context = ExceptionContext(
            operation="save",
            layer="infrastructure",
            entity_type="Template",
            entity_id="template-123",
        )
        result = context.to_dict()
        assert result["operation"] == "save"
        assert result["layer"] == "infrastructure"
        assert result["entity_type"] == "Template"
        assert result["entity_id"] == "template-123"


class TestExceptionTranslator:
    """Tests for ExceptionTranslator."""

    def test_to_infrastructure_error(self):
        """Test translating to infrastructure error."""
        original = ValueError("Something went wrong")
        context = ExceptionContext(operation="save", layer="infrastructure")

        result = ExceptionTranslator.to_infrastructure_error(original, context)

        assert isinstance(result, InfrastructureError)
        assert "save failed" in result.message
        assert result.error_code == "INFRA_SAVE_FAILED"
        assert result.details["original_exception"] == "ValueError"

    def test_to_application_error(self):
        """Test translating to application error."""
        original = ValueError("Something went wrong")
        context = ExceptionContext(operation="process", layer="application")

        result = ExceptionTranslator.to_application_error(original, context)

        assert isinstance(result, ApplicationError)
        assert "process failed" in result.message
        assert result.error_code == "APP_PROCESS_FAILED"

    def test_preserve_domain_exception(self):
        """Test preserving domain exception with added context."""
        original = ValidationError("Invalid data")
        context = ExceptionContext(
            operation="validate",
            layer="domain",
            entity_type="Template",
        )

        result = ExceptionTranslator.preserve_domain_exception(original, context)

        assert result is original
        assert result.details["operation"] == "validate"
        assert result.details["entity_type"] == "Template"


class TestExceptionHandler:
    """Tests for ExceptionHandler."""

    def test_handle_and_translate_domain_exception(self):
        """Test that domain exceptions are preserved."""
        original = ValidationError("Invalid data")
        context = ExceptionContext(operation="validate", layer="domain")

        result = ExceptionHandler.handle_and_translate(
            original, context, target_layer="infrastructure"
        )

        assert isinstance(result, ValidationError)
        assert result is original

    def test_handle_and_translate_to_infrastructure(self):
        """Test translating to infrastructure error."""
        original = ValueError("Something went wrong")
        context = ExceptionContext(operation="save", layer="infrastructure")

        result = ExceptionHandler.handle_and_translate(
            original, context, target_layer="infrastructure"
        )

        assert isinstance(result, InfrastructureError)
        assert "save failed" in result.message

    def test_handle_and_translate_to_application(self):
        """Test translating to application error."""
        original = ValueError("Something went wrong")
        context = ExceptionContext(operation="process", layer="application")

        result = ExceptionHandler.handle_and_translate(
            original, context, target_layer="application"
        )

        assert isinstance(result, ApplicationError)
        assert "process failed" in result.message


class TestHandleExceptionsDecorator:
    """Tests for handle_exceptions decorator."""

    def test_decorator_success(self):
        """Test decorator with successful execution."""

        @handle_exceptions(operation="test", layer="infrastructure")
        def successful_function():
            return "success"

        result = successful_function()
        assert result == "success"

    def test_decorator_domain_exception(self):
        """Test decorator preserves domain exceptions."""

        @handle_exceptions(operation="test", layer="infrastructure")
        def raises_domain_exception():
            raise ValidationError("Invalid data")

        with pytest.raises(ValidationError) as exc_info:
            raises_domain_exception()
        assert "Invalid data" in str(exc_info.value)

    def test_decorator_translates_exception(self):
        """Test decorator translates non-domain exceptions."""

        @handle_exceptions(operation="test", layer="infrastructure", translate_to="infrastructure")
        def raises_value_error():
            raise ValueError("Something went wrong")

        with pytest.raises(InfrastructureError) as exc_info:
            raises_value_error()
        assert "test failed" in str(exc_info.value)


class TestHandleRepositoryExceptionsDecorator:
    """Tests for handle_repository_exceptions decorator."""

    def test_repository_decorator(self):
        """Test repository exception decorator."""

        @handle_repository_exceptions(operation="save", entity_type="Template")
        def save_template():
            raise ValueError("Save failed")

        with pytest.raises(InfrastructureError) as exc_info:
            save_template()
        assert "repository_save failed" in str(exc_info.value)


class TestValidationExceptionBuilder:
    """Tests for ValidationExceptionBuilder."""

    def test_add_single_error(self):
        """Test adding single validation error."""
        builder = ValidationExceptionBuilder("Template")
        builder.add_error("name", "Name is required")

        assert builder.has_errors()
        exception = builder.build()
        assert isinstance(exception, ValidationError)
        assert "name: Name is required" in exception.message

    def test_add_multiple_errors(self):
        """Test adding multiple validation errors."""
        builder = ValidationExceptionBuilder("Template")
        builder.add_error("name", "Name is required")
        builder.add_error("image_id", "Image ID is invalid")

        exception = builder.build()
        assert "name: Name is required" in exception.message
        assert "image_id: Image ID is invalid" in exception.message

    def test_chaining(self):
        """Test builder chaining."""
        builder = ValidationExceptionBuilder("Template")
        exception = (
            builder.add_error("name", "Name is required")
            .add_error("image_id", "Image ID is invalid")
            .build()
        )

        assert isinstance(exception, ValidationError)
        assert len(exception.details["errors"]) == 2

    def test_build_without_errors(self):
        """Test building without errors raises ValueError."""
        builder = ValidationExceptionBuilder("Template")

        with pytest.raises(ValueError) as exc_info:
            builder.build()
        assert "No validation errors" in str(exc_info.value)

    def test_has_errors(self):
        """Test has_errors method."""
        builder = ValidationExceptionBuilder("Template")
        assert not builder.has_errors()

        builder.add_error("name", "Name is required")
        assert builder.has_errors()
