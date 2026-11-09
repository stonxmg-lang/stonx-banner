#!/usr/bin/env bash
# STONX banner installer for Termux.
#
#   curl -fsSL https://raw.githubusercontent.com/stonxmg-lang/stonx-banner/main/install.sh | bash && exec bash
#
# Put your name in it straight away:
#
#   curl -fsSL https://raw.githubusercontent.com/stonxmg-lang/stonx-banner/main/install.sh | bash -s -- "YOUR NAME" && exec bash
set -euo pipefail

REPO=${STONX_REPO:-https://github.com/stonxmg-lang/stonx-banner.git}
DIR=${STONX_HOME:-$HOME/.stonx-banner}
CONFIG=${XDG_CONFIG_HOME:-$HOME/.config}/stonx/config
RC=$HOME/.bashrc
MARK="# stonx-banner"

red=$'\e[1;91m'; grey=$'\e[0;90m'; off=$'\e[0m'
say() { printf '%s==>%s %s\n' "$red" "$off" "$*"; }

if [[ -z ${PREFIX:-} || $PREFIX != */com.termux/* ]]; then
    say "This is made for Termux. Continuing anyway."
fi

need=()
command -v python3 >/dev/null || need+=(python)
command -v git >/dev/null || need+=(git)
if (( ${#need[@]} )); then
    say "Installing ${need[*]}"
    pkg install -y "${need[@]}" </dev/null
fi

if [[ -d $DIR/.git ]]; then
    say "Updating $DIR"
    git -C "$DIR" pull --ff-only --quiet
else
    say "Downloading to $DIR"
    rm -rf "$DIR"
    git clone --quiet --depth 1 "$REPO" "$DIR"
fi

mkdir -p "${CONFIG%/*}"
if [[ ${1:-} ]]; then
    tmp=$CONFIG.tmp; : > "$tmp"
    [[ -r $CONFIG ]] && grep -v '^NAME=' "$CONFIG" >> "$tmp" || true
    printf 'NAME=%s\n' "$*" >> "$tmp"
    mv "$tmp" "$CONFIG"
elif [[ ! -e $CONFIG ]]; then
    printf 'NAME=STONX\n' > "$CONFIG"
fi

# Hook into ~/.bashrc once. Older STONX setups are switched off, not deleted.
touch "$RC"
if grep -q '# stonx-interface' "$RC"; then
    sed -i 's|^\(.*# stonx-interface\)$|# \1 (replaced by stonx-banner)|' "$RC"
fi
if ! grep -qF "$MARK" "$RC"; then
    printf '\n[ -f "%s/stonx/shell.sh" ] && . "%s/stonx/shell.sh" %s\n' "$DIR" "$DIR" "$MARK" >> "$RC"
fi
touch "$DIR/.show-once"

echo
python3 -I -S "$DIR/stonx/banner.py" print || true
echo
say "Installed. Commands:"
printf '%s' "$grey"
cat <<'EOF'
  stonx name AHMED        change the name
  stonx tagline "TEXT"    change the grey line
  stonx theme blue        red blue green purple orange cyan pink gold
  stonx help              everything else
EOF
printf '%s' "$off"
say "Open a new session (or run: exec bash) to see it live."
