# SPDX-License-Identifier: MIT
"""Read unquoted KEY=value entries shared with GNU Make and Bash."""
import os
from pathlib import Path
import re


def load_env():
    path = Path(__file__).resolve().parents[1] / '.env'
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            key, sep, value = line.partition('=')
            if not sep or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', key):
                raise ValueError(f'Invalid .env entry for {key!r}')
            os.environ.setdefault(key, value.split(' #', 1)[0].strip())
