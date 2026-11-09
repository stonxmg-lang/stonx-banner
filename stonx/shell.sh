# STONX banner for Termux. Sourced from ~/.bashrc by the installer.
[[ $- == *i* ]] || return 0

STONX_HOME=${STONX_HOME:-$HOME/.stonx-banner}
STONX_CONFIG=${XDG_CONFIG_HOME:-$HOME/.config}/stonx/config

# ---------- settings ----------

__stonx_get() {  # __stonx_get KEY DEFAULT
    local k v
    if [[ -r $STONX_CONFIG ]]; then
        while IFS='=' read -r k v; do
            [[ $k == "$1" ]] && { printf '%s' "$v"; return; }
        done < "$STONX_CONFIG"
    fi
    printf '%s' "$2"
}

__stonx_set() {  # __stonx_set KEY VALUE
    local k v tmp
    mkdir -p "${STONX_CONFIG%/*}"
    tmp=$STONX_CONFIG.tmp
    : > "$tmp"
    if [[ -r $STONX_CONFIG ]]; then
        while IFS='=' read -r k v; do
            [[ $k && $k != "$1" ]] && printf '%s=%s\n' "$k" "$v" >> "$tmp"
        done < "$STONX_CONFIG"
    fi
    printf '%s=%s\n' "$1" "$2" >> "$tmp"
    mv "$tmp" "$STONX_CONFIG"
}

# ---------- prompt ----------

