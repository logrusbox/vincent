"""Verify the trusted installer's bundled source before any source code executes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tarfile
import tempfile


def verify(bundle: Path, manifest: Path, commit: str, build: str) -> dict:
    metadata = json.loads(manifest.read_text())
    if (metadata.get("schema_version") != 1
            or not re.fullmatch(r"[0-9a-f]{40}", commit)
            or metadata.get("platform_commit") != commit
            or metadata.get("installer_build") != build):
        raise ValueError("bundled payload provenance mismatch")
    with bundle.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    if digest != metadata.get("sha256"):
        raise ValueError("bundled payload checksum mismatch")
    with tarfile.open(bundle, "r:gz") as archive:
        if archive.pax_headers.get("comment") != commit:
            raise ValueError("Git archive commit does not match installer provenance")
        seen = set()
        for member in archive.getmembers():
            path = PurePosixPath(member.name)
            if (path.is_absolute() or ".." in path.parts or member.name in seen
                    or not path.parts or not (member.isdir() or member.isfile())):
                raise ValueError("unsupported or unsafe payload member")
            seen.add(member.name)
        for name, key in (("VERSION", "runtime_version"), ("BUILD_NUMBER", "runtime_build")):
            stream = archive.extractfile(name)
            if stream is None or stream.read().decode().strip() != metadata.get(key):
                raise ValueError("runtime identity does not match payload manifest")
    return metadata


def unpack(bundle: Path, manifest: Path, commit: str, build: str, destination: Path) -> dict:
    metadata = verify(bundle, manifest, commit, build)
    if destination.is_symlink():
        raise ValueError("source destination must not be a symlink")
    with tarfile.open(bundle, "r:gz") as archive:
        if destination.exists():
            # A resumed pip build may have added build/egg-info files. Never
            # replace an existing checkout or discard modified source.
            for member in archive.getmembers():
                target = destination / member.name
                if any(parent.is_symlink() for parent in (target, *target.parents)):
                    raise ValueError("existing source contains a symlink")
                if member.isdir():
                    if not target.is_dir():
                        raise ValueError("existing source directory mismatch")
                elif not target.is_file() or target.read_bytes() != archive.extractfile(member).read():
                    raise ValueError("existing source differs; preserved for explicit recovery")
            return metadata
        destination.parent.mkdir(parents=True, exist_ok=True)
        staged = Path(tempfile.mkdtemp(prefix=".vincent-payload-", dir=destination.parent))
        try:
            for member in archive.getmembers():
                target = staged / member.name
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with target.open("xb") as output:
                        shutil.copyfileobj(archive.extractfile(member), output)
                    target.chmod(0o755 if member.mode & 0o111 else 0o644)
            os.rename(staged, destination)
        finally:
            if staged.exists():
                shutil.rmtree(staged)
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("commit")
    parser.add_argument("build")
    parser.add_argument("--destination", type=Path)
    args = parser.parse_args()
    if args.destination:
        metadata = unpack(args.bundle, args.manifest, args.commit, args.build, args.destination)
    else:
        metadata = verify(args.bundle, args.manifest, args.commit, args.build)
    print(json.dumps(metadata, sort_keys=True))


if __name__ == "__main__":
    main()
