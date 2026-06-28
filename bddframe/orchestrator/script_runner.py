"""Run an external script or shell command as a Gherkin step.

Lets a scenario invoke a user-authored script in any language — seed a database
with Python, run a Java jar, call a shell tool — and use its result downstream.
The interpreter is inferred from the file extension; stdout is captured and
returned (the runner stores it in `SCRIPT_OUTPUT`). A non-zero exit fails the
step, so a broken setup script fails the test loudly.

Trust boundary: feature files are trusted code (like step definitions), so
run_command uses a shell. Don't drive these steps from untrusted input.
"""
import os
import shlex
import subprocess
import sys
from pathlib import Path

# Extension → command prefix. .py uses THIS interpreter (venv-aware); others use
# the conventional launcher on PATH. ponytail: extend this dict for new languages.
_INTERPRETERS = {
    ".py": [sys.executable],
    ".js": ["node"],
    ".mjs": ["node"],
    ".jar": ["java", "-jar"],
    ".sh": ["bash"],
    ".rb": ["ruby"],
    ".pl": ["perl"],
}


def command_for(path: str, args: str | None) -> list[str]:
    """Build the argv for a script path, inferring the interpreter by extension.
    Unknown extension → run the file directly (must be executable)."""
    ext = Path(path).suffix.lower()
    prefix = _INTERPRETERS.get(ext, [])
    extra = shlex.split(args) if args else []
    return [*prefix, path, *extra]


def _run(cmd, *, shell: bool, label: str) -> str:
    timeout = int(os.getenv("BDDFRAME_SCRIPT_TIMEOUT", "60"))
    result = subprocess.run(
        cmd, shell=shell, capture_output=True, text=True,
        cwd=Path.cwd(), timeout=timeout, env=os.environ,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"{label} failed (exit {result.returncode})\n"
            f"  stderr: {result.stderr.strip()}\n"
            f"  stdout: {result.stdout.strip()}"
        )
    return result.stdout.strip()


def run_script(path: str, args: str | None = None) -> str:
    if not Path(path).exists():
        raise AssertionError(f"Script not found: {path} (cwd: {Path.cwd()})")
    return _run(command_for(path, args), shell=False, label=f"Script '{path}'")


def run_command(command: str) -> str:
    return _run(command, shell=True, label=f"Command '{command}'")
