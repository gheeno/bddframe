import json
import os
import subprocess
from pathlib import Path
import typer

from noodle import config

app = typer.Typer(help="Noodle — AI-powered BDD test runner", add_completion=False)

_VALID_BROWSERS = {"chromium", "firefox", "webkit"}

# Truthy values accepted from environment (beyond the canonical "true").
_TRUTHY = {"1", "true", "yes", "on"}


def _normalize_headless(raw: str) -> str:
    """Normalise any truthy/falsy env-var spelling to canonical 'true'/'false'."""
    return "true" if raw.strip().lower() in _TRUTHY else "false"


def _find_behave_base(feature_path: Path) -> Path:
    """
    Walk up from the feature file's parent to find the behave root — the nearest
    ancestor that contains a steps/ subdirectory or an environment.py file.
    Falls back to 'features/' if no marker is found (standard layout).
    """
    for directory in [feature_path.parent, *feature_path.parent.parents]:
        if (directory / "steps").is_dir() or (directory / "environment.py").exists():
            return directory
    return Path("features")


@app.command()
def run(
    path: str = typer.Argument(None, help="Path to .feature files or directory (default: workspace features_dir)"),
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace dir holding noodle.yaml, features/, .env"),
    headless: bool = typer.Option(False, "--headless", help="Run browser without UI"),
    headed: bool = typer.Option(False, "--headed", help="Force browser visible (overrides --headless and .env)"),
    tag: str = typer.Option(None, "--tag", "-t", help="Filter by tag e.g. smoke"),
    browser: str = typer.Option(None, "--browser", "-b", help="chromium | firefox | webkit (default: workspace config)"),
    retries: int = typer.Option(None, "--retries", help="Re-run a failed scenario N extra times (default 1; 0 disables)"),
    log_level: str = typer.Option(None, "--log-level", help="DEBUG | INFO | WARNING | ERROR"),
    parallel: int = typer.Option(None, "--parallel", help="Run N feature files at once via behavex (web only; use --headless). 0/omitted = single process. Defaults to $NOODLE_PARALLEL_PROCESSES."),
):
    """Run .feature files."""
    cfg = config.load(workspace)
    # No path given → run the workspace's features dir. browser/headless fall
    # back to the workspace config when the flags aren't set.
    if path is None:
        path = cfg["features_dir"]
    if browser is None:
        browser = cfg["browser"]
    # Toggle: flag wins; otherwise fall back to the env var (lets CI/local flip
    # parallelism without changing the command). 0 or unset = single process.
    if parallel is None:
        parallel = int(os.getenv("NOODLE_PARALLEL_PROCESSES", "0") or "0")
    # Bug 2: reject mutually exclusive flags up front
    if headed and headless:
        raise typer.BadParameter(
            "--headed and --headless are mutually exclusive. Pass one or neither.",
            param_hint="'--headed' / '--headless'",
        )

    # Bug 4: validate browser name before it reaches Playwright
    if browser not in _VALID_BROWSERS:
        raise typer.BadParameter(
            f"Unsupported browser '{browser}'. Valid options: {', '.join(sorted(_VALID_BROWSERS))}",
            param_hint="'--browser'",
        )

    env = os.environ.copy()

    # Bug 1: always write a canonical "true"/"false" — never pass raw env through
    if headed:
        env["NOODLE_HEADLESS"] = "false"
    elif headless:
        env["NOODLE_HEADLESS"] = "true"
    else:
        default = "true" if cfg["headless"] else "false"
        env["NOODLE_HEADLESS"] = _normalize_headless(env.get("NOODLE_HEADLESS", default))

    env["NOODLE_BROWSER"] = browser
    if retries is not None:
        env["NOODLE_RETRIES"] = str(retries)
    if log_level is not None:
        env["NOODLE_LOG_LEVEL"] = log_level

    # Run inside the workspace so behave finds its .env, environments.yaml and
    # writes allure-results there. workspace="." keeps the in-repo behaviour.
    cwd = workspace

    # Parallel: behavex runs N behave workers, each writing to its own results
    # subdir (set in hooks.before_all). We clean once, run, flatten, report.
    if parallel > 0:
        raise typer.Exit(_run_parallel(path, parallel, tag, env, cwd))

    # Bug 5: derive behave base from the passed path, not a hardcoded 'features/'
    if path.endswith(".feature"):
        feature_path = (Path(cwd) / path).resolve()
        base = _find_behave_base(feature_path)
        args = ["behave", str(base), "--include", feature_path.stem, "--no-capture"]
    else:
        args = ["behave", path, "--no-capture"]

    if tag:
        args += ["--tags", tag]

    result = subprocess.run(args, env=env, cwd=cwd)
    rc = result.returncode

    results_root = str(Path(cwd) / "allure-results")
    # @quarantine is non-blocking: if every failed scenario this run is tagged
    # @quarantine, don't fail the build — they still ran and report as failed.
    if rc != 0 and _all_failures_quarantined(results_root) is True:
        typer.echo("\n  🔶 Only @quarantine scenarios failed — not failing the build.")
        rc = 0

    raise typer.Exit(rc)


