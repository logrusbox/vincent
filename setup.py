"""Embed the canonical runtime identity into every wheel without altering source."""
import json
from pathlib import Path
from setuptools import setup
from setuptools.command.build_py import build_py

class BuildWithIdentity(build_py):
    def run(self):
        super().run()
        root = Path(__file__).parent
        target = Path(self.build_lib) / 'mission_control' / 'runtime-build.json'
        target.write_text(json.dumps({'version': (root/'VERSION').read_text().strip(),
                                      'build': (root/'BUILD_NUMBER').read_text().strip()}) + '\n')

setup(cmdclass={'build_py': BuildWithIdentity})
