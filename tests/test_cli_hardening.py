"""
Phase 3 — CLI hardening tests.

All tests run without a browser or behave subprocess.
"""
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from bddframe.cli import _normalize_headless, _find_behave_base, _VALID_BROWSERS


# ---------------------------------------------------------------------------
# Bug 1 — Non-canonical BDDFRAME_HEADLESS passthrough
# ---------------------------------------------------------------------------

class TestNormalizeHeadless:
    def test_canonical_true(self):
        assert _normalize_headless("true") == "true"

    def test_canonical_false(self):
        assert _normalize_headless("false") == "false"

    def test_truthy_1(self):
        assert _normalize_headless("1") == "true"

    def test_truthy_yes(self):
        assert _normalize_headless("yes") == "true"

    def test_truthy_on(self):
        assert _normalize_headless("on") == "true"

    def test_truthy_TRUE_uppercase(self):
        assert _normalize_headless("TRUE") == "true"

    def test_falsy_0(self):
        assert _normalize_headless("0") == "false"

    def test_falsy_no(self):
        assert _normalize_headless("no") == "false"

    def test_empty(self):
        assert _normalize_headless("") == "false"

    def test_whitespace_stripped(self):
        assert _normalize_headless("  true  ") == "true"


# ---------------------------------------------------------------------------
# Bug 2 — --headed and --headless mutual exclusion
# ---------------------------------------------------------------------------

class TestHeadedHeadlessMutualExclusion:
    def _invoke(self, headed=False, headless=False, browser="chromium"):
        """Call run() via the Typer test runner."""
        from typer.testing import CliRunner
        from bddframe.cli import app
        args = []
        if headed:
            args.append("--headed")
        if headless:
            args.append("--headless")
        args += ["--browser", browser]
        runner = CliRunner()
        return runner.invoke(app, ["run", *args])

    def test_both_flags_raises(self):
        result = self._invoke(headed=True, headless=True)
        assert result.exit_code != 0
        assert "--headed" in result.output or "mutually exclusive" in result.output

    def test_only_headed_ok(self):
        # Should not raise the mutual-exclusion error (subprocess will fail because
        # there's nothing to run, but the guard itself must not fire).
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = self._invoke(headed=True)
        assert "mutually exclusive" not in result.output

    def test_only_headless_ok(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = self._invoke(headless=True)
        assert "mutually exclusive" not in result.output


# ---------------------------------------------------------------------------
# Bug 4 (CLI side) — invalid browser name rejected at CLI layer
# ---------------------------------------------------------------------------

class TestBrowserValidation:
    def _invoke(self, browser):
        from typer.testing import CliRunner
        from bddframe.cli import app
        runner = CliRunner()
        return runner.invoke(app, ["run", "--browser", browser])

    def test_invalid_browser_chrome_rejected(self):
        result = self._invoke("chrome")
        assert result.exit_code != 0
        assert "chrome" in result.output.lower() or "unsupported" in result.output.lower()

    def test_invalid_browser_safari_rejected(self):
        result = self._invoke("safari")
        assert result.exit_code != 0

    def test_valid_browsers_accepted(self):
        for b in _VALID_BROWSERS:
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                result = self._invoke(b)
            assert "unsupported" not in result.output.lower(), f"Valid browser {b!r} was rejected"


# ---------------------------------------------------------------------------
# Bug 5 — _find_behave_base derives root from passed path
# ---------------------------------------------------------------------------

class TestFindBehaveBase:
    def test_finds_steps_dir(self, tmp_path):
        steps_dir = tmp_path / "features" / "steps"
        steps_dir.mkdir(parents=True)
        feature_file = tmp_path / "features" / "saucedemo" / "login.feature"
        feature_file.parent.mkdir(parents=True)
        feature_file.touch()

        base = _find_behave_base(feature_file)
        assert base == tmp_path / "features"

    def test_finds_environment_py(self, tmp_path):
        env_py = tmp_path / "tests" / "environment.py"
        env_py.parent.mkdir(parents=True)
        env_py.touch()
        feature_file = tmp_path / "tests" / "sub" / "checkout.feature"
        feature_file.parent.mkdir(parents=True)
        feature_file.touch()

        base = _find_behave_base(feature_file)
        assert base == tmp_path / "tests"

    def test_fallback_when_no_marker(self, tmp_path):
        feature_file = tmp_path / "orphan.feature"
        feature_file.touch()
        base = _find_behave_base(feature_file)
        assert base == Path("features")

    def test_env_var_headless_normalised_in_subprocess(self):
        """
        When BDDFRAME_HEADLESS=1 in the environment and neither flag is passed,
        the env dict sent to behave must contain 'true', not '1'.
        """
        from typer.testing import CliRunner
        from bddframe.cli import app
        captured_env = {}

        def fake_run(args, env=None):
            captured_env.update(env or {})
            return MagicMock(returncode=0)

        with patch.dict(os.environ, {"BDDFRAME_HEADLESS": "1"}):
            with patch("subprocess.run", side_effect=fake_run):
                runner = CliRunner()
                runner.invoke(app, ["run"])

        assert captured_env.get("BDDFRAME_HEADLESS") == "true"