def _all_failures_quarantined(results_dir: str):
    """Scan this run's Allure results. Returns:
      True  — there were failures and ALL are @quarantine
      False — at least one non-quarantine failure
      None  — nothing to judge (no results / reporting off / no failures)
    """
    d = Path(results_dir)
    files = list(d.glob("*-result.json")) if d.is_dir() else []
    if not files:
        return None
    failed = []
    for f in files:
        try:
            r = json.loads(f.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if r.get("status") == "failed":
            tags = {l.get("value") for l in r.get("labels", []) if l.get("name") == "tag"}
            failed.append("quarantine" in tags)
    if not failed:
        return None
    return all(failed)


def _run_parallel(path: str, processes: int, tag: str, env: dict, cwd: str = ".") -> int:
    """Run feature files concurrently via behavex, then merge into one report."""
    try:
        import behavex  # noqa: F401
    except ImportError:
        raise typer.BadParameter(
            'Parallel runs need behavex. Install: pip install -e ".[parallel]"',
            param_hint="'--parallel'",
        )
    results = Path(cwd) / "allure-results"
    _clean_results_root(results)            # workers skip the wipe in parallel mode
    env = {**env, "NOODLE_PARALLEL_WORKER": "1"}
    args = ["behavex", path, "--parallel-processes", str(processes),
            "--parallel-scheme", "feature"]
    if tag:
        args += ["--tags", tag]
    rc = subprocess.run(args, env=env, cwd=cwd).returncode
    _merge_worker_results(results)          # flatten p*/ so report + scan read one dir

    if rc != 0 and _all_failures_quarantined(str(results)) is True:
        typer.echo("\n  🔶 Only @quarantine scenarios failed — not failing the build.")
        rc = 0
    from noodle.reporting.builder import generate
    generate(str(results), str(Path(cwd) / "allure-report"))
    return rc


def _clean_results_root(results: Path):
    """Pre-run wipe of last run's flattened results + leftover worker subdirs."""
    if not results.is_dir():
        return
    import shutil
    for f in results.glob("*-result.json"):
        f.unlink(missing_ok=True)
    (results / "junit.xml").unlink(missing_ok=True)
    for d in results.glob("p*"):
        if d.is_dir():
            shutil.rmtree(d, ignore_errors=True)


def _merge_worker_results(results: Path):
    """Flatten each worker dir into the shared dir so the existing report build +
    quarantine scan (both read the flat dir) work unchanged, then remove the now-
    empty worker dirs. Per-worker junit files merge into one allure-results/
    junit.xml — same artifact a single-process run produces. uuid filenames don't
    collide. Cross-platform: pathlib rename + rmtree only."""
    import shutil
    from noodle.reporting import junit as _junit

    worker_dirs = sorted(d for d in results.glob("p*") if d.is_dir())
    junits = [d / "junit.xml" for d in worker_dirs]
    for d in worker_dirs:
        for f in d.iterdir():
            if f.is_file() and f.name != "junit.xml":
                f.rename(results / f.name)
    if any(j.is_file() for j in junits):
        _junit.merge_junits(junits, results / "junit.xml")
    for d in worker_dirs:
        shutil.rmtree(d, ignore_errors=True)


_NOODLE_YAML = """\
# Noodle workspace config. Paths are relative to this file.
features_dir: features
env_file: .env
reports_dir: reports
browser: chromium
headless: false
"""

_ENV_STUB = """\
# Workspace config (committed). NO SECRETS — put credentials in secrets.env.
NOODLE_BROWSER=chromium
NOODLE_HEADLESS=false
NOODLE_TIMEOUT=10000
"""

# behave glue — re-exports from the installed engine so behave discovers the
# lifecycle hooks and the single catch-all step matcher. Same files the BFRAME
# repo's own features/ uses; without them behave has no steps dir and won't run.
_ENVIRONMENT_PY = """\
from noodle.hooks import (
    before_all,
    before_feature,
    before_scenario,
    after_step,
    after_scenario,
    after_all,
)
"""

_CATCH_ALL_PY = """\
# behave auto-imports features/steps/*.py at startup. The engine registers one
# regex catch-all that routes each Gherkin line to the right agent. The z_ prefix
# keeps it last in load order so any project-local steps register first.
from noodle.steps.catch_all import *  # noqa: F401,F403
"""


@app.command()
def init(
    path: str = typer.Argument(".", help="Directory to scaffold the workspace in"),
):
    """Scaffold a test workspace (noodle.yaml, .env, features/environment.py, features/steps/).
    Page objects, environment/, and resources/ are created per app-under-test
    (see docs/feature-packages.md) — nothing to scaffold for them up front."""
    root = Path(path)
    root.mkdir(parents=True, exist_ok=True)
    created = []
    files = {
        root / "noodle.yaml": _NOODLE_YAML,
        root / ".env": _ENV_STUB,
        root / "features" / "environment.py": _ENVIRONMENT_PY,
        root / "features" / "steps" / "z_catch_all.py": _CATCH_ALL_PY,
    }
    for f, text in files.items():
        if f.exists():
            continue
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text)
        created.append(str(f))
    if created:
        typer.echo("Created:\n  " + "\n  ".join(created))
    else:
        typer.echo(f"Workspace already initialised at {root.resolve()}")
    typer.echo(f"\nNext: cd {path} && noodle-agent")


