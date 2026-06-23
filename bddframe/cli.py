import os
import subprocess
import typer

app = typer.Typer(help="BDDFrame — AI-powered BDD test runner", add_completion=False)


@app.command()
def run(
    path: str = typer.Argument("features/", help="Path to .feature files or directory"),
    headless: bool = typer.Option(False, "--headless", help="Run browser without UI"),
    tag: str = typer.Option(None, "--tag", "-t", help="Filter by tag e.g. smoke"),
    browser: str = typer.Option("chromium", "--browser", "-b", help="chromium | firefox | webkit"),
    workers: int = typer.Option(1, "--workers", "-w", help="Parallel scenario workers (phase 5)"),
):
    """Run .feature files."""
    env = os.environ.copy()
    env["BDDFRAME_HEADLESS"] = "true" if headless else "false"
    env["BDDFRAME_BROWSER"] = browser

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
