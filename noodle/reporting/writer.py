import json
import time
import uuid
from pathlib import Path

from noodle.reporting.paths import results_dir


class ScenarioResult:
    def __init__(self, scenario):
        self.uuid = str(uuid.uuid4())
        self._failure_message = None
        self._failure_trace = None
        self.result = {
            "uuid": self.uuid,
            "name": scenario.name,
            "fullName": f"{scenario.feature.name}: {scenario.name}",
            "labels": [
                {"name": "feature", "value": scenario.feature.name},
                *[{"name": "tag", "value": t} for t in scenario.tags],
            ],
            "steps": [],
            "start": int(time.time() * 1000),
            "status": "passed",
        }

    def add_step(self, step, status, attachment_path=None):
        entry = {
            "name": f"{step.keyword} {step.name}",
            "status": status,
            "start": int(time.time() * 1000),
            "stop": int(time.time() * 1000),
        }
        if status == "failed":
            error_msg = str(step.exception) if step.exception else "Step failed"
            entry["statusDetails"] = {
                "message": error_msg,
                "trace": step.error_message or "",
            }
            if attachment_path:
                attach_name = Path(attachment_path).name
                entry["attachments"] = [{
                    "name": "failure_screenshot",
                    "source": attach_name,
                    "type": "image/png",
                }]
        self.result["steps"].append(entry)

    def finish(self, scenario):
        self.result["stop"] = int(time.time() * 1000)
        # Determine overall status from steps
        statuses = [s["status"] for s in self.result["steps"]]
        if "failed" in statuses:
            self.result["status"] = "failed"
            # Propagate first failure details to top-level statusDetails
            for s in self.result["steps"]:
                if s["status"] == "failed" and "statusDetails" in s:
                    self.result["statusDetails"] = s["statusDetails"]
                    break
        else:
            self.result["status"] = "passed"


def write_result(scenario_result: ScenarioResult):
    d = results_dir()
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{scenario_result.uuid}-result.json"
    path.write_text(json.dumps(scenario_result.result, indent=2))
    return path
