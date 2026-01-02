# Container Build System Optimization Implementation Plan

## Overview
Optimize the container build/tag/push system to properly handle Python version variants with consistent multi-architecture support and proper tagging strategy.

## Current Issues Identified

### Critical Problems
- ❌ **Tag Inconsistency**: Each Python version builds separately with inconsistent tagging
- ❌ **Missing Multi-Arch Manifests**: Only default Python version gets proper multi-arch manifests
- ❌ **Broken Tag Logic**: Release vs main branch tagging is inconsistent
- ❌ **Resource Waste**: Duplicate security scans and inefficient matrix builds
- ❌ **User Confusion**: No clear primary tags (`latest`, `X.Y.Z`) pointing to recommended Python version

### Root Cause Analysis
- **Python version is primary differentiator** (not OS dependencies)
- **Matrix strategy conflicts** with multi-arch manifest creation
- **Tag creation logic scattered** across multiple workflow jobs
- **No centralized tagging strategy**

## Target Tag Structure

### Primary Tags (Recommended for Users)
```bash
orb:latest            # -> latest release + python3.13 + multi-arch
orb:0.2.3             # -> specific version + python3.13 + multi-arch
orb:1.0.0             # -> specific version + python3.13 + multi-arch
```

### Python Variant Tags (For Compatibility)
```bash
orb:python3.9         # -> latest release + python3.9 + multi-arch
orb:python3.10        # -> latest release + python3.10 + multi-arch
orb:python3.11        # -> latest release + python3.11 + multi-arch
orb:python3.12        # -> latest release + python3.12 + multi-arch
orb:python3.13        # -> latest release + python3.13 + multi-arch (same as latest)
```

### Precision Tags (Version + Python)
```bash
orb:0.2.3-python3.9   # -> specific version + specific python + multi-arch
orb:0.2.3-python3.13  # -> specific version + specific python + multi-arch
orb:1.0.0-python3.9   # -> specific version + specific python + multi-arch
```

### Development Tags
```bash
orb:main              # -> latest main branch + python3.13 + multi-arch
orb:dev               # -> development builds + python3.13 + multi-arch
```

## Implementation Plan

### Phase 1: Workflow Restructure ⏳
**Goal**: Fix the container build workflow structure

#### 1.1 Centralize Tag Calculation
- [ ] Create centralized tag calculation step
- [ ] Define tag strategy based on event type (release/main/PR)
- [ ] Calculate all required tags upfront

#### 1.2 Optimize Build Matrix
- [ ] Build per Python version with multi-arch in single step
- [ ] Remove architecture from matrix (handle in Docker buildx)
- [ ] Use `--platform linux/amd64,linux/arm64` for all builds

#### 1.3 Fix Container Push Logic
- [ ] Consolidate tag creation in single job
- [ ] Push all variants with proper tags
- [ ] Create intermediate tags for manifest creation

### Phase 2: Multi-Arch Manifest Creation ⏳
**Goal**: Proper multi-architecture manifest creation

#### 2.1 Create Manifests for All Tags
- [ ] Primary tags: `latest`, `X.Y.Z` → point to default Python multi-arch
- [ ] Python variant tags: `pythonX.Y` → point to specific Python multi-arch  
- [ ] Precision tags: `X.Y.Z-pythonA.B` → point to specific combo multi-arch

#### 2.2 Manifest Creation Strategy
```yaml
# For each Python version: already multi-arch from buildx
orb:0.2.3-python3.9   # -> built with --platform linux/amd64,linux/arm64

# Create alias manifests
orb:latest            # -> alias to orb:0.2.3-python3.13
orb:0.2.3             # -> alias to orb:0.2.3-python3.13  
orb:python3.9         # -> alias to orb:0.2.3-python3.9
```

### Phase 3: Security & Optimization ⏳
**Goal**: Optimize security scanning and resource usage

#### 3.1 Optimize Security Scanning
- [ ] Scan Dockerfile once (not per Python version)
- [ ] Scan representative images (default + oldest Python)
- [ ] Reduce security scan matrix

#### 3.2 Resource Optimization
- [ ] Remove duplicate work across matrix
- [ ] Optimize caching strategy
- [ ] Reduce build time

### Phase 4: Testing & Validation ⏳
**Goal**: Ensure all tags work correctly

#### 4.1 Tag Validation
- [ ] Test primary tags pull correct images
- [ ] Test multi-arch pulls work on both amd64/arm64
- [ ] Test Python variant tags work correctly

#### 4.2 Integration Testing
- [ ] Test container startup across all Python versions
- [ ] Test health checks work
- [ ] Test deployment scenarios

## Detailed Implementation

### New Workflow Structure

