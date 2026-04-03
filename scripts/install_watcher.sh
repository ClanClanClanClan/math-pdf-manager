#!/bin/bash
# Install the Math-PDF Watcher as a macOS launchd daemon.
#
# This creates a LaunchAgent that:
# - Starts automatically on login
# - Restarts on crash
# - Watches ~/Downloads/MathInbox/ for new PDFs
# - Logs to ~/.mathpdf/watcher.log
#
# Usage:
#   ./scripts/install_watcher.sh          # install and start
#   ./scripts/install_watcher.sh uninstall # stop and remove

set -euo pipefail

LABEL="com.mathpdf.watcher"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
SCRIPTS_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${SCRIPTS_DIR}/.venv/bin/python3"
INBOX="$HOME/Downloads/MathInbox"
LOG_DIR="$HOME/.mathpdf"

if [ "${1:-}" = "uninstall" ]; then
    echo "Stopping watcher..."
    launchctl bootout "gui/$(id -u)/${LABEL}" 2>/dev/null || true
    rm -f "$PLIST"
    echo "Watcher uninstalled."
    exit 0
fi

# Verify Python and venv
if [ ! -x "$PYTHON" ]; then
    echo "Error: Python not found at $PYTHON"
    echo "Run: python3.12 -m venv .venv && .venv/bin/pip install -e ."
    exit 1
fi

# Create inbox and log directories
mkdir -p "$INBOX" "$LOG_DIR"

# Create the launchd plist
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
        <string>watcher.daemon</string>
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
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${LOG_DIR}/watcher.stdout.log</string>
    <key>StandardErrorPath</key>
    <string>${LOG_DIR}/watcher.stderr.log</string>
    <key>ThrottleInterval</key>
    <integer>10</integer>
</dict>
</plist>
EOF

echo "Installed plist: $PLIST"

# Load the daemon
launchctl bootout "gui/$(id -u)/${LABEL}" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"

echo ""
echo "Math-PDF Watcher installed and started!"
echo ""
echo "  Inbox:   $INBOX"
echo "  Log:     $LOG_DIR/watcher.log"
echo "  Config:  ${SCRIPTS_DIR}/config/watcher.yaml"
echo ""
echo "Drop a PDF in $INBOX to test."
echo ""
echo "To uninstall: $0 uninstall"
