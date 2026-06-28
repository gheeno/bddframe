"""BFRAME_0022 — local process parallelism (behavex) reporting safety.

The risk parallelism introduces is workers clobbering each other in the shared
allure-results/ dir. These cover the three fixes: per-worker results dir, the
skipped wipe, and the merge-back.
"""
import os

from bddframe.reporting.paths import results_dir


def test_results_dir_default(monkeypatch):
    monkeypatch.delenv("BDDFRAME_RESULTS_DIR", raising=False)
    assert str(results_dir()) == "allure-results"


def test_results_dir_env_override(monkeypatch):
    monkeypatch.setenv("BDDFRAME_RESULTS_DIR", "allure-results/p999")
    assert str(results_dir()) == "allure-results/p999"


def test_before_all_parallel_uses_pid_dir_and_skips_wipe(monkeypatch):
    from bddframe import hooks
    monkeypatch.setattr(hooks, "load_dotenv", lambda *a, **k: None)
    monkeypatch.setattr(hooks, "_load_environments", lambda: None)
    monkeypatch.setattr(hooks, "_load_keyvault", lambda: None)
    monkeypatch.setattr(hooks, "_run_hooks", lambda *a, **k: None)
    monkeypatch.setattr(hooks.healing, "reset", lambda: None)
    wiped = []
    monkeypatch.setattr(hooks, "_clean_allure_results", lambda: wiped.append(True))
    monkeypatch.setenv("BDDFRAME_PARALLEL", "1")
    monkeypatch.delenv("BDDFRAME_RESULTS_DIR", raising=False)

    hooks.before_all(object())

    assert wiped == []  # parallel worker must NOT wipe the shared dir
    assert os.environ["BDDFRAME_RESULTS_DIR"] == f"allure-results/p{os.getpid()}"


def test_before_all_sequential_wipes_shared_dir(monkeypatch):
    from bddframe import hooks
    monkeypatch.setattr(hooks, "load_dotenv", lambda *a, **k: None)
    monkeypatch.setattr(hooks, "_load_environments", lambda: None)
    monkeypatch.setattr(hooks, "_load_keyvault", lambda: None)
    monkeypatch.setattr(hooks, "_run_hooks", lambda *a, **k: None)
    monkeypatch.setattr(hooks.healing, "reset", lambda: None)
    wiped = []
    monkeypatch.setattr(hooks, "_clean_allure_results", lambda: wiped.append(True))
    monkeypatch.delenv("BDDFRAME_PARALLEL", raising=False)

    hooks.before_all(object())
    assert wiped == [True]


def test_merge_flattens_worker_results(tmp_path):
    from bddframe.cli import _merge_worker_results
    (tmp_path / "p1").mkdir()
    (tmp_path / "p2").mkdir()
    (tmp_path / "p1" / "a-result.json").write_text("{}")
    (tmp_path / "p1" / "junit.xml").write_text("<x/>")
    (tmp_path / "p2" / "b-result.json").write_text("{}")

    _merge_worker_results(tmp_path)

    flat = {f.name for f in tmp_path.glob("*-result.json")}
    assert flat == {"a-result.json", "b-result.json"}
    # per-worker junit stays put, not flattened
    assert (tmp_path / "p1" / "junit.xml").exists()


def test_clean_removes_worker_dirs(tmp_path):
    from bddframe.cli import _clean_results_root
    (tmp_path / "old-result.json").write_text("{}")
    (tmp_path / "junit.xml").write_text("<x/>")
    (tmp_path / "p7").mkdir()
    (tmp_path / "p7" / "x-result.json").write_text("{}")

    _clean_results_root(tmp_path)

    assert list(tmp_path.glob("*-result.json")) == []
    assert not (tmp_path / "junit.xml").exists()
    assert not (tmp_path / "p7").exists()
