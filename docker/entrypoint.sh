#!/usr/bin/env bash
set -euo pipefail

if [ ! -f "${FAVICONS_PATH}" ]; then
  echo "Downloading favicons.xml -> ${FAVICONS_PATH}"
  curl -fsSL "${FAVICONS_URL}" -o "${FAVICONS_PATH}"
fi

exec "$@"
