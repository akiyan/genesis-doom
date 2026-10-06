#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Source this file; local .env is trusted shell configuration.
GENESIS_REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -f "$GENESIS_REPO_ROOT/.env" ]; then
    set -a
    source "$GENESIS_REPO_ROOT/.env"
    set +a
fi
