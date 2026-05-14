#!/usr/bin/env bash
# Install both launchd agents. Run from the project root:
#   bash deploy/launchd/install.sh

set -euo pipefail

# Resolve absolute path of project root (one level up from deploy/launchd/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LAUNCH_AGENTS="${HOME}/Library/LaunchAgents"

mkdir -p "${LAUNCH_AGENTS}"
mkdir -p "${HOME}/.mathpdf"

for plist in "${SCRIPT_DIR}"/ch.ethz.dpossamai.mathpdf.*.plist; do
    name="$(basename "$plist")"
    target="${LAUNCH_AGENTS}/${name}"

    echo "Installing ${name}…"
    sed \
        -e "s|PROJECT_PATH|${PROJECT_ROOT}|g" \
        -e "s|HOME|${HOME}|g" \
        "$plist" > "${target}"

    # Unload first in case it was already loaded
    launchctl unload "${target}" 2>/dev/null || true
    launchctl load "${target}"

    echo "  loaded: ${target}"
done

echo
echo "Done. Verify:"
echo "  launchctl list | grep mathpdf"
echo
echo "Logs:"
echo "  tail -f ~/.mathpdf/watcher.log"
echo "  tail -f ~/.mathpdf/weekly.stdout"
