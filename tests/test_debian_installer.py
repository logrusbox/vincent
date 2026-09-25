import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "installer/debian13"


class DebianInstallerTests(unittest.TestCase):
    def test_all_installer_shell_scripts_parse(self):
        names = (
            "fetch-source.sh", "build-image.sh", "inspect-image.sh", "flash-usb.sh",
            "prepare-offline-packages.sh", "installer-media-guard.sh", "installer-network-preflight.sh",
            "first-boot.sh", "self-test.sh", "console-status.sh", "codex-console.sh",
            "network-console.sh", "network-diagnostics.sh", "diagnostics.sh", "diagnostics-console.sh",
        )
        scripts = [INSTALLER / name for name in names]
        scripts += [ROOT / "bootstrap/provision-worker-baseline.sh", ROOT / "installer/install.sh"]
        for path in scripts:
            result = subprocess.run(["sh", "-n", str(path)])
            self.assertEqual(result.returncode, 0, path.name)

    def test_partitioning_is_normal_debian_interactive_workflow(self):
        preseed = (INSTALLER / "preseed.cfg").read_text()
        for marker in (
            "partman-auto/disk", "partman-auto/method", "partman-auto/choose_recipe",
            "partman-auto-lvm", "partman/confirm_write_new_label", "partman/confirm boolean",
        ):
            self.assertNotIn(marker, preseed)

    def test_active_installer_media_is_excluded_without_selecting_target(self):
        preseed = (INSTALLER / "preseed.cfg").read_text()
        guard = (INSTALLER / "installer-media-guard.sh").read_text()
        build = (INSTALLER / "build-image.sh").read_text()
        self.assertIn("partman/early_command string sh /cdrom/vincent/installer-network-preflight.sh; sh /cdrom/vincent/installer-media-guard.sh", preseed)
        self.assertNotIn("preseed/early_command string sh /cdrom/vincent/installer-media-guard.sh", preseed)
        self.assertIn('/cdrom', guard)
        self.assertIn('parted_devices', guard)
        self.assertIn('list-devices', guard)
        self.assertIn('blockdev --setro', guard)
        self.assertIn('/run/vincent-installer-disk', guard)
        self.assertNotIn('partman-auto/disk', guard)
        self.assertNotIn('debconf-set partman', guard)
        self.assertIn('/vincent/installer-media-guard.sh', build)
        self.assertIn('/vincent/installer-network-preflight.sh', build)
        self.assertIn('"installer_media_excluded":True', build)
        self.assertIn('"installer_network_preflight":True', build)

    def test_installer_network_preflight_captures_interception_evidence(self):
        script = (INSTALLER / "installer-network-preflight.sh").read_text()
        self.assertIn("/etc/resolv.conf", script)
        self.assertIn("DIRECT_DNS", script)
        self.assertIn("1.1.1.1", script)
        self.assertIn("9.9.9.9", script)
        self.assertIn("HTTP_PROBE", script)
        self.assertIn("deb.debian.org", script)
        self.assertIn("security.debian.org", script)
        self.assertIn("VINCENT_NET_EVIDENCE", script)

    def test_installer_uses_verified_media_plus_offline_bootstrap_bundle(self):
        preseed = (INSTALLER / "preseed.cfg").read_text()
        build = (INSTALLER / "build-image.sh").read_text()
        inspect = (INSTALLER / "inspect-image.sh").read_text()
        prepare = (INSTALLER / "prepare-offline-packages.sh").read_text()
        self.assertIn("apt-setup/use_mirror boolean false", preseed)
        self.assertIn("apt-setup/cdrom/set-first boolean true", preseed)
        self.assertIn("pkgsel/run_tasksel boolean false", preseed)
        self.assertIn("pkgsel/upgrade select none", preseed)
        self.assertIn("offline-packages.tar.gz", preseed)
        self.assertIn("/opt/vincent-installer/offline-debs/*.deb", preseed)
        self.assertIn("prepare-offline-packages.sh", build)
        self.assertIn("offline-packages.tar.gz", build)
        self.assertIn('"installer_network_mirror_required":False', build)
        self.assertIn('"offline_bootstrap_bundle_sha256":offline_sha256', build)
        self.assertIn("Dir::State::status", prepare)
        self.assertIn("--download-only", prepare)
        self.assertIn("network-manager", prepare)
        self.assertIn("openssh-server", prepare)
        self.assertIn("bubblewrap", prepare)
        self.assertIn("OFFLINE_BOOTSTRAP_BUNDLE=PASS", inspect)
        self.assertIn("INSTALLER_NETWORK_MIRROR_REQUIRED=false", inspect)

    def test_installer_media_identity_is_preserved(self):
        build = (INSTALLER / "build-image.sh").read_text()
        inspect = (INSTALLER / "inspect-image.sh").read_text()
        self.assertIn("source-disk-info", build)
        self.assertIn("output-disk-info", build)
        self.assertIn('cmp -s "$work_root/source-disk-info" "$work_root/output-disk-info"', build)
        self.assertNotIn('-map "$payload_root/disk-info" /.disk/info', build)
        self.assertIn('"debian_media_identity_preserved":True', build)
        self.assertIn("Debian\\ GNU/Linux*", inspect)
        self.assertIn("DEBIAN_MEDIA_IDENTITY=PASS", inspect)

    def test_runtime_sources_use_signed_debian_https_repositories(self):
        sources = (INSTALLER / "runtime-debian.sources").read_text()
        self.assertIn("URIs: https://deb.debian.org/debian", sources)
        self.assertIn("URIs: https://security.debian.org/debian-security", sources)
        self.assertIn("Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg", sources)
        self.assertNotIn("8.8.8.8", sources)

    def test_no_human_account_and_root_locked_before_first_boot(self):
        preseed = (INSTALLER / "preseed.cfg").read_text()
        self.assertIn("passwd/root-login boolean true", preseed)
        self.assertIn("passwd/root-password-crypted password !vincent-installer-no-login!", preseed)
        self.assertIn("passwd/make-user boolean false", preseed)
        self.assertIn("in-target passwd -l root", preseed)
        self.assertNotIn("passwd/username", preseed)
        self.assertNotIn("passwd/user-fullname", preseed)
        self.assertNotIn("passwd/user-password", preseed)

    def test_network_and_wifi_selection_remain_interactive(self):
        preseed = (INSTALLER / "preseed.cfg").read_text()
        self.assertIn("netcfg/get_hostname string vincent-worker", preseed)
        self.assertNotIn("unenrolled", preseed)
        self.assertNotIn("netcfg/choose_interface", preseed)
        self.assertNotIn("netcfg/get_nameservers string 1.1.1.1 9.9.9.9", preseed)
        self.assertNotIn("8.8.8.8", preseed)
        self.assertNotIn("8.8.4.4", preseed)
        for name in ("grub-mission-control.cfg", "isolinux-mission-control.cfg"):
            boot = (INSTALLER / name).read_text()
            self.assertNotIn("auto=true", boot)
            self.assertIn("priority=high", boot)
            self.assertIn("locale=en_US.UTF-8", boot)
            self.assertIn("keymap=us", boot)

    def test_runtime_wifi_recovery_and_diagnostics_exist(self):
        preseed = (INSTALLER / "preseed.cfg").read_text()
        prepare = (INSTALLER / "prepare-offline-packages.sh").read_text()
        console = (INSTALLER / "network-console.sh").read_text()
        diagnostics = (INSTALLER / "network-diagnostics.sh").read_text()
        unit = (INSTALLER / "vincent-network-console.service").read_text()
        self.assertIn("network-manager", prepare)
        self.assertIn("iw", prepare)
        self.assertIn("wpasupplicant", prepare)
        self.assertIn("vincent-network-console.service", preseed)
        self.assertIn("nmcli --ask device wifi connect", console)
        self.assertIn("saved Wi-Fi profiles", console)
        self.assertIn("show_unique_wifi", console)
        self.assertNotIn("vincent-network-diagnostics", console)
        self.assertIn("Alt+F4: diagnostics", console)
        self.assertIn("deb.debian.org/debian/dists/trixie/InRelease", diagnostics)
        self.assertNotIn("chatgpt.com/codex/install.sh", diagnostics)
        self.assertNotIn("download.docker.com", diagnostics)
        self.assertIn("podman", diagnostics)
        self.assertIn("git ls-remote https://github.com/logrusbox/vincent.git HEAD", diagnostics)
        self.assertIn("DEBIAN PACKAGE VISIBILITY", diagnostics)
        self.assertIn("TTYPath=/dev/tty3", unit)

    def test_scheduled_diagnostics_use_separate_tty4(self):
        preseed = (INSTALLER / "preseed.cfg").read_text()
        diagnostics = (INSTALLER / "diagnostics.sh").read_text()
        console = (INSTALLER / "diagnostics-console.sh").read_text()
        timer = (INSTALLER / "vincent-diagnostics.timer").read_text()
        unit = (INSTALLER / "vincent-diagnostics-console.service").read_text()
        self.assertIn("vincent-diagnostics.timer", preseed)
        self.assertIn("vincent-diagnostics-console.service", preseed)
        self.assertIn("OnUnitActiveSec=15min", timer)
        self.assertIn("TTYPath=/dev/tty4", unit)
        self.assertIn("codex_code_mode_host", diagnostics)
        self.assertIn("container_rootless", diagnostics)
        self.assertIn("no_root_equivalent_docker_group", diagnostics)
        self.assertIn("root_free_space", diagnostics)
        self.assertIn("VINCENT DIAGNOSTICS", console)

    def test_vincent_service_identity_is_dedicated_and_non_login(self):
        install = (ROOT / "installer/install.sh").read_text()
        unit = (ROOT / "installer/systemd/mission-control-worker.service").read_text()
        bootstrap = (ROOT / "bootstrap/provision-worker-baseline.sh").read_text()
        self.assertIn("service_user=vincent", install)
        self.assertIn("--shell /usr/sbin/nologin", install)
        self.assertIn("state_root=/var/lib/vincent", install)
        self.assertIn("User=vincent", unit)
        self.assertIn("Group=vincent", unit)
        self.assertIn("XDG_RUNTIME_DIR=/run/vincent", unit)
        self.assertNotIn("User=mission-control", unit)
        self.assertNotIn("runuser -u nobody", bootstrap)
        self.assertNotIn("usermod -aG docker", bootstrap)

    def test_first_boot_is_explicitly_resumable(self):
        first_boot = (INSTALLER / "first-boot.sh").read_text()
        install = (ROOT / "installer/install.sh").read_text()
        self.assertIn("bootstrap-state.json", first_boot)
        self.assertIn("write_bootstrap_state in_progress", first_boot)
        self.assertIn("write_bootstrap_state completed", first_boot)
        self.assertIn("VINCENT_RESUME_IDENTITY=$resume_identity", first_boot)
        self.assertIn("resume_identity=${VINCENT_RESUME_IDENTITY:-0}", install)
        self.assertIn("explicitly resuming bootstrap", install)
        self.assertIn("refusing implicit reuse", install)

    def test_generic_baseline_excludes_project_specific_ddev(self):
        preseed = (INSTALLER / "preseed.cfg").read_text()
        bootstrap = (ROOT / "bootstrap/provision-worker-baseline.sh").read_text()
        selftest = (INSTALLER / "self-test.sh").read_text()
        self.assertNotIn("ddev", preseed.lower())
        self.assertNotIn("ddev", bootstrap.lower())
        self.assertNotIn("ddev", selftest.lower())
        self.assertNotIn("docker-ce", bootstrap)
        self.assertIn("podman", bootstrap)
        self.assertIn("podman-docker", bootstrap)
        self.assertIn("uidmap", bootstrap)
        self.assertIn("--add-subuids", bootstrap)
        self.assertIn("--add-subgids", bootstrap)
        self.assertIn("gh git", bootstrap)
        self.assertIn("network-manager", bootstrap)
        self.assertIn("bubblewrap", bootstrap)

    def test_provider_installation_requires_reviewed_local_artifacts(self):
        bootstrap = (ROOT / "bootstrap/provision-worker-baseline.sh").read_text()
        self.assertIn('VINCENT_CODEX_MANIFEST:?', bootstrap)
        self.assertIn('install-provider.py', bootstrap)
        self.assertNotIn('chatgpt.com/codex/install.sh', bootstrap)
        self.assertNotIn('hello-world:latest', bootstrap)

    def test_codex_companion_runtime_is_preserved(self):
        bootstrap = (ROOT / "bootstrap/provision-worker-baseline.sh").read_text()
        selftest = (INSTALLER / "self-test.sh").read_text()
        self.assertIn("codex-code-mode-host", bootstrap)
        self.assertIn("/opt/vincent-codex/bin/codex", bootstrap)
        self.assertIn("/usr/local/bin/codex-code-mode-host", bootstrap)
        self.assertNotIn('run("codex"', selftest)

    def test_build_number_is_durable_and_consistent(self):
        build_number = (INSTALLER / "BUILD_NUMBER").read_text().strip()
        self.assertRegex(build_number, r"^\d{4}(?:\.\d+)?$")
        build = (INSTALLER / "build-image.sh").read_text()
        inspect = (INSTALLER / "inspect-image.sh").read_text()
        self.assertIn("BUILD_NUMBER", build)
        self.assertIn("build-${build_number}", build)
        self.assertIn("volume_build=$(printf '%s' \"$build_number\" | tr '.' '_')", build)
        self.assertIn('volume_id="VINCENT_B${volume_build}"', build)
        self.assertIn("volume_build=$(printf '%s' \"$build_number\" | tr '.' '_')", inspect)
        self.assertIn('expected_volume="VINCENT_B${volume_build}"', inspect)
        self.assertIn('"build_number":build', build)
        self.assertIn('/vincent/build-number', build)
        console = (INSTALLER / "console-status.sh").read_text()
        self.assertIn("BUILD:", console)
        self.assertIn("/etc/vincent/build-number", console)

    def test_runtime_source_is_verified_embedded_payload(self):
        script = (INSTALLER / "first-boot.sh").read_text()
        self.assertIn("payload-manifest.json", script)
        self.assertIn("--destination", script)
        self.assertNotIn(" fetch ", script)
        self.assertNotIn('rm -rf "$source_root"', script)
        self.assertNotIn("https://github.com", script)

    def test_dashboard_and_tty2_codex_console_exist(self):
        dashboard = (INSTALLER / "console-status.sh").read_text()
        codex_console = (INSTALLER / "codex-console.sh").read_text()
        self.assertIn("LIVE WORK OUTPUT", dashboard)
        self.assertIn("LAST ERROR", dashboard)
        self.assertIn("Alt+F2", dashboard)
        self.assertIn("Alt+F4", dashboard)
        self.assertIn("runuser -u \"$service_user\"", codex_console)
        self.assertIn("service_user=vincent", codex_console)
        self.assertIn("XDG_RUNTIME_DIR=\"$service_runtime\"", codex_console)
        self.assertNotIn("/bin/bash", codex_console)

    def test_build_never_writes_directly_to_block_devices(self):
        build = (INSTALLER / "build-image.sh").read_text()
        self.assertNotIn("/dev/sd", build)
        self.assertNotRegex(build, re.compile(r"\bdd\s+if="))
        self.assertIn("refusing to overwrite or append to existing output", build)

    def test_inspection_enforces_build_number_and_interactive_partitioning(self):
        inspect = (INSTALLER / "inspect-image.sh").read_text()
        self.assertIn('expected_volume="VINCENT_B${volume_build}"', inspect)
        self.assertIn("embedded build number mismatch", inspect)
        self.assertIn("forced partitioning detected", inspect)
        self.assertIn("DEBIAN_MEDIA_IDENTITY=PASS", inspect)
        self.assertIn("PARTMAN_DEVICE_FILTER=PASS", inspect)
        self.assertIn("INSTALLER_MEDIA_EXCLUSION=PASS", inspect)
        self.assertIn("INSTALLER_NETWORK_PREFLIGHT=PASS", inspect)
        self.assertIn("OFFLINE_BOOTSTRAP_BUNDLE=PASS", inspect)
        self.assertIn("RUNTIME_WIFI_RECOVERY=PASS", inspect)
        self.assertIn("SCHEDULED_DIAGNOSTICS=PASS", inspect)
        self.assertIn("INSTALLER_INSPECTION=PASS", inspect)

    def test_toolchain_uses_rootless_podman_and_complete_environments(self):
        script = (ROOT / "bootstrap/provision-worker-baseline.sh").read_text()
        self.assertNotIn("download.docker.com", script)
        self.assertNotIn("docker-ce", script)
        self.assertNotIn("usermod -aG docker", script)
        self.assertIn("podman podman-docker uidmap", script)
        self.assertIn("container_privilege_model", script)
        self.assertIn("rootless_podman", script)
        self.assertIn("service_user=vincent", script)
        self.assertIn("service_run()", script)
        self.assertIn("HOME=\"$service_home\"", script)
        self.assertIn("XDG_RUNTIME_DIR=\"$service_runtime\"", script)
        self.assertIn('runuser -u "$service_user" -- env', script)
        self.assertNotIn('runuser -u "$service_user" --login', script)
        self.assertIn("export HOME=/root USER=root LOGNAME=root", script)
        self.assertIn("XDG_CONFIG_HOME=/root/.config", script)
        self.assertNotIn("runuser -u nobody", script)

    def test_first_boot_assigns_stable_vincent_hostname(self):
        script = (INSTALLER / "first-boot.sh").read_text()
        self.assertIn("/sys/class/dmi/id/product_uuid", script)
        self.assertIn('print(f"vincent-worker-{value:06d}")', script)
        self.assertIn('hostnamectl set-hostname "$vincent_hostname"', script)

    def test_debian_source_location_is_version_pinned(self):
        source = (INSTALLER / "source.env").read_text()
        version = re.search(r"^DEBIAN_VERSION=(.+)$", source, re.MULTILINE).group(1)
        self.assertIn(f"/archive/{version}/amd64/iso-cd", source)
        self.assertNotIn("/current/", source)

    def test_fetch_requires_the_debian_cd_signing_keyring(self):
        script = (INSTALLER / "fetch-source.sh").read_text()
        self.assertIn("/usr/share/keyrings/debian-role-keys.gpg", script)
        self.assertNotIn("debian-archive-keyring.gpg", script)


if __name__ == "__main__":
    unittest.main()
