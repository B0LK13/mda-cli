#!/usr/bin/env bash
# Install mda-cli for zsh (WSL, macOS, Linux). Ensures `mda` is on PATH via ~/.local/bin.
# Usage: ./scripts/install-global.sh
#        MDA_CLI_ROOT=/path/to/mda-cli ./scripts/install-global.sh

set -euo pipefail

MARK_BEGIN="# >>> mda-cli >>>"
MARK_END="# <<< mda-cli <<<"

detect_environment() {
  ENV_KIND="unix"
  if grep -qi microsoft /proc/version 2>/dev/null; then
    ENV_KIND="wsl"
  elif [[ -n "${MSYSTEM:-}" ]]; then
    ENV_KIND="git-bash"
  elif [[ "$(uname -s 2>/dev/null || true)" == "Darwin" ]]; then
    ENV_KIND="macos"
  fi
}

find_python() {
  if [[ -n "${PYTHON:-}" ]] && command -v "$PYTHON" >/dev/null 2>&1; then
    echo "$PYTHON"
    return 0
  fi
  for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
      echo "$candidate"
      return 0
    fi
  done
  return 1
}

resolve_repo_root() {
  if [[ -n "${MDA_CLI_ROOT:-}" ]]; then
    cd "$MDA_CLI_ROOT"
    pwd -P 2>/dev/null || pwd
    return 0
  fi
  local script_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  cd "$script_dir/.."
  pwd -P 2>/dev/null || pwd
}

ensure_zsh_path() {
  local zshrc="${ZDOTDIR:-$HOME}/.zshrc"
  touch "$zshrc"

  if grep -qF "$MARK_BEGIN" "$zshrc" 2>/dev/null; then
    echo "mda-cli PATH block already present in $zshrc"
    return 0
  fi

  if grep -qE '(^|:)\$HOME/\.local/bin|~/.local/bin|\.local/bin' "$zshrc" 2>/dev/null; then
    echo "~/.local/bin already referenced in $zshrc (no block added)"
    return 0
  fi

  {
    echo ""
    echo "$MARK_BEGIN"
    echo '# Ensure pip user scripts (mda) are on PATH in zsh'
    echo 'export PATH="$HOME/.local/bin:$PATH"'
    echo "$MARK_END"
  } >>"$zshrc"
  echo "Appended mda-cli PATH block to $zshrc"
}

install_wrapper() {
  local bindir="$HOME/.local/bin"
  mkdir -p "$bindir"
  export PATH="$bindir:$PATH"
  if command -v mda >/dev/null 2>&1 && mda --version >/dev/null 2>&1; then
    echo "Console script mda already works; skipping wrapper copy"
    return 0
  fi
  local wrapper_src="$REPO_ROOT/scripts/mda"
  if [[ ! -f "$wrapper_src" ]]; then
    echo "Warning: wrapper not found at $wrapper_src" >&2
    return 0
  fi
  cp "$wrapper_src" "$bindir/mda"
  chmod +x "$bindir/mda"
  echo "Installed fallback wrapper: $bindir/mda"
}

main() {
  detect_environment
  echo "Environment: $ENV_KIND ($(uname -s 2>/dev/null || echo unknown))"

  PYTHON="$(find_python)" || {
    echo "Error: python3 not found. Install Python 3.10+ or set PYTHON=..." >&2
    exit 1
  }
  echo "Using Python: $PYTHON ($("$PYTHON" --version 2>&1))"

  REPO_ROOT="$(resolve_repo_root)"
  if [[ ! -f "$REPO_ROOT/pyproject.toml" ]]; then
    echo "Error: pyproject.toml not found under $REPO_ROOT" >&2
    exit 1
  fi
  echo "Installing from: $REPO_ROOT"

  install_editable() {
    if command -v pipx >/dev/null 2>&1; then
      echo "Installing with pipx (recommended on PEP 668 / Homebrew Python)..."
      pipx install -e "$REPO_ROOT" --force
      return 0
    fi
    if "$PYTHON" -m pip install --user -e "$REPO_ROOT" 2>/dev/null; then
      return 0
    fi
    echo "Retrying pip with --user --break-system-packages (externally-managed Python)..."
    "$PYTHON" -m pip install --user --break-system-packages -e "$REPO_ROOT"
  }

  "$PYTHON" -m pip install --upgrade pip >/dev/null 2>&1 || true
  install_editable

  USER_BASE="$("$PYTHON" -m site --user-base 2>/dev/null || echo "$HOME/.local")"
  SCRIPTS_DIR="$USER_BASE/bin"
  mkdir -p "$HOME/.local/bin"
  export PATH="$HOME/.local/bin:$PATH"

  export PATH="$HOME/.local/bin:$PATH"
  ensure_zsh_path
  install_wrapper

  echo ""
  echo "Verification (current shell PATH):"
  if command -v mda >/dev/null 2>&1; then
    mda --version
    mda --check || true
  elif [[ -x "$SCRIPTS_DIR/mda" ]]; then
    "$SCRIPTS_DIR/mda" --version
  elif [[ -x "$HOME/.local/bin/mda" ]]; then
    "$HOME/.local/bin/mda" --version
  else
    echo "mda not on PATH yet. Run: source ~/.zshrc  (or open a new zsh)"
    echo "Expected script dir: $SCRIPTS_DIR"
  fi

  echo ""
  echo "Done. Open a new zsh tab or: source ~/.zshrc"
  if [[ "$ENV_KIND" == "wsl" ]]; then
    echo "WSL repo path: $REPO_ROOT"
    echo "Windows path:  C:\\Users\\Admin\\Projects\\mda-cli"
  fi
}

main "$@"
