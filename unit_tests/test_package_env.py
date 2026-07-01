"""NOOD_0005 Phase 2 — per-package environment/ loader self-check.

No browser, no LLM. Verifies the <feature_dir>/environment/.env + secrets.env
cascade in hooks.py: package files fill in new keys but never override a key
that's already set (root config/secrets, or a real env var) — same
first-load-wins rule environments.yaml already uses.
"""
import os

import pytest

_KEYS = ("MYAPP_TOKEN", "MYAPP_SECRET", "MYAPP")


@pytest.fixture(autouse=True)
def clean_state():
    from noodle import hooks
    hooks._loaded_package_dirs.clear()
    for k in _KEYS:
        os.environ.pop(k, None)
    yield
    hooks._loaded_package_dirs.clear()
    for k in _KEYS:
        os.environ.pop(k, None)


def _make_package(tmp_path, env_lines=None, secrets_lines=None):
    pkg = tmp_path / "features" / "myapp"
    env_dir = pkg / "environment"
    env_dir.mkdir(parents=True)
    if env_lines:
        (env_dir / ".env").write_text("\n".join(env_lines) + "\n")
    if secrets_lines:
        (env_dir / "secrets.env").write_text("\n".join(secrets_lines) + "\n")
    return pkg


class TestLoadPackageEnv:
    def test_new_key_lands_in_environ(self, tmp_path):
        from noodle import hooks

        pkg = _make_package(tmp_path, env_lines=["MYAPP_TOKEN=from-package"])
        hooks._load_package_env(pkg)
        assert os.environ["MYAPP_TOKEN"] == "from-package"

    def test_existing_key_not_clobbered(self, tmp_path):
        """A key already in os.environ (root config, real env var) wins over
        the package's own value — first-load-wins, same as environments.yaml."""
        from noodle import hooks

        os.environ["MYAPP_TOKEN"] = "from-root"
        pkg = _make_package(tmp_path, env_lines=["MYAPP_TOKEN=from-package"])
        hooks._load_package_env(pkg)
        assert os.environ["MYAPP_TOKEN"] == "from-root"

    def test_env_wins_over_secrets_on_conflict(self, tmp_path):
        """Mirrors before_all's own order: .env loads before secrets.env."""
        from noodle import hooks

        pkg = _make_package(
            tmp_path,
            env_lines=["MYAPP_SECRET=from-env"],
            secrets_lines=["MYAPP_SECRET=from-secrets"],
        )
        hooks._load_package_env(pkg)
        assert os.environ["MYAPP_SECRET"] == "from-env"

    def test_missing_environment_folder_is_a_noop(self, tmp_path):
        from noodle import hooks

        pkg = tmp_path / "features" / "empty_app"
        pkg.mkdir(parents=True)
        hooks._load_package_env(pkg)  # must not raise

    def test_loaded_once_per_package_dir(self, tmp_path):
        """Second call for the same package dir is a no-op — editing the file
        after the first load must not change os.environ (before_feature fires
        once per .feature file, many files share one package dir)."""
        from noodle import hooks

        pkg = _make_package(tmp_path, env_lines=["MYAPP_TOKEN=first"])
        hooks._load_package_env(pkg)
        assert os.environ["MYAPP_TOKEN"] == "first"

        (pkg / "environment" / ".env").write_text("MYAPP_TOKEN=second\n")
        hooks._load_package_env(pkg)
        assert os.environ["MYAPP_TOKEN"] == "first"


class TestLoadEnvironmentsGlob:
    def test_package_environments_yaml_picked_up(self, tmp_path, monkeypatch):
        from noodle import hooks

        monkeypatch.chdir(tmp_path)
        pkg_env = tmp_path / "features" / "myapp" / "environment"
        pkg_env.mkdir(parents=True)
        (pkg_env / "environments.yaml").write_text("myapp: http://localhost:9999\n")

        hooks._load_environments()

        assert os.environ["MYAPP"] == "http://localhost:9999"

    def test_root_environments_yaml_wins_over_package(self, tmp_path, monkeypatch):
        from noodle import hooks

        monkeypatch.chdir(tmp_path)
        (tmp_path / "environments.yaml").write_text("myapp: http://root\n")
        pkg_env = tmp_path / "features" / "myapp" / "environment"
        pkg_env.mkdir(parents=True)
        (pkg_env / "environments.yaml").write_text("myapp: http://package\n")

        hooks._load_environments()

        assert os.environ["MYAPP"] == "http://root"
