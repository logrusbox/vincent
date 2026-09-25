"""Operator-selected standalone scope and revocable managed execution grants."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from .models import Task, parse_created_at


class AuthorizationError(ValueError):
    pass


def repository_identity(value: str, *, local: bool = False) -> str:
    if not isinstance(value, str) or not value or any(c.isspace() for c in value):
        raise AuthorizationError('invalid repository identity')
    if value.startswith('/'):
        if not local:
            raise AuthorizationError('managed local repositories are not supported')
        path = Path(value)
        if any(item.is_symlink() for item in (path, *path.parents)):
            raise AuthorizationError('local repository scopes cannot use symbolic links')
        return str(path.resolve())
    if re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', value):
        value = 'https://github.com/' + value
    if value.startswith('git@'):
        match = re.fullmatch(r'git@([A-Za-z0-9.-]+):([^:]+)', value)
        if not match:
            raise AuthorizationError('invalid SSH repository identity')
        value = 'ssh://git@' + match[1] + '/' + match[2]
    parsed = urlsplit(value)
    if (parsed.scheme not in ('https', 'ssh') or not parsed.hostname
            or parsed.query or parsed.fragment or parsed.password
            or (parsed.username and not (parsed.scheme == 'ssh' and parsed.username == 'git'))
            or parsed.port is not None or '%' in parsed.path):
        raise AuthorizationError('unsupported repository identity')
    path = parsed.path.removesuffix('.git').strip('/')
    parts = path.split('/')
    if len(parts) != 2 or any(p in ('.', '..') or not re.fullmatch(r'[A-Za-z0-9_.-]+', p) for p in parts):
        raise AuthorizationError('repository must identify one exact owner/name')
    host = parsed.hostname.lower()
    return host + '/' + (path.lower() if host == 'github.com' else path)


def read_protected_grant(path: Path) -> dict:
    if not path.is_absolute():
        raise AuthorizationError('managed grant path must be absolute')
    for item in (path, *path.parents):
        info = item.lstat()
        if item.is_symlink() or info.st_uid != 0 or info.st_mode & 0o022:
            raise AuthorizationError('managed grant and parent directories must be root-owned and not writable by workers')
    return json.loads(path.read_text())


@dataclass(frozen=True)
class ExecutionAuthority:
    worker_id: str
    mode: str
    repositories: tuple[str, ...] = ()
    grant_path: Path | None = None

    def require(self, task: Task) -> None:
        try:
            if self.mode == 'standalone':
                allowed = self.repositories
            elif self.mode == 'managed':
                if self.grant_path is None:
                    raise AuthorizationError('managed grant is missing')
                grant = read_protected_grant(self.grant_path)
                if (type(grant.get('schema_version')) is not int or grant['schema_version'] != 1
                        or grant.get('worker_id') != self.worker_id or grant.get('status') != 'active'):
                    raise AuthorizationError('managed grant is invalid, revoked, or belongs to another worker')
                expiry = parse_created_at(grant.get('expires_at'))
                if expiry <= datetime.now(timezone.utc):
                    raise AuthorizationError('managed grant expired')
                allowed = grant.get('repository_scopes')
                if not isinstance(allowed, list) or not allowed:
                    raise AuthorizationError('managed repository scopes are missing')
            else:
                raise AuthorizationError('explicit standalone or managed authority is required')
            target = repository_identity(task.repository, local=self.mode == 'standalone')
            identities = {repository_identity(item, local=self.mode == 'standalone') for item in allowed}
            if target not in identities:
                raise AuthorizationError('task repository is outside authorized scope')
        except (OSError, TypeError, ValueError) as exc:
            if isinstance(exc, AuthorizationError):
                raise
            raise AuthorizationError('execution authority could not be verified') from exc
