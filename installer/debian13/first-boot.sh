#!/bin/sh
set -eu

log_file=/var/log/vincent/bootstrap.log
status_file=/var/lib/vincent-install/status.json
bootstrap_state=/var/lib/vincent-install/bootstrap-state.json
expected_commit_file=/opt/vincent-installer/expected-commit
build_number_file=/opt/vincent-installer/build-number
source_root=/opt/vincent/source
self_test=/usr/local/sbin/vincent-self-test
network_attempts=20
network_delay=15

install -d -m 0750 /var/log/vincent /etc/vincent
install -d -m 0700 /var/lib/vincent-install
exec >>"$log_file" 2>&1

write_status() {
    state=$1; step=$2; detail=$3; attempt=${4:-0}; maximum=${5:-0}
    route=$(ip route show default 2>/dev/null | head -n1 || true)
    addresses=$(hostname -I 2>/dev/null | xargs || true)
    dns=fail; getent ahosts github.com >/dev/null 2>&1 && dns=pass
    python3 - "$status_file" "$state" "$step" "$detail" "$attempt" "$maximum" "$route" "$addresses" "$dns" <<'PY'
import json, socket, sys
from datetime import datetime, timezone
from pathlib import Path
path, state, step, detail, attempt, maximum, route, addresses, dns = sys.argv[1:]
Path(path).write_text(json.dumps({"schema_version":1,"state":state,"step":step,"detail":detail,"hostname":socket.gethostname(),"attempt":int(attempt),"max_attempts":int(maximum),"default_route":route,"ip_addresses":addresses,"github_dns":dns,"timestamp":datetime.now(timezone.utc).isoformat().replace("+00:00","Z")}, sort_keys=True, indent=2)+"\n")
PY
    chmod 0600 "$status_file"
}

write_bootstrap_state() {
    phase=$1
    python3 - "$bootstrap_state" "$phase" "$expected_commit" "$build_number" <<'PY'
import json, sys
from datetime import datetime, timezone
from pathlib import Path
path, phase, commit, build = sys.argv[1:]
Path(path).write_text(json.dumps({"schema_version":1,"phase":phase,"platform_commit":commit,"build_number":build,"updated_at":datetime.now(timezone.utc).isoformat().replace("+00:00","Z")}, sort_keys=True, indent=2)+"\n")
PY
    chmod 0600 "$bootstrap_state"
}

trap 'code=$?; if [ "$code" -ne 0 ]; then write_status FAILED bootstrap "bootstrap or self-test failed; see live output"; fi' EXIT

for file in "$expected_commit_file" "$build_number_file"; do
    [ -s "$file" ] || { write_status FAILED metadata "required installer metadata missing: $file"; exit 1; }
done
expected_commit=$(tr -d '\r\n' <"$expected_commit_file")
build_number=$(tr -d '\r\n' <"$build_number_file")
printf '%s\n' "$build_number" | grep -Eq '^[0-9]{4}(\.[0-9]+)?$' || { write_status FAILED metadata "invalid build number"; exit 1; }
printf '%s\n' "$expected_commit" >/etc/vincent/build-commit
printf '%s\n' "$build_number" >/etc/vincent/build-number
chmod 0644 /etc/vincent/build-commit /etc/vincent/build-number

resume_identity=0
if [ -s "$bootstrap_state" ]; then
    python3 - "$bootstrap_state" "$expected_commit" "$build_number" <<'PY'
import json, sys
from pathlib import Path
state=json.loads(Path(sys.argv[1]).read_text())
if state.get("platform_commit") != sys.argv[2] or state.get("build_number") != sys.argv[3]:
    raise SystemExit("bootstrap state belongs to a different Vincent image")
PY
    resume_identity=1
    echo "resuming interrupted first boot for build $build_number"
else
    write_bootstrap_state in_progress
fi

machine_identity=$(cat /sys/class/dmi/id/product_uuid 2>/dev/null || cat /etc/machine-id)
vincent_hostname=$(python3 - "$machine_identity" <<'PY'
import hashlib, sys
value=int.from_bytes(hashlib.sha256(sys.argv[1].strip().encode()).digest()[:8],"big")%1_000_000
print(f"vincent-worker-{value:06d}")
PY
)
hostnamectl set-hostname "$vincent_hostname"
python3 - "$vincent_hostname" <<'PY'
import re, sys
from pathlib import Path
hostname=sys.argv[1]; path=Path('/etc/hosts'); text=path.read_text(); line=f"127.0.1.1\t{hostname}"
text=re.sub(r"^127\.0\.1\.1\s+.*$",line,text,flags=re.MULTILINE) if re.search(r"^127\.0\.1\.1\s+.*$",text,flags=re.MULTILINE) else text+("" if text.endswith("\n") else "\n")+line+"\n"
path.write_text(text)
PY


write_status BOOTSTRAPPING payload "verifying embedded Vincent payload"
python3 /opt/vincent-installer/payload.py \
    /opt/vincent-installer/platform.tar.gz /opt/vincent-installer/payload-manifest.json \
    "$expected_commit" "$build_number" --destination "$source_root"
write_status BOOTSTRAPPING platform "installing Vincent from verified embedded payload"
VINCENT_RESUME_IDENTITY=$resume_identity sh "$source_root/installer/install.sh" "$source_root"
printf '%s\n' "$expected_commit" >/var/lib/vincent-install/installed-commit
chmod 0600 /var/lib/vincent-install/installed-commit

attempt=1
while [ "$attempt" -le "$network_attempts" ]; do
    write_status BOOTSTRAPPING network "waiting for route, DNS and HTTPS to GitHub" "$attempt" "$network_attempts"
    route_ok=false; dns_ok=false; https_ok=false
    ip route show default >/dev/null 2>&1 && route_ok=true
    getent ahosts github.com >/dev/null 2>&1 && dns_ok=true
    curl --fail --silent --show-error --head --connect-timeout 5 --max-time 10 https://github.com/ >/dev/null 2>&1 && https_ok=true
    echo "network attempt $attempt/$network_attempts route=$route_ok dns=$dns_ok https=$https_ok"
    [ "$route_ok" = true ] && [ "$dns_ok" = true ] && [ "$https_ok" = true ] && break
    [ "$attempt" -lt "$network_attempts" ] || { write_status FAILED network "network did not become ready" "$attempt" "$network_attempts"; exit 1; }
    sleep "$network_delay"; attempt=$((attempt+1))
done

write_status BOOTSTRAPPING toolchain "installing and validating worker toolchain"
sh "$source_root/bootstrap/provision-worker-baseline.sh"

write_status SELF_TESTING self-test "running unattended Vincent appliance validation"
"$self_test"
systemctl start vincent-diagnostics.service >/dev/null 2>&1 || true
write_bootstrap_state completed
write_status ENROLLMENT_REQUIRED ready "build $build_number self-test passed; approve scoped enrollment remotely"
systemctl disable vincent-first-boot.service
