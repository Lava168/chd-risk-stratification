#!/usr/bin/env bash
# Run the desktop app with the correct OpenMP runtime (libomp) for xgboost.
# macOS reads DYLD_* at process start, so it must be exported before launching.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -d ".venv/lib/libomp" ]; then
  DYLD_DEFAULT_PATHS="/usr/local/lib:/usr/lib"
  export DYLD_FALLBACK_LIBRARY_PATH="$PWD/.venv/lib/libomp:${DYLD_FALLBACK_LIBRARY_PATH:-$DYLD_DEFAULT_PATHS}"
fi

exec .venv/bin/python desktop.py "$@"
