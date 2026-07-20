#!/usr/bin/env bash
# Fast-forward the configured release branch and run the guarded deploy.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
BRANCH="${DEPLOY_BRANCH:-main}"

[[ -z "$(git status --porcelain)" ]] || {
  echo "ERROR: the VPS checkout has local changes; refusing to overwrite them" >&2
  exit 1
}
CURRENT_BRANCH="$(git branch --show-current)"
[[ "$CURRENT_BRANCH" == "$BRANCH" ]] || {
  echo "ERROR: checkout is on $CURRENT_BRANCH; expected $BRANCH" >&2
  exit 1
}

mkdir -p .deploy
git rev-parse HEAD > .deploy/previous-git-sha
git fetch origin "$BRANCH"
git merge --ff-only "origin/$BRANCH"
./scripts/deploy.sh