__stonx_prompt_set() {
    [[ $(__stonx_get PROMPT on) == on ]] || return 0
    local name; name=$(__stonx_get NAME STONX)
    name=${name//[^a-zA-Z0-9_.-]/}; name=${name,,}   # safe inside PS1
    [[ $name ]] || name=stonx
    # Two-line prompt: red frame, blue names, blue input text.
    PS1='\[\e[0;91m\]┌──(\[\e[1;94m\]'"$name"'㉿Termux\[\e[0;91m\])-[\[\e[1;94m\]\w\[\e[0;91m\]]\n\[\e[0;91m\]└─\[\e[1;94m\]\$\[\e[0;94m\] '
    PS0=$'\e[0m'   # back to normal colours for command output
}
__stonx_prompt_set

# ---------- live banner ----------

__stonx_pid=
__stonx_line=
__stonx_start() {
    [[ -t 1 ]] && command -v python3 >/dev/null || return
    [[ $(__stonx_get ENABLED on) == on ]] || return
    local rows cols height=9 r c h line layout=${STONX_CONFIG%/*}/.layout
    read -r rows cols < <(stty size 2>/dev/null)
    [[ $rows && $cols ]] || return
    # The banner corrects this itself if the remembered height does not match.
    if [[ -r $layout ]] && read -r r c h < "$layout" && [[ $r == "$rows" && $c == "$cols" ]]; then
        height=$h
    fi
    (( rows >= height + 4 )) || height=0
    line=${PS1@P}; line=${line%%$'\n'*}; line=${line//$'\001'/}; line=${line//$'\002'/}
    __stonx_line=$line
    printf '\e[0m\e[H\e[2J'
    (( height )) && printf '\n%.0s' $(seq 1 "$height")
    { PYTHONDONTWRITEBYTECODE=1 python3 -I -S "$STONX_HOME/stonx/banner.py" live "$$" "$line" "$height" </dev/null & __stonx_pid=$!; disown; } 2>/dev/null
    trap '__stonx_debug' DEBUG
}

__stonx_stop() {
    [[ $__stonx_pid ]] || return 0
    kill -TERM "$__stonx_pid" 2>/dev/null
    local i
    for ((i = 0; i < 100; i++)); do kill -0 "$__stonx_pid" 2>/dev/null || break; sleep 0.01; done
    printf '\e7\e[r\e8'
    __stonx_pid=
    trap - DEBUG
}

# The banner runs until the first real command, so it never draws over output.
__stonx_debug() {
    [[ $BASH_COMMAND == __stonx_prompt* || $__stonx_quiet ]] && return 0
    __stonx_stop
}

# Show it in a fresh Termux session, not in every nested shell. The installer
# leaves a one-time flag so the shell it opens shows the banner too.
__stonx_pending=
if (( SHLVL <= 1 )) || [[ -e $STONX_HOME/.show-once ]]; then
    __stonx_pending=1
    rm -f "$STONX_HOME/.show-once"
fi
__stonx_prompt() {
    [[ $__stonx_pending ]] || return 0
    __stonx_pending=
    __stonx_start
}
PROMPT_COMMAND="${PROMPT_COMMAND:+${PROMPT_COMMAND%;};}__stonx_prompt"

# "clear" wipes the screen, then the banner comes straight back on top.
clear() { command clear "$@"; __stonx_pending=1; }

# Ctrl+L does the same without losing what you are typing.
__stonx_redraw() {
    __stonx_stop
    __stonx_line=
    local __stonx_quiet=1   # its own commands must not stop the banner it starts
    __stonx_start
    [[ $__stonx_line ]] || { printf '\e[0m\e[H\e[2J'; __stonx_line=${PS1@P}; __stonx_line=${__stonx_line%%$'\n'*}; }
    __stonx_line=${__stonx_line//$'\001'/}; __stonx_line=${__stonx_line//$'\002'/}
    printf '%s\n' "$__stonx_line"
}
bind -x '"\C-l": __stonx_redraw' 2>/dev/null

# ---------- the stonx command ----------

stonx() {
    local themes="red blue green purple orange cyan pink gold"
    case $1 in
        "")
            __stonx_pending=1 ;;
        name)
            shift
            [[ $* ]] || { echo "usage: stonx name YOUR NAME"; return 1; }
            local name=$* bad
            # The block font has A-Z, 0-9, space and - . ! ? _ & @ #
            bad=${name//[A-Za-z0-9 .!?_&@#-]/}
            if [[ ${name//[^A-Za-z0-9]/} == "" ]]; then
                echo "stonx: use English letters or numbers, e.g. stonx name AHMED"
                return 1
            fi
            if [[ $bad ]]; then
                echo "stonx: these characters can't be drawn and will be skipped: $bad"
            fi
            __stonx_set NAME "$name"; __stonx_prompt_set; __stonx_pending=1 ;;
        tagline|tag)
            shift
            [[ $1 == off ]] && set -- ""
            __stonx_set TAGLINE "$*"; __stonx_pending=1 ;;
        theme|color|colour)
            if [[ " $themes " == *" $2 "* ]]; then
                __stonx_set THEME "$2"; __stonx_pending=1
            else
                echo "themes: $themes"; return 1
            fi ;;
        prompt)
            case $2 in
                on|off) __stonx_set PROMPT "$2"; echo "prompt $2 (open a new session to apply)" ;;
                *) echo "usage: stonx prompt on|off"; return 1 ;;
            esac ;;
        on)
            __stonx_set ENABLED on; __stonx_pending=1 ;;
        off)
            __stonx_set ENABLED off; echo "banner off. Turn it back on with: stonx on" ;;
        preview|print)
            python3 -I -S "$STONX_HOME/stonx/banner.py" print ;;
        update)
            git -C "$STONX_HOME" pull --ff-only && __stonx_pending=1 ;;
        version|-v|--version)
            echo "stonx-banner $(cat "$STONX_HOME/VERSION" 2>/dev/null || echo unknown)" ;;
        uninstall)
            bash "$STONX_HOME/uninstall.sh" ;;
        help|-h|--help)
            cat <<EOF
stonx                    show the banner again
stonx name AHMED         set the name in the banner
stonx tagline "TEXT"     set the grey line (stonx tagline off to hide it)
stonx theme blue         colours: $themes
stonx prompt on|off      use the STONX prompt or keep your own
stonx off | on           turn the banner off / on
stonx preview            print the banner once
stonx update             get the latest version
stonx version            show the installed version
stonx uninstall          remove everything
EOF
            ;;
        *)
            echo "unknown option: $1  (try: stonx help)"; return 1 ;;
    esac
}
