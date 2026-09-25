#!/bin/sh
set -eu

image=${1:-}
[ -n "$image" ] && [ -f "$image" ] || { echo "usage: inspect-image.sh /path/to/installer.iso" >&2; exit 2; }
script_root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
build_number=$(tr -d '\r\n' <"$script_root/BUILD_NUMBER")
volume_build=$(printf '%s' "$build_number" | tr '.' '_')
expected_volume="VINCENT_B${volume_build}"
case "$(basename -- "$image")" in *"build-${build_number}"*) ;; *) echo "image filename does not contain build-${build_number}" >&2; exit 3;; esac

inspection_root=$(mktemp -d)
trap 'rm -rf "$inspection_root"' EXIT HUP INT TERM

for required in \
    /.disk/info \
    /preseed.cfg \
    /vincent/platform.tar.gz \
    /vincent/payload-manifest.json \
    /vincent/payload.py \
    /vincent/expected-commit \
    /vincent/build-number \
    /vincent/runtime-debian.sources \
    /vincent/offline-packages.tar.gz \
    /vincent/offline-packages.manifest \
    /vincent/installer-media-guard.sh \
    /vincent/installer-network-preflight.sh \
    /vincent/first-boot.sh \
    /vincent/self-test.sh \
    /vincent/console-status.sh \
    /vincent/codex-console.sh \
    /vincent/network-console.sh \
    /vincent/network-diagnostics.sh \
    /vincent/diagnostics.sh \
    /vincent/diagnostics-console.sh \
    /vincent/vincent-first-boot.service \
    /vincent/vincent-console-status.service \
    /vincent/vincent-codex-console.service \
    /vincent/vincent-network-console.service \
    /vincent/vincent-diagnostics.service \
    /vincent/vincent-diagnostics.timer \
    /vincent/vincent-diagnostics-console.service \
    /isolinux/mission-control.cfg; do
    extracted="$inspection_root/$(basename -- "$required")"
    xorriso -osirrox on -indev "$image" -extract "$required" "$extracted" >/dev/null 2>&1 || { echo "missing installer payload: $required" >&2; exit 3; }
    [ -s "$extracted" ] || { echo "empty installer payload: $required" >&2; exit 3; }
done

tar -tzf "$inspection_root/platform.tar.gz" >/dev/null
python3 "$inspection_root/payload.py" "$inspection_root/platform.tar.gz" \
    "$inspection_root/payload-manifest.json" "$(cat "$inspection_root/expected-commit")" "$build_number"
tar -tzf "$inspection_root/offline-packages.tar.gz" >"$inspection_root/offline-package-list"
[ "$(tr -d '\r\n' <"$inspection_root/build-number")" = "$build_number" ] || { echo "embedded build number mismatch" >&2; exit 3; }
case "$(cat "$inspection_root/info")" in
    Debian\ GNU/Linux*) ;;
    *) echo "Debian installer media identity was not preserved" >&2; exit 3 ;;
esac
volume=$(xorriso -indev "$image" -pvd_info 2>&1 | sed -n "s/^Volume id    : '\(.*\)'$/\1/p" | head -n1)
[ "$volume" = "$expected_volume" ] || { echo "volume id mismatch: expected $expected_volume got $volume" >&2; exit 3; }

grep -F 'passwd/make-user boolean false' "$inspection_root/preseed.cfg" >/dev/null
grep -F 'in-target passwd -l root' "$inspection_root/preseed.cfg" >/dev/null
grep -F 'partman/early_command string sh /cdrom/vincent/installer-network-preflight.sh; sh /cdrom/vincent/installer-media-guard.sh' "$inspection_root/preseed.cfg" >/dev/null
grep -F 'apt-setup/use_mirror boolean false' "$inspection_root/preseed.cfg" >/dev/null
grep -F 'pkgsel/run_tasksel boolean false' "$inspection_root/preseed.cfg" >/dev/null
grep -F '/opt/vincent-installer/offline-debs/*.deb' "$inspection_root/preseed.cfg" >/dev/null
grep -F 'runtime-debian.sources' "$inspection_root/preseed.cfg" >/dev/null
grep -F 'vincent-network-console.service' "$inspection_root/preseed.cfg" >/dev/null
grep -F 'vincent-diagnostics.timer' "$inspection_root/preseed.cfg" >/dev/null
grep -F 'vincent-diagnostics-console.service' "$inspection_root/preseed.cfg" >/dev/null
if grep -E 'partman-auto/(method|choose_recipe|disk)|partman-auto-lvm' "$inspection_root/preseed.cfg" >/dev/null; then
    echo "Vincent-specific forced partitioning detected" >&2
    exit 3
