#!/usr/bin/env python3
"""Install reviewed local Codex artifacts; never download or execute installation code."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

NAMES = ('codex', 'codex-code-mode-host')


def install(manifest_path: Path, destination: Path) -> Path:
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    if (type(manifest.get('schema_version')) is not int or manifest['schema_version'] != 1
            or manifest.get('provider') != 'codex' or not isinstance(manifest.get('version'), str)
            or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', manifest['version'])
            or set(manifest.get('artifacts', {})) != set(NAMES)):
        raise ValueError('reviewed versioned Codex manifest required')
    # Caller controls trust in the expected digest. A hash recorded after a download
    # is not an independently reviewed expected hash.
    identity = hashlib.sha256(manifest_bytes).hexdigest()
    destination.mkdir(parents=True, exist_ok=True)
    if destination.is_symlink():
        raise ValueError('provider destination cannot be a symlink')
    with tempfile.TemporaryDirectory(prefix='.provider-', dir=destination) as temporary:
        stage = Path(temporary)
        for name in NAMES:
            artifact = manifest['artifacts'][name]
            digest = artifact.get('sha256', '')
            if not isinstance(digest, str) or not re.fullmatch(r'[a-f0-9]{64}', digest):
                raise ValueError('expected SHA256 required for ' + name)
            source = Path(artifact['path'])
            if not source.is_absolute() or not source.is_file():
                raise ValueError('absolute local artifact file required')
            # Verify the staged bytes; replacing the source during copying cannot
            # cause installation of bytes different from the approved digest.
            shutil.copyfile(source, stage / name)
            with (stage / name).open('rb') as stream:
                actual = hashlib.file_digest(stream, 'sha256').hexdigest()
            if actual != digest:
                raise ValueError('artifact checksum mismatch: ' + name)
            (stage / name).chmod(0o755)
        (stage / 'manifest.json').write_bytes(manifest_bytes)
        (stage / 'manifest.json').chmod(0o644)
        release = destination / identity
        if release.exists():
            if release.is_symlink() or (release / 'manifest.json').read_bytes() != manifest_bytes:
                raise ValueError('existing provider release differs')
            for name in NAMES:
                with (release / name).open('rb') as stream:
                    if (release / name).is_symlink() or hashlib.file_digest(stream, 'sha256').hexdigest() != manifest['artifacts'][name]['sha256']:
                        raise ValueError('existing provider release differs')
        else:
            stage.chmod(0o755)
            os.rename(stage, release)
        link = destination / ('.current-' + str(os.getpid()))
        try:
            link.symlink_to(identity)
            os.replace(link, destination / 'bin')
        finally:
            link.unlink(missing_ok=True)
    return release


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--destination', type=Path, default=Path('/opt/vincent-codex'))
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error('operator root installation required')
    for path in (args.manifest, args.destination):
        if not path.is_absolute():
            parser.error('absolute protected paths required')
        for item in (path, *path.parents):
            if not item.exists():
                continue
            info = item.lstat()
            if item.is_symlink() or info.st_uid != 0 or info.st_mode & 0o022:
                parser.error('manifest and destination parents must be root-owned and not group/world writable')
    print(install(args.manifest, args.destination))
