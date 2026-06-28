import json
import os
import subprocess
from pathlib import Path
import typer

app = typer.Typer(help="BDDFrame — AI-powered BDD test runner", add_completion=False)

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
    path: str = typer.Argument("features/", help="Path to .feature files or directory"),
    headless: bool = typer.Option(False, "--headless", help="Run browser without UI"),
    headed: bool = typer.Option(False, "--headed", help="Force browser visible (overrides --headless and .env)"),
    tag: str = typer.Option(None, "--tag", "-t", help="Filter by tag e.g. smoke"),
    browser: str = typer.Option("chromium", "--browser", "-b", help="chromium | firefox | webkit"),
    retries: int = typer.Option(None, "--retries", help="Re-run a failed scenario N extra times (default 1; 0 disables)"),
    log_level: str = typer.Option(None, "--log-level", help="DEBUG | INFO | WARNING | ERROR"),
    parallel: int = typer.Option(None, "--parallel", help="Run N feature files at once via behavex (web only; use --headless). 0/omitted = single process. Defaults to $BDDFRAME_PARALLEL_PROCESSES."),
):
    """Run .feature files."""
    # Toggle: flag wins; otherwise fall back to the env var (lets CI/local flip
    # parallelism without changing the command). 0 or unset = single process.
    if parallel is None:
        parallel = int(os.getenv("BDDFRAME_PARALLEL_PROCESSES", "0") or "0")
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
        env["BDDFRAME_HEADLESS"] = "false"
    elif headless:
        env["BDDFRAME_HEADLESS"] = "true"
    else:
        env["BDDFRAME_HEADLESS"] = _normalize_headless(env.get("BDDFRAME_HEADLESS", "false"))

    env["BDDFRAME_BROWSER"] = browser
    if retries is not None:
        env["BDDFRAME_RETRIES"] = str(retries)
    if log_level is not None:
        env["BDDFRAME_LOG_LEVEL"] = log_level

    # Parallel: behavex runs N behave workers, each writing to its own results
    # subdir (set in hooks.before_all). We clean once, run, flatten, report.
    if parallel > 0:
        raise typer.Exit(_run_parallel(path, parallel, tag, env))

    # Bug 5: derive behave base from the passed path, not a hardcoded 'features/'
    if path.endswith(".feature"):
        feature_path = Path(path).resolve()
        base = _find_behave_base(feature_path)
        args = ["behave", str(base), "--include", feature_path.stem, "--no-capture"]
    else:
        args = ["behave", path, "--no-capture"]

    if tag:
        args += ["--tags", tag]

    result = subprocess.run(args, env=env)
    rc = result.returncode

    # @quarantine is non-blocking: if every failed scenario this run is tagged
    # @quarantine, don't fail the build — they still ran and report as failed.
    if rc != 0 and _all_failures_quarantined("allure-results") is True:
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


def _run_parallel(path: str, processes: int, tag: str, env: dict) -> int:
    """Run feature files concurrently via behavex, then merge into one report."""
    try:
        import behavex  # noqa: F401
    except ImportError:
        raise typer.BadParameter(
            'Parallel runs need behavex. Install: pip install -e ".[parallel]"',
            param_hint="'--parallel'",
        )
    results = Path("allure-results")
    _clean_results_root(results)            # workers skip the wipe in parallel mode
    env = {**env, "BDDFRAME_PARALLEL_WORKER": "1"}
    args = ["behavex", path, "--parallel-processes", str(processes),
            "--parallel-scheme", "feature"]
    if tag:
        args += ["--tags", tag]
    rc = subprocess.run(args, env=env).returncode
    _merge_worker_results(results)          # flatten p*/ so report + scan read one dir

    if rc != 0 and _all_failures_quarantined("allure-results") is True:
        typer.echo("\n  🔶 Only @quarantine scenarios failed — not failing the build.")
        rc = 0
    from bddframe.reporting.builder import generate
    generate("allure-results", "allure-report")
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
    from bddframe.reporting import junit as _junit

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


@app.command()
def validate(
    path: str = typer.Argument("features/", help="Path to validate"),
):
    """Parse .feature files and check variable references — no browser launched."""
    result = subprocess.run(["behave", path, "--dry-run", "--no-capture"])
    raise typer.Exit(result.returncode)


@app.command("list")
def list_scenarios(
    path: str = typer.Argument("features/", help="Path to scan"),
):
    """List all discovered scenarios without running them."""
    subprocess.run([
        "behave", path, "--dry-run", "--no-capture",
        "--format", "pretty", "--no-skipped",
    ])


@app.command()
def record(
    output: str = typer.Option("features/recorded.feature", "--output", "-o", help="Path to write the generated .feature file"),
    name: str = typer.Option("Recorded Feature", "--name", "-n", help="Feature/scenario name"),
):
    """Record a new test by performing actions in a browser."""
    from bddframe.recorder.recorder import Recorder
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
    from bddframe.reporting.builder import open_report
    open_report(report_dir)


@report_app.command("generate")
def report_generate(
    results_dir: str = typer.Argument("allure-results", help="Path to allure-results/"),
    report_dir: str = typer.Option("allure-report", "--out", "-o", help="Output directory"),
):
    """Re-generate the Allure HTML report from existing results."""
    from bddframe.reporting.builder import generate
    generate(results_dir, report_dir)


if __name__ == "__main__":
    app()
