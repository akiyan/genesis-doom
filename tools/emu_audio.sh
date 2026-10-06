#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Usage: bash tools/emu_audio.sh rom.bin [out.wav] [record_seconds=12]
exec bash "$(dirname "$0")/emu_session.sh" audio "$1" "${2:-/tmp/gdoom_audio.wav}" 2 Return "${3:-12}"
