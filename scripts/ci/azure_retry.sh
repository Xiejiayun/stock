#!/usr/bin/env bash
set -euo pipefail

az_retry() {
  local attempt=1
  local max_attempts=3
  local delay_seconds=20

  while true; do
    if az "$@"; then
      return 0
    fi

    if [ "$attempt" -ge "$max_attempts" ]; then
      return 1
    fi

    echo "Azure CLI command failed on attempt ${attempt}; retrying in ${delay_seconds}s: az $*" >&2
    sleep "$delay_seconds"
    attempt=$((attempt + 1))
  done
}
