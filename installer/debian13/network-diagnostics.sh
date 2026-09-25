#!/bin/sh
set -u

report=${1:-/var/lib/vincent-install/network-diagnostics.log}
install -d -m 0700 "$(dirname -- "$report")"

http_probe() {
    label=$1
    url=$2
    code=$(curl --silent --show-error --location --output /dev/null --write-out '%{http_code}' \
        --connect-timeout 10 --max-time 20 "$url" 2>/dev/null || printf '000')
    case "$code" in
        2??|3??) result=PASS ;;
        000) result=FAIL_TRANSPORT ;;
        *) result=HTTP_RESPONSE ;;
    esac
    printf '%-18s %-16s HTTP=%s %s\n' "$label" "$result" "$code" "$url"
}

{
    echo "===== VINCENT NETWORK DIAGNOSTICS ====="
    date -Is
    echo
    echo "===== NIC STATE ====="
    nmcli -f DEVICE,TYPE,STATE,CONNECTION device status 2>&1 || true
    echo
    echo "===== ADDRESSES ====="
    ip -brief address 2>&1 || true
    echo
    echo "===== ROUTES ====="
    ip route 2>&1 || true
    echo
    echo "===== WIFI RADIO ====="
    nmcli radio wifi 2>&1 || true
    echo
    echo "===== WIFI ASSOCIATION ====="
    nmcli -f GENERAL.DEVICE,GENERAL.TYPE,GENERAL.STATE,GENERAL.CONNECTION,IP4.ADDRESS,IP4.GATEWAY device show 2>&1 || true
    echo
    echo "===== DNS ====="
    for host in deb.debian.org github.com chatgpt.com; do
        printf '%s: ' "$host"
        getent ahostsv4 "$host" 2>/dev/null | awk 'NR==1 {print $1; found=1} END {if (!found) print "FAIL"}'
    done
    echo
    echo "===== OPTIONAL CONNECTIVITY ENDPOINTS ====="
    http_probe "debian-index" "https://deb.debian.org/debian/dists/trixie/InRelease"
    if git ls-remote https://github.com/logrusbox/vincent.git HEAD >/dev/null 2>&1; then
        echo "vincent-git        PASS             https://github.com/logrusbox/vincent.git"
    else
        echo "vincent-git        FAIL             https://github.com/logrusbox/vincent.git"
    fi
    echo
    echo "===== DEBIAN PACKAGE VISIBILITY ====="
    for package in git curl ca-certificates rsync python3-venv python3-pip python3-setuptools build-essential xz-utils podman podman-docker uidmap; do
        candidate=$(apt-cache policy "$package" 2>/dev/null | awk '/Candidate:/ {print $2; exit}')
        [ -n "$candidate" ] || candidate=UNKNOWN
        printf '%s candidate=%s\n' "$package" "$candidate"
    done
} | tee "$report"

chmod 0600 "$report"
