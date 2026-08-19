#!/usr/bin/env bash
# Point git at the VERSIONED hooks, so they travel with the repo.
#
# .git/hooks is not versioned, so a hook installed by hand exists on one
# machine and nowhere else — which is how .pre-commit-config.yaml sat in
# this repo for months with no hook actually installed.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
git config core.hooksPath .githooks
echo "hooks active: $(git config core.hooksPath)"
ls -1 .githooks
