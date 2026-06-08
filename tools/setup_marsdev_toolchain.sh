#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCK="$ROOT/toolchain/marsdev.lock"

usage() {
  cat <<'EOF'
Usage: tools/setup_marsdev_toolchain.sh [options]

Build and install the pinned Marsdev m68k-elf toolchain used by this repo.

Options:
  --src-dir DIR       Marsdev checkout/build directory
  --install-dir DIR   Install prefix expected by port/Makefile
  --jobs N            Bounded parallel make job count
  --no-build          Fetch/checkout/verify sources only
  -h, --help          Show this help

Environment overrides:
  MARSDEV_SRC_DIR
  MARSDEV_INSTALL_DIR
  MARSDEV_JOBS
EOF
}

lock_value() {
  awk -F= -v key="$1" '$1 == key { sub(/^[^=]*=/, ""); print; exit }' "$LOCK"
}

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "error: missing required command: $1" >&2
    exit 1
  fi
}

expand_path() {
  local value="$1"
  value="${value//\$HOME/$HOME}"
  if [[ "$value" != /* ]]; then
    value="$ROOT/$value"
  fi
  printf '%s\n' "$value"
}

REPO="$(lock_value MARSDEV_REPO)"
COMMIT="$(lock_value MARSDEV_COMMIT)"
GCC_VER="$(lock_value GCC_VER)"
BINUTILS_VER="$(lock_value BINUTILS_VER)"
NEWLIB_VER="$(lock_value NEWLIB_VER)"
LANGS="$(lock_value LANGS)"

SRC_DIR="$(expand_path "${MARSDEV_SRC_DIR:-$(lock_value SOURCE_DIR_DEFAULT)}")"
INSTALL_DIR="$(expand_path "${MARSDEV_INSTALL_DIR:-$(lock_value INSTALL_DIR_DEFAULT)}")"
JOBS="${MARSDEV_JOBS:-$(lock_value JOBS_DEFAULT)}"
DO_BUILD=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --src-dir)
      SRC_DIR="$(expand_path "$2")"
      shift 2
      ;;
    --install-dir)
      INSTALL_DIR="$(expand_path "$2")"
      shift 2
      ;;
    --jobs)
      JOBS="$2"
      shift 2
      ;;
    --no-build)
      DO_BUILD=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

case "$JOBS" in
  ''|*[!0-9]*)
    echo "error: --jobs must be a positive integer" >&2
    exit 1
    ;;
  0)
    echo "error: --jobs must be greater than zero" >&2
    exit 1
    ;;
esac

need_cmd git

mkdir -p "$(dirname "$SRC_DIR")" "$INSTALL_DIR"

if [[ ! -d "$SRC_DIR/.git" ]]; then
  git clone "$REPO" "$SRC_DIR"
else
  current_url="$(git -C "$SRC_DIR" config --get remote.origin.url || true)"
  if [[ "$current_url" != "$REPO" ]]; then
    echo "error: $SRC_DIR remote.origin.url is '$current_url', expected '$REPO'" >&2
    exit 1
  fi
fi

git -C "$SRC_DIR" fetch origin "$COMMIT"
git -C "$SRC_DIR" checkout --detach "$COMMIT"
git -C "$SRC_DIR" submodule sync -- m68k-gcc-toolchain
git -C "$SRC_DIR" submodule update --init -- m68k-gcc-toolchain

while read -r tag path sha; do
  [[ "$tag" == "SUBMODULE" ]] || continue
  actual="$(git -C "$SRC_DIR/$path" rev-parse HEAD)"
  if [[ "$actual" != "$sha" ]]; then
    echo "error: submodule $path is $actual, expected $sha" >&2
    exit 1
  fi
done < "$LOCK"

echo "Marsdev checkout: $SRC_DIR"
echo "Marsdev commit:   $(git -C "$SRC_DIR" rev-parse HEAD)"
echo "Install dir:      $INSTALL_DIR"
echo "GCC/Binutils/Newlib: $GCC_VER / $BINUTILS_VER / $NEWLIB_VER"

if [[ "$DO_BUILD" -eq 0 ]]; then
  echo "Source checkout verified; --no-build requested."
  exit 0
fi

need_cmd make
need_cmd makeinfo
need_cmd wget
need_cmd gcc
need_cmd g++

make -C "$SRC_DIR" m68k-toolchain-newlib \
  GCC_VER="$GCC_VER" \
  BINUTILS_VER="$BINUTILS_VER" \
  NEWLIB_VER="$NEWLIB_VER" \
  LANGS="$LANGS" \
  -j"$JOBS"

make -C "$SRC_DIR" install MARS_INSTALL_DIR="$INSTALL_DIR"

GCC="$INSTALL_DIR/m68k-elf/bin/m68k-elf-gcc"
AS="$INSTALL_DIR/m68k-elf/bin/m68k-elf-as"
gcc_version="$("$GCC" --version | sed -n '1p')"
as_version="$("$AS" --version | sed -n '1p')"
nosys_path="$("$GCC" -print-file-name=nosys.specs)"
libc_path="$("$GCC" -print-file-name=libc.a)"

case "$gcc_version" in
  *"$GCC_VER"*) ;;
  *)
    echo "error: installed compiler reports '$gcc_version', expected GCC $GCC_VER" >&2
    exit 1
    ;;
esac

case "$as_version" in
  *"$BINUTILS_VER"*) ;;
  *)
    echo "error: installed assembler reports '$as_version', expected Binutils $BINUTILS_VER" >&2
    exit 1
    ;;
esac

if [[ "$nosys_path" == "nosys.specs" || ! -f "$nosys_path" ]]; then
  echo "error: installed compiler cannot resolve nosys.specs" >&2
  exit 1
fi

if [[ "$libc_path" == "libc.a" || ! -f "$libc_path" ]]; then
  echo "error: installed compiler cannot resolve libc.a" >&2
  exit 1
fi

echo "$gcc_version"
echo "$as_version"
echo "$nosys_path"
echo "$libc_path"

echo "Marsdev m68k-elf toolchain is installed."
