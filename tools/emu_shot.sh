#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Usage: bash tools/emu_shot.sh rom.bin [out.png] [wait=8] [keys=Return] [load_wait=6]
exec bash "$(dirname "$0")/emu_session.sh" shot "$1" "${2:-/tmp/emu_shot.png}" "${3:-8}" "${4-Return}" "${5:-6}"
