#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Compatibility entry point: run_emu.sh rom.bin [output_name]
exec bash "$(dirname "$0")/emu_shot.sh" "$1" "/tmp/${2:-shot}.png"
