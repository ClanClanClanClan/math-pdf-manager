#!/bin/bash
# Install weekly library maintenance as a macOS launchd scheduled task.
#
# Runs every Sunday at 10:00 AM:
# - Checks if unpublished papers got published (via Crossref)
# - Finds aging working papers (>5 years old)
# - Detects duplicate papers
# - Generates HTML report + macOS notification
#
# Usage:
#   ./scripts/install_weekly_maintenance.sh          # install
#   ./scripts/install_weekly_maintenance.sh uninstall # remove
#   ./scripts/install_weekly_maintenance.sh run       # run now

set -euo pipefail

LABEL="com.mathpdf.maintenance"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
SCRIPTS_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${SCRIPTS_DIR}/.venv/bin/python3"
REPORT_DIR="$HOME/.mathpdf/reports"

if [ "${1:-}" = "uninstall" ]; then
    echo "Removing maintenance schedule..."
    launchctl bootout "gui/$(id -u)/${LABEL}" 2>/dev/null || true
    rm -f "$PLIST"
    echo "Weekly maintenance uninstalled."
    exit 0
fi

if [ "${1:-}" = "run" ]; then
    echo "Running maintenance now..."
    cd "${SCRIPTS_DIR}/src"
    PYTHONPATH="${SCRIPTS_DIR}/src" "$PYTHON" -m maintenance.weekly_report -v
    exit $?
fi

# Verify Python
if [ ! -x "$PYTHON" ]; then
    echo "Error: Python not found at $PYTHON"
    exit 1
fi

mkdir -p "$REPORT_DIR"

# Create the launchd plist — runs every Sunday at 10:00 AM
cat > "$PLIST" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>${PYTHON}</string>
        <string>-m</string>
        <string>maintenance.weekly_report</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${SCRIPTS_DIR}/src</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PYTHONPATH</key>
        <string>${SCRIPTS_DIR}/src</string>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:${SCRIPTS_DIR}/.venv/bin</string>
    </dict>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Weekday</key>
        <integer>0</integer>
        <key>Hour</key>
        <integer>10</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>${REPORT_DIR}/maintenance.stdout.log</string>
    <key>StandardErrorPath</key>
    <string>${REPORT_DIR}/maintenance.stderr.log</string>
</dict>
</plist>
EOF

echo "Installed plist: $PLIST"

launchctl bootout "gui/$(id -u)/${LABEL}" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"

echo ""
echo "Weekly maintenance installed!"
echo ""
echo "  Schedule: every Sunday at 10:00 AM"
echo "  Reports:  $REPORT_DIR/"
echo ""
echo "To run now:      $0 run"
echo "To uninstall:    $0 uninstall"
