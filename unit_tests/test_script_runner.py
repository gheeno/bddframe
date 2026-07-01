import sys

import pytest

from noodle.orchestrator import script_runner
from noodle.resolver.step_resolver import resolve


def test_command_for_infers_interpreter_by_extension():
    assert script_runner.command_for("x.py", None) == [sys.executable, "x.py"]
    assert script_runner.command_for("x.js", None) == ["node", "x.js"]
    assert script_runner.command_for("tool.jar", None) == ["java", "-jar", "tool.jar"]


def test_command_for_unknown_ext_runs_directly():
    assert script_runner.command_for("./run", None) == ["./run"]


def test_command_for_splits_args():
    assert script_runner.command_for("x.py", "--flag val") == [sys.executable, "x.py", "--flag", "val"]


def test_run_script_returns_stdout(tmp_path):
    s = tmp_path / "hi.py"
    s.write_text("print('hello from script')")
    assert script_runner.run_script(str(s)) == "hello from script"


def test_run_script_nonzero_exit_raises(tmp_path):
    s = tmp_path / "boom.py"
    s.write_text("import sys; sys.exit(3)")
    with pytest.raises(AssertionError):
        script_runner.run_script(str(s))


def test_run_script_missing_file_raises():
    with pytest.raises(AssertionError):
        script_runner.run_script("nope/does_not_exist.py")


def test_resolver_matches_run_script_phrasings():
    assert resolve('runs the script "x.py"')['type'] == 'run_script'
    assert resolve('script "x.py" executes')['type'] == 'run_script'
    got = resolve('runs the script "x.py" with "--a b" storing the output as `RESULT`')
    assert got == {'type': 'run_script', 'path': 'x.py', 'args': '--a b', 'var': 'RESULT'}
    assert resolve('runs the command "ls -la"') == {'type': 'run_command', 'command': 'ls -la', 'var': None}
