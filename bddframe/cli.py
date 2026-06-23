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
    workers: int = typer.Option(1, "--workers", "-w", help="Parallel scenario workers (phase 6)"),
):
    """Run .feature files."""
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
    raise typer.Exit(result.returncode)


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


if __name__ == "__main__":
    app()
