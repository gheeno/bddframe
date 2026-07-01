"""BFRAME_0035 — agent + workspace self-checks. No browser, no LLM, no network."""
import json

from noodle import config
from noodle.agent import generate, repl
from noodle.reporting import summary


def test_config_defaults_and_override(tmp_path):
    assert config.load(str(tmp_path))["features_dir"] == "features"
    (tmp_path / "noodle.yaml").write_text("features_dir: tests\nheadless: true\n")
    cfg = config.load(str(tmp_path))
    assert cfg["features_dir"] == "tests"
    assert cfg["headless"] is True
    assert cfg["browser"] == "chromium"  # unspecified key keeps default


def test_template_pick():
    assert generate.pick_template("login page") is generate._LOGIN
    assert generate.pick_template("search the catalog") is generate._SEARCH
    assert generate.pick_template("browse around") is generate._GENERIC


def test_generate_writes_files(tmp_path):
    cfg = config.load(str(tmp_path))
    feat, pom = generate.generate("the login page", "https://saucedemo.com",
                                  cfg, str(tmp_path))
    assert feat.exists() and pom.exists()
    assert feat.name == "login.feature"
    assert feat.parent == tmp_path / "features" / "saucedemo"
    assert pom.parent == tmp_path / "features" / "saucedemo" / "pageobjects"
    text = feat.read_text()
    assert 'User is on "https://saucedemo.com"' in text
    assert "username field" in pom.read_text()


def test_app_from_url():
    assert generate._app_from_url("https://www.canadiantire.ca/en.html") == "canadiantire"
    assert generate._app_from_url("http://localhost:3333") == "localhost"


def test_dispatch_create(tmp_path, capsys):
    cfg = config.load(str(tmp_path))
    keep = repl.dispatch('create test for login at https://example.com',
                         cfg, str(tmp_path), llm=None)
    assert keep is True
    assert (tmp_path / "features" / "example" / "login.feature").exists()


def test_dispatch_quit_and_help(tmp_path, capsys):
    cfg = config.load(str(tmp_path))
    assert repl.dispatch("quit", cfg, str(tmp_path), None) is False
    assert repl.dispatch("help", cfg, str(tmp_path), None) is True
    assert "commands" in capsys.readouterr().out


def test_summary_counts(tmp_path):
    d = tmp_path / "allure-results"
    d.mkdir()
    (d / "a-result.json").write_text(json.dumps({
        "name": "Valid login", "status": "passed",
        "labels": [{"name": "feature", "value": "Login"}],
        "steps": [], "start": 1000, "stop": 2000}))
    (d / "b-result.json").write_text(json.dumps({
        "name": "Bad login", "status": "failed",
        "labels": [{"name": "feature", "value": "Login"}],
        "steps": [{"name": 'Then User should see "ok"', "status": "failed"}],
        "start": 2000, "stop": 5000}))
    s = summary.collect(str(d))
    assert s["passed"] == 1 and s["failed"] == 1
    assert s["seconds"] == 4
    assert s["failures"][0]["feature"] == "Login"
    out = summary.render(str(d))
    assert "1 passed" in out and "1 failed" in out and "Bad login" in out
