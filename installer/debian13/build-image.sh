#!/bin/sh
set -eu

script_root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repository_root=$(CDPATH= cd -- "$script_root/../.." && pwd)
. "$script_root/source.env"

source_iso=${1:-}
[ -n "$source_iso" ] && [ -f "$source_iso" ] || { echo "usage: build-image.sh /path/to/verified-debian.iso [output.iso]" >&2; exit 2; }

build_number=$(tr -d '\r\n' <"$script_root/BUILD_NUMBER")
printf '%s\n' "$build_number" | grep -Eq '^[0-9]{4}(\.[0-9]+)?$' || { echo "invalid BUILD_NUMBER" >&2; exit 2; }
installer_version=$(tr -d '\r\n' <"$script_root/VERSION")
output_iso=${2:-$repository_root/dist/vincent-${installer_version}-debian-${DEBIAN_VERSION}-${DEBIAN_ARCH}-build-${build_number}.iso}
case "$(basename -- "$output_iso")" in *"build-${build_number}"*) ;; *) echo "output filename must contain build-${build_number}" >&2; exit 2;; esac
[ ! -e "$output_iso" ] || { echo "refusing to overwrite or append to existing output: $output_iso" >&2; exit 3; }

for command in git xorriso tar sha256sum python3 cmp apt-get dpkg; do command -v "$command" >/dev/null || { echo "required build command is missing: $command" >&2; exit 2; }; done
tracked_dirty=$(git -C "$repository_root" status --porcelain --untracked-files=no)
[ -z "$tracked_dirty" ] || { echo "installer builds require a clean tracked Git checkout" >&2; exit 3; }
commit=$(git -C "$repository_root" rev-parse HEAD)
source_date_epoch=$(git -C "$repository_root" show -s --format=%ct HEAD)
volume_build=$(printf '%s' "$build_number" | tr '.' '_')
volume_id="VINCENT_B${volume_build}"

work_root=$(mktemp -d)
trap 'rm -rf "$work_root"' EXIT HUP INT TERM
payload_root=$work_root/payload
install -d "$payload_root" "$(dirname -- "$output_iso")"

git -C "$repository_root" archive --format=tar.gz --output="$payload_root/platform.tar.gz" HEAD
printf '%s\n' "$commit" >"$payload_root/expected-commit"
printf '%s\n' "$build_number" >"$payload_root/build-number"
python3 - "$payload_root" "$commit" "$build_number" "$repository_root" <<'PYMETA'
import hashlib, json, sys
from pathlib import Path
payload, commit, build, repository = sys.argv[1:]
root, source = Path(payload), Path(repository)
with (root / "platform.tar.gz").open("rb") as stream:
    digest = hashlib.file_digest(stream, "sha256").hexdigest()
(root / "payload-manifest.json").write_text(json.dumps({
    "schema_version": 1, "platform_commit": commit, "installer_build": build,
    "installer_version": (source / "installer/debian13/VERSION").read_text().strip(),
    "runtime_version": (source / "VERSION").read_text().strip(),
    "runtime_build": (source / "BUILD_NUMBER").read_text().strip(), "sha256": digest,
}, sort_keys=True, indent=2) + "\n")
PYMETA
install -m 0644 "$script_root/payload.py" "$payload_root/payload.py"
install -m 0644 "$script_root/preseed.cfg" "$payload_root/preseed.cfg"
install -m 0644 "$script_root/runtime-debian.sources" "$payload_root/runtime-debian.sources"
install -m 0755 "$script_root/installer-media-guard.sh" "$payload_root/installer-media-guard.sh"
install -m 0755 "$script_root/installer-network-preflight.sh" "$payload_root/installer-network-preflight.sh"
install -m 0755 "$script_root/first-boot.sh" "$payload_root/first-boot.sh"
install -m 0755 "$script_root/self-test.sh" "$payload_root/self-test.sh"
install -m 0755 "$script_root/console-status.sh" "$payload_root/console-status.sh"
install -m 0755 "$script_root/codex-console.sh" "$payload_root/codex-console.sh"
install -m 0755 "$script_root/network-console.sh" "$payload_root/network-console.sh"
install -m 0755 "$script_root/network-diagnostics.sh" "$payload_root/network-diagnostics.sh"
install -m 0755 "$script_root/diagnostics.sh" "$payload_root/diagnostics.sh"
install -m 0755 "$script_root/diagnostics-console.sh" "$payload_root/diagnostics-console.sh"
install -m 0644 "$script_root/vincent-first-boot.service" "$payload_root/vincent-first-boot.service"
install -m 0644 "$script_root/vincent-console-status.service" "$payload_root/vincent-console-status.service"
install -m 0644 "$script_root/vincent-codex-console.service" "$payload_root/vincent-codex-console.service"
install -m 0644 "$script_root/vincent-network-console.service" "$payload_root/vincent-network-console.service"
install -m 0644 "$script_root/vincent-diagnostics.service" "$payload_root/vincent-diagnostics.service"
install -m 0644 "$script_root/vincent-diagnostics.timer" "$payload_root/vincent-diagnostics.timer"
install -m 0644 "$script_root/vincent-diagnostics-console.service" "$payload_root/vincent-diagnostics-console.service"
install -m 0644 "$script_root/isolinux-mission-control.cfg" "$payload_root/isolinux-mission-control.cfg"
install -m 0644 "$script_root/grub-mission-control.cfg" "$payload_root/grub-mission-control.cfg"

