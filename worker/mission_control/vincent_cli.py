"""Local Vincent status and explicit enrollment; no implicit online bootstrap."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

IDENTITY_ROOT = Path('/var/lib/vincent/identity')
READY_RECORD = Path('/var/lib/vincent/ready.json')
AUTHORIZATION = Path('/etc/vincent/authorization.json')


def local_status(identity_root: Path = IDENTITY_ROOT, ready_record: Path = READY_RECORD) -> dict:
    identity = json.loads((identity_root / 'identity.json').read_text())
    if identity.get('schema_version') != 1 or not identity.get('worker_id'):
        raise ValueError('invalid local worker identity')
    try:
        ready = json.loads(ready_record.read_text())
    except FileNotFoundError:
        ready = {}
    passed = (ready.get('schema_version') == 1 and ready.get('state') == 'READY'
              and ready.get('worker_id') == identity['worker_id'])
    return {
        'schema_version': 1, 'worker_id': identity['worker_id'],
        'local_state': 'READY' if passed else 'SETUP_REQUIRED',
        'last_local_self_test': ready.get('verified_at'),
        'provider_available': shutil.which('codex') is not None,
        'managed_authority': 'not_evaluated',
        'detail': 'Local readiness does not grant project or managed execution authority.',
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog='vincent')
    parser.add_argument('command', choices=('status', 'enroll'), nargs='?', default='status')
    arguments = parser.parse_args(argv)
    try:
        if arguments.command == 'enroll':
            from .enrollment import request_enrollment
            print(request_enrollment(IDENTITY_ROOT).to_json(), end='')
            return 0
        status = local_status(IDENTITY_ROOT, READY_RECORD)
        print(json.dumps(status, sort_keys=True, indent=2))
        return 0 if status['local_state'] == 'READY' else 10
    except (OSError, RuntimeError, ValueError) as exc:
        print(f'Vincent: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
