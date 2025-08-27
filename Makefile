# Makefile for Open Host Factory Plugin
# Main entry point - includes modular makefiles

.PHONY: help install install-pip dev-install dev-install-pip test test-unit test-integration test-e2e test-all test-cov test-html test-parallel test-quick test-performance test-aws test-report test-install test-completions lint lint-optional format format-fix format-container security security-quick security-all security-with-container ci-security-container security-full security-scan security-validate-sarif security-report sbom-generate clean clean-all clean-requirements clean-whitespace build build-test build-historical docs docs-build docs-serve docs-deploy docs-clean docs-deploy-version docs-list-versions docs-delete-version ci-docs-build ci-docs-build-for-pages ci-docs-deploy run run-dev version-show generate-pyproject ci-quality ci-quality-full ci-quality-mypy ci-quality-radon ci-quality-ruff ci-quality-ruff-optional ci-security ci-security-bandit ci-security-codeql ci-security-container ci-security-hadolint ci-security-safety ci-security-semgrep ci-security-trivy ci-security-trivy-fs ci-security-trufflehog ci-architecture ci-arch-clean ci-arch-cqrs ci-arch-file-sizes ci-arch-imports ci-imports ci-build-sbom ci-git-setup ci-install ci-tests-unit ci-tests-integration ci-tests-e2e ci-tests-matrix ci-tests-performance ci-check ci-check-quick ci-check-fix ci-check-verbose ci ci-quick workflow-ci workflow-test-matrix workflow-security architecture-check architecture-report quality-check quality-check-all quality-check-fix quality-check-files quality-gates quality-full generate-completions install-completions install-bash-completions install-zsh-completions uninstall-completions dev-setup install-package uninstall-package reinstall-package init-db create-config validate-config validate-all-files validate-all-workflows validate-shell-scripts validate-shellcheck validate-workflow-logic validate-workflow-syntax validate-workflows container-build container-build-single container-build-multi container-push-multi container-show-version container-health-check container-run docker-compose-up docker-compose-down quick-start dev status uv-lock uv-sync uv-sync-dev uv-check uv-benchmark file-sizes file-sizes-report detect-secrets hadolint-check install-dev-tools install-dev-tools-required install-dev-tools-dry-run dev-checks-container dev-checks-container-required hadolint-check-container pre-commit pre-commit-check pre-commit-check-required print-next-rc-version print-json-PYTHON_VERSIONS get-version show-package-info publish publish-test test-install deps-add deps-add-dev deps-update requirements-generate promote-alpha promote-beta promote-rc promote-stable release-patch release-minor release-major release-patch-alpha release-patch-beta release-patch-rc release-minor-alpha release-minor-beta release-minor-rc release-major-alpha release-major-beta release-major-rc release-version release-backfill release-historical local-ci local-clean local-dry-run local-list local-pr local-push local-release local-security local-test-matrix

# Include modular makefiles
include makefiles/common.mk
include makefiles/dev.mk
include makefiles/quality.mk
include makefiles/ci.mk
include makefiles/deploy.mk

# Generate pyproject.toml from template with project configuration
generate-pyproject:  ## Generate pyproject.toml from template using project config
	@echo "Generating pyproject.toml from template using $(PROJECT_CONFIG)..."
	@./dev-tools/scripts/generate_pyproject.py --config $(PROJECT_CONFIG)

# Version management targets
version-show:  ## Show current version from project config
	@echo "Current version: $(VERSION)"

get-version:  ## Generate unified version (works for PyPI, Docker, Git)
	@if [ "$${IS_RELEASE:-false}" = "true" ]; then \
		echo "$(VERSION)"; \
	else \
		commit=$$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown'); \
		dev_int=$$(python3 -c "print(int('$${commit}'[:6], 16))"); \
		echo "$(VERSION).dev$${dev_int}"; \
	fi

# Cleanup targets
clean:  ## Clean up build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf $(COVERAGE_HTML)/
	rm -f $(COVERAGE_REPORT)
	rm -f test-results.xml
	rm -f bandit-report.json
	rm -f pyproject.toml
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true

clean-all: clean docs-clean  ## Clean everything including virtual environment
	rm -rf $(VENV)

# Configuration management targets
show-package-info:  ## Show current package and version metadata
	@echo "Package Information:"
	@echo "  Name: $(PACKAGE_NAME)"
	@echo "  Version: $(VERSION)"
	@echo "  CLI Command: $(PACKAGE_NAME_SHORT)"
	@echo "  Repository: $(REPO_ORG)/$(PACKAGE_NAME)"
	@echo "  Container Registry: $(CONTAINER_REGISTRY)"
	@echo "  Documentation: $(DOCS_URL)"

