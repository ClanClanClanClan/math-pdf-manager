#!/bin/bash
# Restore script for backup created on 20250726_232945
echo "Restoring from backup..."
rm -rf "/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/Scripts"
cp -r "/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/Scripts_backup_20250726_232945" "/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/Scripts"
echo "✅ Restored successfully"
