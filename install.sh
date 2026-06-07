#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FLUSH_DIR="$HOME/.claude/flush"
HOOKS_DIR="$HOME/.claude/hooks"
SETTINGS="$HOME/.claude/settings.json"

echo "==> Installing flush..."

# 1. copy hook script
mkdir -p "$HOOKS_DIR"
cp "$SCRIPT_DIR/hooks/post_response.py" "$HOOKS_DIR/flush_post_response.py"
chmod +x "$HOOKS_DIR/flush_post_response.py"
echo "    hook installed: $HOOKS_DIR/flush_post_response.py"

# 2. copy scorer package and config
mkdir -p "$FLUSH_DIR"
cp -r "$SCRIPT_DIR/scorer/" "$FLUSH_DIR/scorer"
cp -r "$SCRIPT_DIR/config/"  "$FLUSH_DIR/config"
cp -r "$SCRIPT_DIR/server/"  "$FLUSH_DIR/server"
cp -r "$SCRIPT_DIR/ui/"      "$FLUSH_DIR/ui"
chmod +x "$FLUSH_DIR/ui/terminal_ui.py"
echo "    package installed: $FLUSH_DIR"

# 3. merge hook registration into claude settings
touch "$SETTINGS"
# ensure settings.json is at least an empty object
python3 - <<'EOF'
import json, sys, os
path = os.path.expanduser("~/.claude/settings.json")
try:
    with open(path) as f:
        json.load(f)
except (json.JSONDecodeError, FileNotFoundError):
    with open(path, "w") as f:
        f.write("{}\n")
EOF

python3 "$SCRIPT_DIR/install_helpers/merge_settings.py" "$SETTINGS" "$SCRIPT_DIR/settings.patch.json"
echo "    settings updated: $SETTINGS"

echo ""
echo "flush installed successfully."
echo ""
echo "Optional: open the terminal UI (in a separate terminal tab)"
echo "  python3 ~/.claude/flush/ui/terminal_ui.py"