# Show project status
status:  ## Show project status and useful commands
	@echo "=== $(PACKAGE_NAME) v$(VERSION) Status ==="
	@echo ""
	@echo "Project Structure:"
	@echo "  Source code:     $(PACKAGE)/"
	@echo "  Tests:          $(TESTS)/"
	@echo "  Documentation:  $(DOCS_DIR)/"
	@echo "  Dev tools:      dev-tools/"
	@echo ""
	@echo "Package Information:"
	@echo "  Name:           $(PACKAGE_NAME)"
	@echo "  Version:        $(VERSION)"
	@echo "  CLI Command:    $(PACKAGE_NAME_SHORT)"
	@echo "  Repository:     $(REPO_ORG)/$(PACKAGE_NAME)"
	@echo ""
	@echo "Quick Commands:"
	@echo "  make dev-setup     - Set up development environment"
	@echo "  make test          - Run tests"
	@echo "  make docs          - Build documentation"
	@echo "  make docs-serve    - Start documentation server"
	@echo "  make dev           - Quick development workflow"
	@echo ""
	@echo "Documentation:"
	@echo "  Local docs:     make docs-serve (versioned)"
	@echo "  GitHub Pages:   $(DOCS_URL)"
	@echo "  Deploy docs:    make docs-deploy (local) or make ci-docs-deploy (CI)"
	@echo "  List versions:  make docs-list-versions"
	@echo "  Deploy version: make docs-deploy-version VERSION=1.0.0"
	@echo ""
	@echo "Release Management:"
	@echo "  Standard:       make release-patch|minor|major"
	@echo "  Pre-releases:   make release-patch-alpha|beta|rc"
	@echo "  Promotions:     make promote-alpha|beta|rc|stable"
	@echo "  Custom version: RELEASE_VERSION=1.2.3 make release-version"
	@echo "  Backfill:       RELEASE_VERSION=1.2.3 TO_COMMIT=abc make release-backfill"
	@echo "  Historical:     COMMIT=abc123 VERSION=0.0.1 make build-historical"
	@echo "  Dry run:        DRY_RUN=true make release-minor"
	@echo ""
	@echo "Environment Variables:"
	@echo "  RELEASE_VERSION  Override version (use with release-version/backfill)"
	@echo "  FROM_COMMIT      Start commit (optional, smart defaults)"
	@echo "  TO_COMMIT        End commit (optional, defaults to HEAD)"
	@echo "  DRY_RUN          Test mode without making changes"
	@echo ""
	@echo "Release Management:"
	@echo "  Standard releases:  make release-patch|minor|major"
	@echo "  Pre-releases:       make release-patch-alpha|beta|rc"
	@echo "  Promotions:         make promote-alpha|beta|rc|stable"
	@echo ""
	@echo "Container Management:"
	@echo "  Show info:      make container-show-version"
	@echo "  Build single:   make container-build-single PYTHON_VERSION=3.11"
	@echo "  Build all:      make container-build-multi"

# Print variable targets for CI integration
print-next-rc-version:  ## Calculate next RC version without making changes
	@DRY_RUN=true ./dev-tools/release/version_manager.sh bump minor rc | grep "New version:" | cut -d' ' -f3

print-%:
	@echo $($*)

# JSON print targets for GitHub Actions (handles both single values and lists)
print-json-PYTHON_VERSIONS:  ## Print Python versions as JSON for GitHub Actions
	@echo "$(PYTHON_VERSIONS)" | tr ' ' '\n' | jq -R . | jq -s . | jq -c .

print-json-%:
	@value="$($*)"; \
	if echo "$$value" | grep -q " "; then \
		echo "$$value" | tr ' ' '\n' | jq -R . | jq -s . | jq -c .; \
	else \
		echo "$$value" | jq -R . | jq -c .; \
	fi

help:  ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@awk 'BEGIN {FS = ":.*## "; section=""} \
		/^# @SECTION / {if(section && length(buffer)>0) {print buffer | "sort"; close("sort"); buffer=""} section=substr($$0,12); print "\n" section ":"} \
		/^[[:alnum:]_-]+:.*## / {if(section) buffer = buffer sprintf("  %-20s %s\n", $$1, $$2)} \
		END {if(section && length(buffer)>0) {print buffer | "sort"; close("sort")}}' $(MAKEFILE_LIST)