# Build a complete Debian dependency closure into the installer. Package
# resolution is pinned to Debian 13 and derives its archive trust anchor from
# this exact already-verified source ISO, never from the build host's APT
# configuration.
sh "$script_root/prepare-offline-packages.sh" "$payload_root/offline-packages.tar.gz" "$source_iso"
offline_bundle_sha256=$(sha256sum "$payload_root/offline-packages.tar.gz" | awk '{print $1}')
offline_package_count=$(wc -l <"$payload_root/offline-packages.tar.gz.manifest" | tr -d ' ')
mv "$payload_root/offline-packages.tar.gz.manifest" "$payload_root/offline-packages.manifest"

xorriso -osirrox on -indev "$source_iso" -extract /.disk/info "$work_root/source-disk-info" >/dev/null 2>&1
[ -s "$work_root/source-disk-info" ] || { echo "source Debian media identity is missing" >&2; exit 3; }

xorriso -osirrox on -indev "$source_iso" -extract /isolinux/menu.cfg "$work_root/menu.cfg" >/dev/null 2>&1
xorriso -osirrox on -indev "$source_iso" -extract /boot/grub/grub.cfg "$work_root/grub.cfg" >/dev/null 2>&1
chmod u+w "$work_root/menu.cfg" "$work_root/grub.cfg"
printf '\ninclude mission-control.cfg\n' >>"$work_root/menu.cfg"
cat "$payload_root/grub-mission-control.cfg" >>"$work_root/grub.cfg"
find "$payload_root" "$work_root/menu.cfg" "$work_root/grub.cfg" -exec touch -d "@$source_date_epoch" {} +

xorriso \
    -indev "$source_iso" \
    -outdev "$output_iso" \
    -volid "$volume_id" \
    -boot_image any replay \
    -map "$payload_root/preseed.cfg" /preseed.cfg \
    -map "$payload_root/platform.tar.gz" /vincent/platform.tar.gz \
    -map "$payload_root/payload-manifest.json" /vincent/payload-manifest.json \
    -map "$payload_root/payload.py" /vincent/payload.py \
    -map "$payload_root/expected-commit" /vincent/expected-commit \
    -map "$payload_root/build-number" /vincent/build-number \
    -map "$payload_root/runtime-debian.sources" /vincent/runtime-debian.sources \
    -map "$payload_root/offline-packages.tar.gz" /vincent/offline-packages.tar.gz \
    -map "$payload_root/offline-packages.manifest" /vincent/offline-packages.manifest \
    -map "$payload_root/installer-media-guard.sh" /vincent/installer-media-guard.sh \
    -map "$payload_root/installer-network-preflight.sh" /vincent/installer-network-preflight.sh \
    -map "$payload_root/first-boot.sh" /vincent/first-boot.sh \
    -map "$payload_root/self-test.sh" /vincent/self-test.sh \
    -map "$payload_root/console-status.sh" /vincent/console-status.sh \
    -map "$payload_root/codex-console.sh" /vincent/codex-console.sh \
    -map "$payload_root/network-console.sh" /vincent/network-console.sh \
    -map "$payload_root/network-diagnostics.sh" /vincent/network-diagnostics.sh \
    -map "$payload_root/diagnostics.sh" /vincent/diagnostics.sh \
    -map "$payload_root/diagnostics-console.sh" /vincent/diagnostics-console.sh \
    -map "$payload_root/vincent-first-boot.service" /vincent/vincent-first-boot.service \
    -map "$payload_root/vincent-console-status.service" /vincent/vincent-console-status.service \
    -map "$payload_root/vincent-codex-console.service" /vincent/vincent-codex-console.service \
    -map "$payload_root/vincent-network-console.service" /vincent/vincent-network-console.service \
    -map "$payload_root/vincent-diagnostics.service" /vincent/vincent-diagnostics.service \
    -map "$payload_root/vincent-diagnostics.timer" /vincent/vincent-diagnostics.timer \
    -map "$payload_root/vincent-diagnostics-console.service" /vincent/vincent-diagnostics-console.service \
    -map "$payload_root/isolinux-mission-control.cfg" /isolinux/mission-control.cfg \
    -map "$work_root/menu.cfg" /isolinux/menu.cfg \
    -map "$work_root/grub.cfg" /boot/grub/grub.cfg \
    -commit >/dev/null

