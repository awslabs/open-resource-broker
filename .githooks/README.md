# Git Hooks

Version-controlled git hooks for the Open Resource Broker project.

## Setup

After cloning the repository, run once:

```bash
./dev-tools/setup/install-hooks.sh
```

This configures git to use `.githooks/` instead of `.git/hooks/`.

## Hooks

### pre-commit
1. **Beads sync** - Flushes pending changes to JSONL
2. **Quality checks** - Runs `pre-commit run` (reads `.pre-commit-config.yaml`, skips manual-stage hooks)

### post-merge
- **Beads sync** - Imports updated JSONL after pull/merge

### pre-push
- **Beads validation** - Prevents pushing stale JSONL

### post-checkout
- **Beads sync** - Imports JSONL after branch checkout

### prepare-commit-msg
- **Beads forensics** - Adds agent identity trailers

## Adding Custom Hooks

Edit hooks in `.githooks/` and they'll be version controlled:

```bash
# .githooks/pre-commit
#!/bin/bash
set -e

bd hooks run pre-commit    # Beads integration
pre-commit run             # Project checks (reads .pre-commit-config.yaml)
# Add more checks here
```

## Manual Hook Execution

```bash
# Test a hook manually
.githooks/pre-commit

# Or via beads
bd hooks run pre-commit
```
