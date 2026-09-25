#!/bin/sh
set -eu

output=${1:-}
source_iso=${2:-}
[ -n "$output" ] && [ -n "$source_iso" ] && [ -f "$source_iso" ] || {
    echo "usage: prepare-offline-packages.sh OUTPUT.tar.gz VERIFIED_DEBIAN.iso" >&2
    exit 2
}

for command in apt-get dpkg dpkg-deb tar sha256sum xorriso; do
    command -v "$command" >/dev/null || { echo "missing required command: $command" >&2; exit 2; }
done

arch=$(dpkg --print-architecture)
[ "$arch" = "amd64" ] || { echo "offline installer bundle currently requires amd64 builder" >&2; exit 2; }

mkdir -p "$(dirname -- "$output")"
output_dir=$(CDPATH= cd -- "$(dirname -- "$output")" && pwd)
output="$output_dir/$(basename -- "$output")"

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT HUP INT TERM
state="$work/state"
cache="$work/cache"
log="$work/log"
sourceparts="$work/sourceparts"
keyring_pool="$work/keyring-pool"
keyring_root="$work/keyring-root"
sources="$work/debian.sources.list"
mkdir -p "$state/lists/partial" "$cache/archives/partial" "$log" "$sourceparts" "$keyring_pool" "$keyring_root"
: >"$state/status"

# The Debian ISO was already authenticated by fetch-source.sh. Derive the APT
# archive trust anchor from that exact verified installation medium rather than
# trusting whatever Debian/Ubuntu keyring happens to be installed on the build
# host.
xorriso -osirrox on -indev "$source_iso" \
    -extract /pool/main/d/debian-archive-keyring "$keyring_pool" >/dev/null 2>&1 || {
    echo "verified Debian ISO does not contain debian-archive-keyring" >&2
    exit 3
}
keyring_deb=$(find "$keyring_pool" -type f -name 'debian-archive-keyring_*_all.deb' -print -quit)
[ -n "$keyring_deb" ] || { echo "Debian archive keyring package missing from verified ISO" >&2; exit 3; }
dpkg-deb -x "$keyring_deb" "$keyring_root"
archive_keyring="$keyring_root/usr/share/keyrings/debian-archive-keyring.gpg"
[ -s "$archive_keyring" ] || { echo "Debian archive keyring missing after extraction" >&2; exit 3; }

cat >"$sources" <<EOF
deb [arch=amd64 signed-by=$archive_keyring] https://deb.debian.org/debian trixie main
deb [arch=amd64 signed-by=$archive_keyring] https://deb.debian.org/debian trixie-updates main
deb [arch=amd64 signed-by=$archive_keyring] https://security.debian.org/debian-security trixie-security main
EOF

packages='debian-archive-keyring sudo git curl ca-certificates gpg jq gh rsync openssh-client openssh-server python3 python3-venv python3-pip python3-setuptools python3-wheel podman podman-docker uidmap slirp4netns passt fuse-overlayfs build-essential xz-utils network-manager iw wpasupplicant rfkill bubblewrap'

# Isolate package resolution completely from the build host. GitHub Actions runs
# Ubuntu, while Vincent targets Debian 13; inheriting host APT sources would
# silently construct an invalid cross-distribution bundle.
apt_opts="-o Debug::NoLocking=1 -o Dir::State=$state -o Dir::State::status=$state/status -o Dir::Cache=$cache -o Dir::Cache::archives=$cache/archives -o Dir::Log=$log -o Dir::Etc::sourcelist=$sources -o Dir::Etc::sourceparts=$sourceparts -o APT::Architecture=amd64"

# shellcheck disable=SC2086
apt-get $apt_opts update
# shellcheck disable=SC2086
apt-get $apt_opts --download-only --no-install-recommends -y install $packages

set -- "$cache"/archives/*.deb
[ -e "$1" ] || { echo "offline package bundle is empty" >&2; exit 3; }

manifest="$work/offline-packages.manifest"
(
    cd "$cache/archives"
    sha256sum ./*.deb | sort
) >"$manifest"

(
    cd "$cache/archives"
    tar -czf "$output" ./*.deb
)
cp "$manifest" "${output}.manifest"

echo "offline_bundle=$output"
echo "offline_bundle_sha256=$(sha256sum "$output" | awk '{print $1}')"
echo "offline_package_count=$(wc -l <"$manifest" | tr -d ' ')"
