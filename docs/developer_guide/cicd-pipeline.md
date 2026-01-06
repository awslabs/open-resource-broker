# CI/CD Pipeline Documentation

## Overview

The project uses a multi-stage CI/CD pipeline that ensures quality gates are met before publishing artifacts and creating releases.

## Pipeline Architecture

```
Push to main → Quality Gates → Development Artifacts → Release Decision → Production Artifacts
     ↓              ↓                    ↓                    ↓                ↓
  CI Quality    Dev Containers      Semantic Release    Prod Containers    GitHub Release
  CI Tests      Dev PyPI Publish    (if "release:")     Prod PyPI Publish  Release Assets
  Security      Dev Docs Deploy                         Prod Docs Deploy   SBOM Upload
```

## Workflow Descriptions

### Quality Gates (Always Run First)
- **`ci-quality.yml`** - Code linting, formatting, security scans
- **`ci-tests.yml`** - Unit and integration tests
- **`security-code.yml`** - CodeQL security analysis

### Development Artifacts (After Quality Success)
- **`dev-containers.yml`** - Build and push development containers
  - Tags: `main`, `dev`, `0.2.3.devXXXXX-pythonX.Y`
  - Registry: `ghcr.io/awslabs/open-resource-broker`
- **`dev-publish.yml`** - Publish to TestPyPI for testing
  - Target: `test.pypi.org`
  - Versions: `0.2.3.devXXXXX`
- **`docs.yml`** - Deploy development documentation

### Release Decision (After Dev Artifacts)
- **`semantic-release.yml`** - Calculate version and create GitHub release
  - Triggered by commits with "release:" prefix
  - Uses conventional commits for version calculation

### Production Pipeline (On Release Event)
- **`prod-release.yml`** - Build and publish all production artifacts
  - Production containers with `latest`, `X.Y.Z`, `pythonX.Y` tags
  - Publish to PyPI (production)
  - Deploy production documentation
  - Upload release assets (wheel, source, SBOM)

## How to Release

### 1. Development Workflow (Automatic)
Every push to `main` triggers:
1. Quality gates run first
2. If quality passes → development artifacts are built
3. TestPyPI gets new dev version for testing

### 2. Release Workflow (Manual)
To create a new release:

```bash
# Make your changes and commit with conventional commit messages
git commit -m "feat: add new feature"
git commit -m "fix: resolve bug"

# When ready to release, commit with "release:" prefix
git commit -m "release: version 1.2.0 with new features and bug fixes"
git push origin main
```

**What happens:**
1. Quality gates run
2. Development artifacts build
3. Semantic-release calculates version based on commits:
   - `fix:` → patch version (1.0.1)
   - `feat:` → minor version (1.1.0)  
   - `BREAKING CHANGE:` → major version (2.0.0)
4. GitHub release is created
5. Production pipeline builds all production artifacts

### 3. Manual Release (Emergency)
For emergency releases or specific versions:

```bash
# Trigger production pipeline directly
gh workflow run prod-release.yml -f version=1.0.1
```

## Artifact Locations

### Development Artifacts
- **Containers**: `ghcr.io/awslabs/open-resource-broker:main`
- **PyPI**: `test.pypi.org/project/open-resource-broker`
- **Docs**: GitHub Pages (development branch)

### Production Artifacts  
- **Containers**: `ghcr.io/awslabs/open-resource-broker:latest`
- **PyPI**: `pypi.org/project/open-resource-broker`
- **Docs**: GitHub Pages (production)
- **Assets**: GitHub Releases page

## Container Tags

### Development Tags
- `main` - Latest main branch build
- `dev` - Alias for main
- `0.2.3.devXXXXX-python3.12` - Specific dev version with Python version

### Production Tags
- `latest` - Latest production release
- `1.0.0` - Specific version
- `python3.12` - Latest release with specific Python version

## Troubleshooting

### Quality Gates Failing
If quality gates fail, no artifacts are built. Check:
- Linting errors in `ci-quality.yml`
- Test failures in `ci-tests.yml`
- Security issues in `security-code.yml`

### Development Artifacts Not Building
Check that quality gates passed successfully. Development artifacts only build after quality gates succeed.

### Release Not Created
Ensure your commit message contains "release:" prefix:
```bash
# ✅ Correct
git commit -m "release: add new feature"

# ❌ Incorrect  
git commit -m "feat: add new feature"
```

### Production Pipeline Not Triggered
Check that:
1. Semantic-release successfully created a GitHub release
2. The release is published (not draft)
3. Check `prod-release.yml` workflow runs

### Container Manifest Issues
If multi-arch manifests fail, check that all Python versions built successfully in the matrix job.

## Environment Variables

### Required Secrets
- `GH_APP_ID` - GitHub App ID for cross-workflow triggers
- `GH_APP_PRIVATE_KEY` - GitHub App private key

### PyPI Publishing
Uses OIDC trusted publishing (no tokens required):
- TestPyPI: Automatic for development
- PyPI: Automatic for production releases

## Monitoring

### Workflow Status
Monitor workflow runs in GitHub Actions:
- Quality gates should complete in ~5 minutes
- Development artifacts should complete in ~15 minutes  
- Production pipeline should complete in ~20 minutes

### Artifact Verification
- Check TestPyPI for development versions
- Check PyPI for production versions
- Verify container images in GitHub Container Registry
- Check GitHub Releases for assets
