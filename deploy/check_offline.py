"""Sequential offline gates; uses installed dependencies, never starts Docker."""
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
npm = shutil.which('npm.cmd') or shutil.which('npm')
node = shutil.which('node')
if not npm or not node:
    raise SystemExit('Node.js and npm are required; install dependencies before running.')
commands = [
    [node, '--test', 'tests/web/state.test.mjs'],
    [sys.executable, '-m', 'pytest', '-q', '--confcutdir=tests/evaluation', 'tests/evaluation'],
    [sys.executable, '-m', 'pytest', '-q', '--confcutdir=tests/assistant', 'tests/assistant'],
    [sys.executable, '-m', 'pytest', '-q', '--confcutdir=tests/worker', 'tests/worker'],
    [sys.executable, '-m', 'pytest', '-q', '--confcutdir=tests/reliability', 'tests/reliability'],
    [npm, 'run', 'build', '--prefix', 'client'],
    [node, '--test', 'client/tests/assistant.test.mjs'],
    [npm, 'run', 'build', '--prefix', 'mcp-server'],
    [npm, 'test', '--prefix', 'mcp-server'],
]
for command in commands:
    print('Running: ' + ' '.join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)
print('Offline gates passed. Docker, live providers and model inference were not run.')