xorriso -indev "$output_iso" -pvd_info 2>&1 | grep -F "Volume id    : '$volume_id'" >/dev/null || { echo "generated ISO volume id mismatch" >&2; exit 3; }
xorriso -osirrox on -indev "$output_iso" -extract /.disk/info "$work_root/output-disk-info" >/dev/null 2>&1
cmp -s "$work_root/source-disk-info" "$work_root/output-disk-info" || { echo "generated ISO changed Debian media identity" >&2; exit 3; }

sha256=$(sha256sum "$output_iso" | awk '{print $1}')
manifest="$output_iso.manifest.json"
python3 - "$manifest" "$source_iso" "$output_iso" "$DEBIAN_VERSION" "$DEBIAN_ARCH" "$commit" "$sha256" "$build_number" "$volume_id" "$offline_bundle_sha256" "$offline_package_count" "$repository_root" <<'PY'
import hashlib, json, pathlib, sys
manifest, source_iso, output_iso, debian_version, architecture, commit, output_sha256, build, volume_id, offline_sha256, offline_count, repository_root = sys.argv[1:]
def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()
payload={
    "schema_version":1,
    "debian_version":debian_version,
    "architecture":architecture,
    "build_number":build,
    "installer_version":(pathlib.Path(repository_root)/"installer/debian13/VERSION").read_text().strip(),
    "installer_build":build,
    "runtime_version":(pathlib.Path(repository_root)/"VERSION").read_text().strip(),
    "runtime_build":(pathlib.Path(repository_root)/"BUILD_NUMBER").read_text().strip(),
    "volume_id":volume_id,
    "source_iso":pathlib.Path(source_iso).name,
    "source_sha256":sha256(source_iso),
    "output_iso":pathlib.Path(output_iso).name,
    "output_sha256":output_sha256,
    "platform_commit":commit,
    "runtime_source":"verified_embedded_git_archive",
    "runtime_repository":"https://github.com/logrusbox/vincent.git",
    "partitioning_mode":"debian_installer_interactive",
    "service_account":"vincent",
    "human_login_account":False,
    "interactive_codex_console":"tty2_non_root",
    "persistent_console_status":True,
    "network_configuration_console":"tty3",
    "scheduled_diagnostics_console":"tty4",
    "installer_network_preflight":True,
    "unattended_self_test":True,
    "embedded_secrets":False,
    "installer_media_excluded":True,
    "debian_media_identity_preserved":True,
    "installer_network_mirror_required":False,
    "offline_bootstrap_bundle_sha256":offline_sha256,
    "offline_bootstrap_package_count":int(offline_count),
}
pathlib.Path(manifest).write_text(json.dumps(payload,sort_keys=True,indent=2)+"\n")
PY
sha256sum "$output_iso" >"$output_iso.sha256"
echo "build_number=$build_number"
echo "volume_id=$volume_id"
echo "offline_bootstrap_package_count=$offline_package_count"
echo "offline_bootstrap_bundle_sha256=$offline_bundle_sha256"
echo "image=$output_iso"
echo "manifest=$manifest"
echo "sha256=$sha256"
