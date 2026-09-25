#!/bin/sh
set -eu
: "${VINCENT_CODEX_MANIFEST:?provide an absolute reviewed local provider manifest}"

status_root=/var/lib/vincent-install
service_user=vincent
service_home=/var/lib/vincent
service_config=$service_home/.config
service_cache=$service_home/.cache
service_data=$service_home/.local/share
service_runtime=/run/vincent
# Canonical preserved Codex runtime: /opt/vincent-codex/bin/codex
codex_root=/opt/vincent-codex

# systemd services do not guarantee a login-style root environment.
export HOME=/root USER=root LOGNAME=root
export XDG_CONFIG_HOME=/root/.config XDG_CACHE_HOME=/root/.cache XDG_DATA_HOME=/root/.local/share
install -d -m 0700 "$HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" "$XDG_DATA_HOME"

install -d -o root -g "$service_user" -m 0750 "$status_root"
install -d -o "$service_user" -g "$service_user" -m 0700 \
    "$service_home" "$service_config" "$service_cache" "$service_data" "$service_home/.local/bin" "$service_runtime"

service_run() {
    runuser -u "$service_user" -- env \
        HOME="$service_home" USER="$service_user" LOGNAME="$service_user" \
        XDG_CONFIG_HOME="$service_config" XDG_CACHE_HOME="$service_cache" \
        XDG_DATA_HOME="$service_data" XDG_RUNTIME_DIR="$service_runtime" \
        PATH=/usr/local/bin:/usr/bin:/bin "$@"
}

apt-get update
apt-get install -y \
    ca-certificates curl gpg jq gh git network-manager iw wpasupplicant rfkill bubblewrap \
    podman podman-docker uidmap slirp4netns passt fuse-overlayfs
systemctl enable --now NetworkManager

# Rootless Podman needs subordinate UID/GID ranges. Do not grant the service
# account access to a root-owned Docker daemon/socket; docker-compatible CLI
# behavior is supplied by podman-docker and executes rootlessly as vincent.
if ! grep -q "^${service_user}:" /etc/subuid; then
    usermod --add-subuids 100000-165535 "$service_user"
fi
if ! grep -q "^${service_user}:" /etc/subgid; then
    usermod --add-subgids 100000-165535 "$service_user"
fi

# This optional operator command requires an independently reviewed manifest.
# Preserve codex-code-mode-host beside /opt/vincent-codex/bin/codex.
: "${VINCENT_CODEX_MANIFEST:?provide an absolute reviewed local provider manifest}"
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
python3 "$script_dir/install-provider.py" "$VINCENT_CODEX_MANIFEST" --destination "$codex_root"
ln -sfn "$codex_root/bin/codex" /usr/local/bin/codex
ln -sfn "$codex_root/bin/codex-code-mode-host" /usr/local/bin/codex-code-mode-host

podman --version
docker --version
[ "$(service_run podman info --format '{{.Host.Security.Rootless}}')" = true ]
service_run podman unshare true
gh --version
bwrap --version
codex --version
codex-code-mode-host --help >/dev/null 2>&1 || true
service_run /usr/local/bin/codex --version
nmcli --version

python3 - "$status_root/toolchain.json" <<'PY'
import json, subprocess, sys
from pathlib import Path

def output(*command):
    return subprocess.run(command, text=True, capture_output=True, check=True).stdout.strip()

payload = {
    "schema_version": 1,
    "container_runtime": output("podman", "--version"),
    "docker_compatible_cli": output("docker", "--version"),
    "container_privilege_model": "rootless_podman",
    "github_cli": output("gh", "--version").splitlines()[0],
    "codex": output("codex", "--version"),
    "bubblewrap": output("bwrap", "--version"),
    "codex_code_mode_host": str(Path("/usr/local/bin/codex-code-mode-host").resolve()),
    "network_manager": output("nmcli", "--version"),
    "codex_manifest": json.loads(Path("/opt/vincent-codex/bin/manifest.json").read_text()),
}
Path(sys.argv[1]).write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
PY
chmod 0600 "$status_root/toolchain.json"
