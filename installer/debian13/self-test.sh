#!/bin/sh
set -eu

report=/var/lib/vincent-install/self-test.json
install -d -m 0700 /var/lib/vincent-install

python3 - "$report" <<'PY'
import grp, json, os, pwd, re, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

report_path = Path(sys.argv[1])
checks = []

def run(name, command, predicate=lambda rc, out, err: rc == 0):
    completed = subprocess.run(command, text=True, capture_output=True)
    output = (completed.stdout or completed.stderr).strip()
    ok = predicate(completed.returncode, completed.stdout, completed.stderr)
    checks.append({"name": name, "ok": bool(ok), "detail": output[:500]})
    return ok

def run_as_vincent(name, command, predicate=lambda rc, out, err: rc == 0):
    environment = [
        "HOME=/var/lib/vincent",
        "USER=vincent",
        "LOGNAME=vincent",
        "XDG_CONFIG_HOME=/var/lib/vincent/.config",
        "XDG_CACHE_HOME=/var/lib/vincent/.cache",
        "XDG_DATA_HOME=/var/lib/vincent/.local/share",
        "XDG_RUNTIME_DIR=/run/vincent",
        "PATH=/usr/local/bin:/usr/bin:/bin",
    ]
    return run(name, ["runuser", "-u", "vincent", "--", "env", *environment, *command], predicate)

def record(name, ok, detail=""):
    checks.append({"name": name, "ok": bool(ok), "detail": str(detail)[:500]})
    return bool(ok)

hostname = subprocess.run(["hostname"], text=True, capture_output=True, check=True).stdout.strip()
record("hostname", bool(re.fullmatch(r"vincent-worker-\d{6}", hostname)), hostname)
run("network_route", ["ip", "route", "get", "1.1.1.1"])
run("network_dns", ["getent", "ahosts", "github.com"])
run("network_manager", ["systemctl", "is-active", "--quiet", "NetworkManager"])
run("network_diagnostics", ["/usr/local/sbin/vincent-network-diagnostics"])
run("diagnostics_timer", ["systemctl", "is-enabled", "--quiet", "vincent-diagnostics.timer"])
run("diagnostics_console", ["systemctl", "is-enabled", "--quiet", "vincent-diagnostics-console.service"])
run("ssh_service", ["systemctl", "is-active", "--quiet", "ssh"])
run("git", ["git", "--version"])
run("github_cli", ["gh", "--version"])
run_as_vincent(
    "container_rootless",
    ["podman", "info", "--format", "{{.Host.Security.Rootless}}"],
    lambda rc, out, err: rc == 0 and out.strip() == "true",
)
run_as_vincent("container_smoke", ["podman", "run", "--rm", "docker.io/library/hello-world:latest"])
run_as_vincent("docker_compatible_cli", ["docker", "--version"])
run("bubblewrap", ["bwrap", "--version"])
run("codex", ["codex", "--version"])
record("codex_code_mode_host", os.path.isfile("/opt/vincent-codex/bin/codex-code-mode-host") and os.access("/opt/vincent-codex/bin/codex-code-mode-host", os.X_OK), "/opt/vincent-codex/bin/codex-code-mode-host")
run("python_packaging", ["python3", "-c", "import pip, setuptools.build_meta"])

source_root = Path("/opt/vincent/source")
expected_path = Path("/etc/vincent/build-commit")
installed_path = Path("/var/lib/vincent-install/installed-commit")
build_path = Path("/etc/vincent/build-number")
try:
    expected = expected_path.read_text().strip()
    installed = installed_path.read_text().strip()
    metadata = json.loads(Path("/opt/vincent-installer/payload-manifest.json").read_text())
    record("payload_exact_commit", bool(expected and expected == installed == metadata["platform_commit"]), f"expected={expected} installed={installed}")
    run("payload_integrity", ["python3", "/opt/vincent-installer/payload.py",
        "/opt/vincent-installer/platform.tar.gz", "/opt/vincent-installer/payload-manifest.json",
        expected, build_path.read_text().strip()])
except Exception as exc:
    record("payload_exact_commit", False, repr(exc))

try:
    build = build_path.read_text().strip()
    record("build_number", bool(re.fullmatch(r"\d{4}(?:\.\d+)?", build)), build)
except Exception as exc:
    record("build_number", False, repr(exc))

try:
    account = pwd.getpwnam("vincent")
    record("service_account", account.pw_shell.endswith("nologin"), f"uid={account.pw_uid} home={account.pw_dir} shell={account.pw_shell}")
    supplementary = {group.gr_name for group in grp.getgrall() if "vincent" in group.gr_mem}
    primary = grp.getgrgid(account.pw_gid).gr_name
    groups = supplementary | {primary}
    record("no_root_equivalent_docker_group", "docker" not in groups, ",".join(sorted(groups)))
except KeyError:
    record("service_account", False, "vincent account missing")
    record("no_root_equivalent_docker_group", False, "vincent account missing")

human_accounts = [entry.pw_name for entry in pwd.getpwall() if 1000 <= entry.pw_uid < 60000]
record("no_human_login_accounts", not human_accounts, ",".join(human_accounts) or "none")
try:
    shadow = subprocess.run(["getent", "shadow", "root"], text=True, capture_output=True, check=True).stdout.split(":",2)[1]
    record("root_password_locked", shadow.startswith("!") or shadow.startswith("*"), shadow[:4])
except Exception as exc:
    record("root_password_locked", False, repr(exc))

request_path = Path("/var/lib/vincent/identity/enrollment-request.json")
try:
    request = json.loads(request_path.read_text())
    required = {"worker_id", "fingerprint", "public_key"}
    record("enrollment_request", required.issubset(request), request.get("worker_id", "missing worker_id"))
except Exception as exc:
    record("enrollment_request", False, repr(exc))

completed = subprocess.run(["systemctl", "is-enabled", "mission-control-worker.service"], text=True, capture_output=True)
record("worker_authority_disabled", completed.returncode != 0, (completed.stdout or completed.stderr).strip())

passed = all(item["ok"] for item in checks)
payload = {
    "schema_version": 1,
    "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "hostname": hostname,
    "overall": "PASS" if passed else "FAIL",
    "checks": checks,
}
report_path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
os.chmod(report_path, 0o600)
for item in checks:
    print(f"{item['name']}: {'PASS' if item['ok'] else 'FAIL'} {item['detail']}")
print(f"VINCENT_SELF_TEST={'PASS' if passed else 'FAIL'}")
sys.exit(0 if passed else 1)
PY
