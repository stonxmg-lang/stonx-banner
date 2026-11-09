#!/usr/bin/env bash
# Removes the STONX banner: the ~/.bashrc hook, the settings and the program.
set -euo pipefail

DIR=${STONX_HOME:-$HOME/.stonx-banner}
CONFIG_DIR=${XDG_CONFIG_HOME:-$HOME/.config}/stonx
RC=$HOME/.bashrc

if [[ -f $RC ]]; then
    sed -i '/# stonx-banner$/d' "$RC"
fi
rm -rf "$CONFIG_DIR" "$DIR"
echo "STONX banner removed. Open a new session to get your old prompt back."