fi
if grep -F 'netcfg/get_nameservers string 1.1.1.1 9.9.9.9' "$inspection_root/preseed.cfg" >/dev/null; then
    echo "temporary 0021.2 DNS experiment leaked into substantive build" >&2
    exit 3
fi
for package in network-manager openssh-server ca-certificates curl git python3 bubblewrap; do
    grep -E "/?${package}_[^/]*\.deb$" "$inspection_root/offline-package-list" >/dev/null || { echo "offline package bundle missing $package" >&2; exit 3; }
done
grep -F 'URIs: https://deb.debian.org/debian' "$inspection_root/runtime-debian.sources" >/dev/null
grep -F 'URIs: https://security.debian.org/debian-security' "$inspection_root/runtime-debian.sources" >/dev/null
grep -F 'Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg' "$inspection_root/runtime-debian.sources" >/dev/null
grep -F 'media_source=' "$inspection_root/installer-media-guard.sh" >/dev/null
grep -F 'parted_devices' "$inspection_root/installer-media-guard.sh" >/dev/null
grep -F 'list-devices' "$inspection_root/installer-media-guard.sh" >/dev/null
grep -F 'blockdev --setro' "$inspection_root/installer-media-guard.sh" >/dev/null
grep -F 'VINCENT_NET_PREFLIGHT' "$inspection_root/installer-network-preflight.sh" >/dev/null
grep -F 'DIRECT_DNS' "$inspection_root/installer-network-preflight.sh" >/dev/null
grep -F 'HTTP_PROBE' "$inspection_root/installer-network-preflight.sh" >/dev/null
if grep -E 'partman-auto/(disk|method|choose_recipe)|debconf-set[[:space:]]+partman' "$inspection_root/installer-media-guard.sh" >/dev/null; then
    echo "installer media guard attempts to select a target disk" >&2
    exit 3
fi
grep -F 'BUILD:' "$inspection_root/console-status.sh" >/dev/null
grep -F 'runuser -u "$service_user"' "$inspection_root/codex-console.sh" >/dev/null
grep -F 'nmcli --ask device wifi connect' "$inspection_root/network-console.sh" >/dev/null
grep -F 'Alt+F4: diagnostics' "$inspection_root/network-console.sh" >/dev/null
grep -F 'DEBIAN PACKAGE VISIBILITY' "$inspection_root/network-diagnostics.sh" >/dev/null
grep -F 'codex_code_mode_host' "$inspection_root/diagnostics.sh" >/dev/null
grep -F 'TTYPath=/dev/tty4' "$inspection_root/vincent-diagnostics-console.service" >/dev/null
grep -F 'OnUnitActiveSec=15min' "$inspection_root/vincent-diagnostics.timer" >/dev/null

if grep -a -E 'BEGIN (OPENSSH|RSA|EC) PRIVATE KEY' "$image" >/dev/null; then echo "private key material detected in installer image" >&2; exit 4; fi

echo "BUILD_NUMBER=$build_number"
echo "VOLUME_ID=$volume"
echo "DEBIAN_MEDIA_IDENTITY=PASS"
echo "PARTMAN_DEVICE_FILTER=PASS"
echo "INSTALLER_MEDIA_EXCLUSION=PASS"
echo "INSTALLER_NETWORK_PREFLIGHT=PASS"
echo "OFFLINE_BOOTSTRAP_BUNDLE=PASS"
echo "INSTALLER_NETWORK_MIRROR_REQUIRED=false"
echo "RUNTIME_WIFI_RECOVERY=PASS"
echo "SCHEDULED_DIAGNOSTICS=PASS"
echo "INSTALLER_INSPECTION=PASS"
