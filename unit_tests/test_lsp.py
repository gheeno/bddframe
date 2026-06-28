"""
Phase 7 — LSP server unit tests.

Tests the validation logic and completion helpers directly without
spinning up a real language server process.
"""
import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# _validate — step diagnostics
# ---------------------------------------------------------------------------

class TestValidate:
    def _validate(self, source):
        from bddframe.lsp.server import _validate
        return _validate(source)

    def test_no_diagnostics_for_known_step(self):
        source = 'Given User is on "https://example.com"'
        diags = self._validate(source)
        assert diags == []

    def test_unknown_step_produces_diagnostic(self):
        source = "When User performs a totally unknown action"
        diags = self._validate(source)
        assert len(diags) == 1
        assert "llm-fallback" in diags[0].code

    def test_diagnostic_points_to_correct_line(self):
        source = "\n".join([
            'Feature: Demo',
            '',
            '  Scenario: test',
            '    Given User is on "https://example.com"',
            '    When User does something unknown',
        ])
        diags = self._validate(source)
        assert len(diags) == 1
        assert diags[0].range.start.line == 4

    def test_no_diagnostic_for_non_step_lines(self):
        source = "\n".join([
            "Feature: Guest Checkout",
            "",
            "  @web @smoke",
            "  Scenario: A scenario",
            "    # just a comment",
        ])
        diags = self._validate(source)
        assert diags == []

    def test_multiple_unknown_steps_all_flagged(self):
        source = "\n".join([
            "    Given User frobnicates the widget",
            "    When User performs the quux",
            "    Then User should see some results",  # this one is known
        ])
        diags = self._validate(source)
        assert len(diags) == 2

    def test_severity_none_suppresses_diagnostics(self):
        from lsprotocol import types as lsp
        source = "When User does something unknown"
        import bddframe.lsp.server as srv
        original = srv._UNKNOWN_STEP_SEVERITY
        try:
            srv._UNKNOWN_STEP_SEVERITY = None
            diags = srv._validate(source)
        finally:
            srv._UNKNOWN_STEP_SEVERITY = original
        assert diags == []

    def test_step_keyword_and_variants_recognised(self):
        """Given/When/Then/And/But all trigger step validation."""
        known_step = 'User is on "https://example.com"'
        for kw in ("Given", "When", "Then", "And", "But"):
            diags = self._validate(f"    {kw} {known_step}")
            assert diags == [], f"keyword {kw!r} produced unexpected diagnostics"


# ---------------------------------------------------------------------------
# KNOWN_TAGS — completeness check
# ---------------------------------------------------------------------------

class TestKnownTags:
    def test_headed_tag_present(self):
        from bddframe.lsp.server import KNOWN_TAGS
        tags = [t for t, _ in KNOWN_TAGS]
        assert "headed" in tags

    def test_headless_tag_present(self):
        from bddframe.lsp.server import KNOWN_TAGS
        tags = [t for t, _ in KNOWN_TAGS]
        assert "headless" in tags

    def test_slow_tag_present(self):
        from bddframe.lsp.server import KNOWN_TAGS
        tags = [t for t, _ in KNOWN_TAGS]
        assert "slow" in tags

    def test_record_video_tag_present(self):
        from bddframe.lsp.server import KNOWN_TAGS
        tags = [t for t, _ in KNOWN_TAGS]
        assert "record_video" in tags

    def test_no_duplicate_tags(self):
        from bddframe.lsp.server import KNOWN_TAGS
        tags = [t for t, _ in KNOWN_TAGS]
        assert len(tags) == len(set(tags)), "Duplicate tag entries in KNOWN_TAGS"


# ---------------------------------------------------------------------------
# _env_var_names — variable completion helper
# ---------------------------------------------------------------------------

class TestEnvVarNames:
    def test_returns_variable_names_from_env_file(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("MY_EMAIL=test@example.com\nSAUCE_USERNAME=standard_user\n")
        feature = tmp_path / "features" / "login.feature"
        feature.parent.mkdir()
        feature.touch()

        from bddframe.lsp.server import _env_var_names
        names = _env_var_names(str(feature))

        assert "MY_EMAIL" in names
        assert "SAUCE_USERNAME" in names

    def test_returns_lowercase_alternatives(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("MY_EMAIL=test@example.com\n")
        feature = tmp_path / "feature.feature"
        feature.touch()

        from bddframe.lsp.server import _env_var_names
        names = _env_var_names(str(feature))

        assert "my email" in names

    def test_ignores_comments_and_blank_lines(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("# comment\n\nVALID_VAR=1\n")
        feature = tmp_path / "f.feature"
        feature.touch()

        from bddframe.lsp.server import _env_var_names
        names = _env_var_names(str(feature))

        comment_names = [n for n in names if "comment" in n]
        assert comment_names == []
        assert "VALID_VAR" in names

    def test_returns_empty_list_when_no_env_file(self, tmp_path):
        feature = tmp_path / "f.feature"
        feature.touch()

        from bddframe.lsp.server import _env_var_names
        names = _env_var_names(str(feature))

        assert names == []

    def test_walks_up_to_find_env(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("ROOT_VAR=1\n")
        nested = tmp_path / "a" / "b" / "c.feature"
        nested.parent.mkdir(parents=True)
        nested.touch()

        from bddframe.lsp.server import _env_var_names
        names = _env_var_names(str(nested))

        assert "ROOT_VAR" in names
