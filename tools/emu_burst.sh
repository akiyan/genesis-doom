#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Usage: bash tools/emu_burst.sh rom.bin [outdir] [count=44] [interval=0.5]
exec bash "$(dirname "$0")/emu_session.sh" burst "$1" "${2:-/tmp/burst}" 2 Return 6 "${3:-44}" "${4:-0.5}"
