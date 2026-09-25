#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo "installer must run as root" >&2
    exit 1
fi

source_root=${1:-}
if [ -z "$source_root" ] || [ ! -f "$source_root/pyproject.toml" ]; then
    echo "usage: install.sh /absolute/path/to/verified/platform-checkout" >&2
    exit 2
fi
case "$source_root" in
    /*) ;;
    *) echo "source checkout path must be absolute" >&2; exit 2 ;;
esac

service_user=vincent
install_root=/opt/mission-control
configuration_root=/etc/mission-control
state_root=/var/lib/vincent
workspace_root=/srv/codex
resume_identity=${VINCENT_RESUME_IDENTITY:-0}

if ! getent passwd "$service_user" >/dev/null; then
    useradd --system --home-dir "$state_root" --shell /usr/sbin/nologin "$service_user"
fi

install -d -o root -g root -m 0755 "$install_root"
install -d -o root -g "$service_user" -m 0750 "$configuration_root"
install -d -o "$service_user" -g "$service_user" -m 0700 \
    "$state_root" "$state_root/identity" "$state_root/.config" "$state_root/.cache" "$state_root/.local" "$state_root/.local/share" "$state_root/.local/bin"
install -d -o "$service_user" -g "$service_user" -m 0750 "$workspace_root" "$workspace_root/worktrees"

python3 -m venv --system-site-packages "$install_root/venv"
"$install_root/venv/bin/python" -c 'import setuptools.build_meta'
"$install_root/venv/bin/python" -m pip install --no-deps --no-build-isolation --no-index "$source_root"
ln -sfn "$install_root/venv/bin/vincent" /usr/local/bin/vincent

if [ ! -f "$configuration_root/worker.toml" ]; then
    install -o root -g "$service_user" -m 0640 \
        "$source_root/config/worker.example.toml" "$configuration_root/worker.toml"
fi

install -o root -g root -m 0644 \
    "$source_root/installer/systemd/vincent-container-namespace.service" \
    /etc/systemd/system/vincent-container-namespace.service
install -o root -g root -m 0644 \
    "$source_root/installer/systemd/mission-control-worker.service" \
    /etc/systemd/system/mission-control-worker.service
systemctl daemon-reload

identity_file=$state_root/identity/identity.json
request_file=$state_root/identity/enrollment-request.json
if [ -e "$identity_file" ]; then
    if [ "$resume_identity" = 1 ] && [ -s "$request_file" ]; then
        echo "existing in-progress Vincent identity detected; explicitly resuming bootstrap"
    else
        echo "existing identity detected; refusing implicit reuse" >&2
        echo "follow the documented recovery or replacement enrollment procedure" >&2
        exit 3
    fi
else
    runuser -u "$service_user" -- env \
        HOME="$state_root" USER="$service_user" LOGNAME="$service_user" \
        XDG_CONFIG_HOME="$state_root/.config" XDG_CACHE_HOME="$state_root/.cache" \
        XDG_DATA_HOME="$state_root/.local/share" PATH=/usr/local/bin:/usr/bin:/bin \
        "$install_root/venv/bin/mission-control-worker" \
        --identity-root "$state_root/identity" enroll
fi

echo "installation staged; review and approve enrollment before enabling the service"
echo "service was not enabled or started"
