import subprocess


def generate(results_dir: str = "allure-results", report_dir: str = "allure-report"):
    """Run allure generate to build the HTML report. Silently skips if allure is not installed."""
    subprocess.run(
        ["allure", "generate", results_dir, "-o", report_dir, "--clean"],
        check=False,
    )


def open_report(report_dir: str = "allure-report"):
    """Open the Allure report in the default browser."""
    subprocess.run(["allure", "open", report_dir], check=False)