@app.command()
def summary(
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace dir"),
    llm: str = typer.Option("none", "--llm", help="none | ollama | claude — richer narrative via litellm"),
):
    """Plain-English summary of the last run from allure-results/."""
    from noodle.reporting import summary as _summary
    results = str(Path(workspace) / "allure-results")
    if llm and llm != "none":
        typer.echo(_summary.summarize_llm(results))
    else:
        report = str(Path(workspace) / "reports" / "allure-report")
        typer.echo(_summary.render(results, report))


@app.command()
def validate(
    path: str = typer.Argument(None, help="Path to validate (default: workspace features_dir)"),
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace dir"),
):
    """Parse .feature files and check variable references — no browser launched."""
    if path is None:
        path = config.load(workspace)["features_dir"]
    result = subprocess.run(["behave", path, "--dry-run", "--no-capture"], cwd=workspace)
    raise typer.Exit(result.returncode)


@app.command("list")
def list_scenarios(
    path: str = typer.Argument(None, help="Path to scan (default: workspace features_dir)"),
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace dir"),
):
    """List all discovered scenarios without running them."""
    if path is None:
        path = config.load(workspace)["features_dir"]
    subprocess.run([
        "behave", path, "--dry-run", "--no-capture",
        "--format", "pretty", "--no-skipped",
    ], cwd=workspace)


@app.command()
def record(
    output: str = typer.Option("features/recorded.feature", "--output", "-o", help="Path to write the generated .feature file"),
    name: str = typer.Option("Recorded Feature", "--name", "-n", help="Feature/scenario name"),
):
    """Record a new test by performing actions in a browser."""
    from noodle.recorder.recorder import Recorder
    Recorder(output_path=output, feature_name=name).record()


# ---------------------------------------------------------------------------
# report subcommand group
# ---------------------------------------------------------------------------

report_app = typer.Typer(help="Manage Allure test reports")
app.add_typer(report_app, name="report")


@report_app.command("open")
def report_open(
    report_dir: str = typer.Argument("allure-report", help="Path to the Allure report directory"),
):
    """Open the last Allure report in the browser."""
    from noodle.reporting.builder import open_report
    open_report(report_dir)


@report_app.command("generate")
def report_generate(
    results_dir: str = typer.Argument("allure-results", help="Path to allure-results/"),
    report_dir: str = typer.Option("allure-report", "--out", "-o", help="Output directory"),
):
    """Re-generate the Allure HTML report from existing results."""
    from noodle.reporting.builder import generate
    generate(results_dir, report_dir)


if __name__ == "__main__":
    app()
