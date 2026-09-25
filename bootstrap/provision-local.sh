#!/bin/sh
# Configure dependencies already installed from the authenticated Debian bundle.
set -eu
service_user=vincent
service_home=/var/lib/vincent
service_runtime=/run/vincent
install -d -o root -g "$service_user" -m 0750 /var/lib/vincent-install
install -d -o "$service_user" -g "$service_user" -m 0700 "$service_runtime"
# Allocate one unused range across both files. Never overlap a pre-existing
# subordinate range belonging to another principal.
subordinate_start=$(python3 - <<'PYRANGE'
from pathlib import Path
ranges = []
for name in ('subuid', 'subgid'):
    for line in Path('/etc/' + name).read_text().splitlines():
        owner, start, count = line.split(':')
        ranges.append((int(start), int(start) + int(count)))
start = 100000
while any(start < end and start + 65536 > begin for begin, end in ranges):
    start += 65536
if start + 65536 > 2**32 - 1:
    raise SystemExit('no safe subordinate identity range available')
print(start)
PYRANGE
)
subordinate_end=$((subordinate_start+65535))
if ! grep -q "^${service_user}:" /etc/subuid; then
    usermod --add-subuids "$subordinate_start-$subordinate_end" "$service_user"
fi
if ! grep -q "^${service_user}:" /etc/subgid; then
    usermod --add-subgids "$subordinate_start-$subordinate_end" "$service_user"
fi
systemctl enable --now NetworkManager
systemctl start vincent-container-namespace.service
