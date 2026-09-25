#!/bin/sh
set -eu

status_file=/var/lib/vincent-install/status.json
report_file=/var/lib/vincent-install/self-test.json
enrollment_file=/var/lib/vincent/identity/enrollment-request.json
log_file=/var/log/vincent/bootstrap.log
expected_commit_file=/etc/vincent/build-commit
build_number_file=/etc/vincent/build-number

render() {
    python3 - "$status_file" "$report_file" "$enrollment_file" "$log_file" "$expected_commit_file" "$build_number_file" <<'PY'
import json, shutil, sys
from pathlib import Path

status_path, report_path, enrollment_path, log_path, expected_path, build_path = map(Path, sys.argv[1:])

def read_json(path):
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}

status = read_json(status_path)
report = read_json(report_path)
enrollment = read_json(enrollment_path)
try: expected_commit = expected_path.read_text().strip()
except Exception: expected_commit = "unknown"
try: build_number = build_path.read_text().strip()
except Exception: build_number = "unknown"

state = status.get("state", "BOOTSTRAPPING")
step = status.get("step", "starting")
overall = report.get("overall", "PENDING")
if state == "FAILED": overall = "FAIL"
hostname = status.get("hostname", report.get("hostname", "vincent-worker"))
fingerprint = enrollment.get("fingerprint", "pending")
worker_id = enrollment.get("worker_id", "pending")
checks = report.get("checks", [])
failed = [item for item in checks if not item.get("ok")]
width = max(80, shutil.get_terminal_size((120, 40)).columns)
height = max(24, shutil.get_terminal_size((120, 40)).lines)

def clipped(value, n):
    return str(value).replace("\n", " ")[:max(0, n)]

last_error = ""
if state == "FAILED":
    last_error = status.get("detail", "")
    if not last_error and failed:
        last_error = f"{failed[0].get('name')}: {failed[0].get('detail', '')}"

print("\033[2J\033[H", end="")
print("VINCENT WORKER")
print("=" * min(width, 100))
print(f"BUILD: {build_number:<12} STATE: {state:<20} OVERALL: {overall:<8}")
print(f"CURRENT TASK: {step}")
print(f"HOSTNAME: {hostname:<28} WORKER ID: {worker_id}")
print(f"FINGERPRINT: {fingerprint}")
print(f"SOURCE COMMIT: {expected_commit}")
print(f"IP: {status.get('ip_addresses') or 'pending'}")
print(f"ROUTE: {status.get('default_route') or 'pending'}")
print(f"GITHUB DNS: {status.get('github_dns', 'pending')}")
if status.get("max_attempts"):
    print(f"RETRY: {status.get('attempt',0)}/{status.get('max_attempts',0)}")
if last_error:
    print(f"LAST ERROR: {clipped(last_error, width-12)}")
print("-" * min(width, 100))

if checks:
    print("SELF-TEST STATUS")
    for item in checks[:10]:
        result = "PASS" if item.get("ok") else "FAIL"
        print(f"{item.get('name','unknown'):<28} {result:<4} {clipped(item.get('detail',''), width-40)}")
    print("-" * min(width, 100))

if state == "READY" and overall == "PASS":
    print("READY / UNASSIGNED — optional provider setup and CIC Station enrollment")
elif state == "FAILED" or overall == "FAIL":
    print("INSTALLATION / SELF-TEST FAILURE — photograph this screen")
else:
    print("Vincent is provisioning and testing itself.")
print("Alt+F1: dashboard | Alt+F2: Codex | Alt+F3: network config | Alt+F4: diagnostics")
print("-" * min(width, 100))
print("LIVE WORK OUTPUT")

reserved = 17 + min(len(checks), 10)
log_lines = max(8, height - reserved)
try: lines = log_path.read_text(errors="replace").splitlines()
except Exception: lines = []
for line in lines[-log_lines:]:
    print(line[:width])
PY
}

while :; do
    render
    sleep 2
done
