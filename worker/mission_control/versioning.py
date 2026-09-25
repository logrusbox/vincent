"""Runtime identity and immutable installer provenance are independent facts."""
import json
from importlib.resources import files
from pathlib import Path


def version_info(installer_manifest=Path('/opt/vincent-installer/payload-manifest.json')):
    packaged = files('mission_control').joinpath('runtime-build.json')
    if packaged.is_file():
        runtime = json.loads(packaged.read_text())
    else:
        source = Path(__file__).resolve().parents[2]
        runtime = {'version': (source/'VERSION').read_text().strip(),
                   'build': (source/'BUILD_NUMBER').read_text().strip()}
    installer = None
    if installer_manifest.is_file():
        metadata = json.loads(installer_manifest.read_text())
        installer = {'version': metadata.get('installer_version'),
                     'build': metadata.get('installer_build'),
                     'source_commit': metadata.get('platform_commit'),
                     'original_runtime_version': metadata.get('runtime_version'),
                     'original_runtime_build': metadata.get('runtime_build')}
    return {'runtime': runtime, 'installer': installer}