```yaml
jobs:
  get-config:
    # Get Python versions, default version, registry info
    
  container-build:
    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11, 3.12, 3.13]
    steps:
      - name: Build multi-arch image per Python version
        run: |
          docker buildx build \
            --platform linux/amd64,linux/arm64 \
            --build-arg PYTHON_VERSION=${{ matrix.python-version }} \
            --push \
            -t $REGISTRY/$IMAGE:$VERSION-python${{ matrix.python-version }} .

  container-manifest:
    needs: [container-build]
    steps:
      - name: Create primary tag manifests
        run: |
          # latest -> default Python
          docker buildx imagetools create \
            -t $REGISTRY/$IMAGE:latest \
            $REGISTRY/$IMAGE:$VERSION-python$DEFAULT_PYTHON
          
          # X.Y.Z -> default Python  
          docker buildx imagetools create \
            -t $REGISTRY/$IMAGE:$VERSION \
            $REGISTRY/$IMAGE:$VERSION-python$DEFAULT_PYTHON
          
          # pythonX.Y -> specific Python latest
          for py_ver in 3.9 3.10 3.11 3.12 3.13; do
            docker buildx imagetools create \
              -t $REGISTRY/$IMAGE:python$py_ver \
              $REGISTRY/$IMAGE:$VERSION-python$py_ver
          done

  container-security:
    strategy:
      matrix:
        include:
          - python-version: 3.13  # Default - full scan
          - python-version: 3.9   # Oldest - basic scan
    # Reduced security scanning matrix
```

### Tag Calculation Logic

```yaml
- name: Calculate all tags
  id: tags
  run: |
    VERSION="${{ needs.get-config.outputs.package-version }}"
    DEFAULT_PYTHON="${{ needs.get-config.outputs.default-python-version }}"
    
    if [[ "${{ github.event_name }}" == "release" ]]; then
      # Release tags
      PRIMARY_TAGS="latest,$VERSION"
      PYTHON_TAGS="python3.9,python3.10,python3.11,python3.12,python3.13"
      PRECISION_TAGS="$VERSION-python3.9,$VERSION-python3.10,$VERSION-python3.11,$VERSION-python3.12,$VERSION-python3.13"
    elif [[ "${{ github.ref }}" == "refs/heads/main" ]]; then
      # Main branch tags
      PRIMARY_TAGS="main,dev"
      PYTHON_TAGS=""
      PRECISION_TAGS=""
    fi
    
    echo "primary_tags=$PRIMARY_TAGS" >> $GITHUB_OUTPUT
    echo "python_tags=$PYTHON_TAGS" >> $GITHUB_OUTPUT
    echo "precision_tags=$PRECISION_TAGS" >> $GITHUB_OUTPUT
```

## Success Criteria

### User Experience
- [ ] `docker pull orb:latest` gets recommended version (latest + python3.13 + multi-arch)
- [ ] `docker pull orb:0.2.3` gets specific version with default Python
- [ ] `docker pull orb:python3.9` gets latest with specific Python version
- [ ] `docker pull orb:0.2.3-python3.11` gets exact version + Python combo
- [ ] All pulls work correctly on both amd64 and arm64

### Technical Validation  
- [ ] Multi-arch manifests exist for all primary tags
- [ ] No duplicate/conflicting tags
- [ ] Consistent tagging across release types
- [ ] Reduced CI resource usage
- [ ] Security scans cover representative images

### Operational
- [ ] Clear documentation for users on which tags to use
- [ ] Automated cleanup of old images works correctly
- [ ] Container registry storage optimized

## Progress Tracking

### Phase 1: Workflow Restructure
- [ ] **1.1 Centralize Tag Calculation** - Not Started
- [ ] **1.2 Optimize Build Matrix** - Not Started  
- [ ] **1.3 Fix Container Push Logic** - Not Started

### Phase 2: Multi-Arch Manifest Creation
- [ ] **2.1 Create Manifests for All Tags** - Not Started
- [ ] **2.2 Manifest Creation Strategy** - Not Started

### Phase 3: Security & Optimization
- [ ] **3.1 Optimize Security Scanning** - Not Started
- [ ] **3.2 Resource Optimization** - Not Started

### Phase 4: Testing & Validation
- [ ] **4.1 Tag Validation** - Not Started
- [ ] **4.2 Integration Testing** - Not Started

## Notes
- Focus on Python version as primary differentiator (not OS)
- Multi-arch is handled by Docker buildx, not application logic
- Default Python version (3.13) should be the primary recommendation
- Maintain backward compatibility during transition

---
**Created**: 2026-01-02  
**Status**: Planning Phase  
**Next Action**: Begin Phase 1.1 - Centralize Tag Calculation
