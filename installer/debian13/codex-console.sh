#!/bin/sh
set -eu

service_user=vincent
service_home=/var/lib/vincent
service_runtime=/run/vincent

while :; do
    printf '\033c'
    echo 'VINCENT INTERACTIVE CODEX CONSOLE'
    echo '================================='
    echo
    echo 'Runs Codex as the locked vincent service account.'
    echo 'No root shell or local login account is exposed.'
    echo 'Alt+F1 returns to the Vincent status dashboard.'
    echo

    if ! getent passwd "$service_user" >/dev/null 2>&1; then
        echo 'Vincent service account is not available yet.'
        echo 'Waiting for bootstrap...'
        sleep 5
        continue
    fi
    install -d -o "$service_user" -g "$service_user" -m 0700 "$service_runtime"
    if [ ! -x /usr/local/bin/codex ]; then
        echo 'Codex is not installed yet.'
        echo 'Local READY does not require Codex. Optional provider provisioning is pending.'
        sleep 5
        continue
    fi

    echo 'Press Enter to launch Codex, or Alt+F1 to return to status.'
    IFS= read -r _
    printf '\033c'
    set +e
    runuser -u "$service_user" -- env \
        HOME="$service_home" \
        USER="$service_user" \
        LOGNAME="$service_user" \
        XDG_CONFIG_HOME="$service_home/.config" \
        XDG_CACHE_HOME="$service_home/.cache" \
        XDG_DATA_HOME="$service_home/.local/share" \
        XDG_RUNTIME_DIR="$service_runtime" \
        PATH=/usr/local/bin:/usr/bin:/bin \
        /usr/local/bin/codex
    rc=$?
    set -e
    echo
    echo "Codex exited with status $rc."
    echo 'Press Enter to relaunch, or Alt+F1 to return to status.'
    IFS= read -r _
done
