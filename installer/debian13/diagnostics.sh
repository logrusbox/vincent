#!/bin/sh
set -eu

report=/var/lib/vincent-install/diagnostics.json
install -d -m 0700 /var/lib/vincent-install

python3 - "$report" <<'PY'
import grp, json, os, pwd, shutil, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

report_path = Path(sys.argv[1])
checks = []

def run(name, command, timeout=30, predicate=lambda rc, out, err: rc == 0, required=True):
    try:
        completed = subprocess.run(command, text=True, capture_output=True, timeout=timeout)
        out = completed.stdout or ""
        err = completed.stderr or ""
        ok = bool(predicate(completed.returncode, out, err))
        detail = (out or err).strip().replace("\x00", "")[:1000]
    except Exception as exc:
        ok = False
        detail = repr(exc)
    checks.append({"name": name, "ok": ok, "detail": detail, "required": required})
    return ok

def run_as_vincent(name, command, timeout=30, predicate=lambda rc, out, err: rc == 0, required=True):
    environment = [
        "HOME=/var/lib/vincent", "USER=vincent", "LOGNAME=vincent",
        "XDG_CONFIG_HOME=/var/lib/vincent/.config",
        "XDG_CACHE_HOME=/var/lib/vincent/.cache",
        "XDG_DATA_HOME=/var/lib/vincent/.local/share",
        "XDG_RUNTIME_DIR=/run/vincent",
        "PATH=/usr/local/bin:/usr/bin:/bin",
    ]
    return run(name, ["runuser", "-u", "vincent", "--", "env", *environment, *command], timeout, predicate)

def record(name, ok, detail="", required=True):
    checks.append({"name": name, "ok": bool(ok), "detail": str(detail)[:1000], "required": required})

run("default_route", ["ip", "route", "show", "default"], required=False)
run("dns_debian", ["getent", "ahosts", "deb.debian.org"], required=False)
run("dns_github", ["getent", "ahosts", "github.com"], required=False)
run("debian_index", ["curl", "--fail", "--silent", "--show-error", "--location", "--connect-timeout", "5", "--max-time", "20", "https://deb.debian.org/debian/dists/trixie/InRelease", "-o", "/dev/null"], required=False)
run("vincent_git", ["git", "ls-remote", "https://github.com/logrusbox/vincent.git", "HEAD"], required=False)
run("network_manager", ["systemctl", "is-active", "--quiet", "NetworkManager"])
run("ssh", ["systemctl", "is-active", "--quiet", "ssh"])
run_as_vincent("container_rootless", ["podman", "info", "--format", "{{.Host.Security.Rootless}}"], predicate=lambda rc, out, err: rc == 0 and out.strip() == "true")
run_as_vincent("docker_compatible_cli", ["docker", "--version"])
run("codex", ["codex", "--version"], required=False)
run("bubblewrap", ["bwrap", "--version"])
run("time_sync", ["timedatectl", "show", "-p", "NTPSynchronized", "--value"], predicate=lambda rc, out, err: rc == 0 and out.strip().lower() == "yes", required=False)

try:
    account = pwd.getpwnam("vincent")
    groups = {grp.getgrgid(account.pw_gid).gr_name} | {group.gr_name for group in grp.getgrall() if "vincent" in group.gr_mem}
    record("no_root_equivalent_docker_group", "docker" not in groups, ",".join(sorted(groups)))
except KeyError:
    record("no_root_equivalent_docker_group", False, "vincent account missing")

host = shutil.which("codex-code-mode-host")
record("codex_code_mode_host", bool(host and os.access(host, os.X_OK)), host or "missing", required=False)

build = Path("/etc/vincent/build-number")
record("build_metadata", build.is_file() and bool(build.read_text().strip()), build.read_text().strip() if build.is_file() else "missing")

identity = Path("/var/lib/vincent/identity/identity.json")
request = Path("/var/lib/vincent/identity/enrollment-request.json")
record("identity_state", identity.is_file(), f"identity={identity.is_file()}")
record("enrollment_request", request.is_file(), "optional explicit enrollment", required=False)

usage = shutil.disk_usage("/")
free_pct = round((usage.free / usage.total) * 100, 1) if usage.total else 0
record("root_free_space", free_pct >= 10.0, f"free_percent={free_pct}")

run("runtime_and_installer_versions", ["vincent", "version"])
passed = all(item["ok"] for item in checks if item["required"])
payload = {
    "schema_version": 1,
    "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "overall": "PASS" if passed else "FAIL",
    "checks": checks,
}
report_path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
os.chmod(report_path, 0o600)
for item in checks:
    print(f"{item['name']}: {'PASS' if item['ok'] else 'FAIL'} {item['detail']}")
print(f"VINCENT_DIAGNOSTICS={'PASS' if passed else 'FAIL'}")
sys.exit(0 if passed else 1)
PY
