"""Rule-based test generation: a URL + a short description become a .feature
file plus a skeleton POM YAML in the user's workspace. No LLM, no cost.

Pick the nearest template by keyword. ponytail: three templates (login, search,
generic) cover the common shapes — add form/checkout templates when a real test
needs phrasing these don't give. The Ollama/paid path (generate_llm) replaces
the template entirely when --llm is set.
"""
import re
from pathlib import Path

# --- templates ---------------------------------------------------------------
# Each returns (feature_text, pom_text). {url}/{name}/{Title} filled by caller.

_LOGIN = ("""@web
Feature: {Title}

  @smoke
  Scenario: Valid user logs in successfully
    Given User is on "{url}"
    When User enters "<username>" in the username field
    And User enters "<password>" in the password field
    And User clicks the login button
    Then User should see "<expected text after login>"

  Scenario: Invalid credentials show an error
    Given User is on "{url}"
    When User enters "wrong" in the username field
    And User enters "wrong" in the password field
    And User clicks the login button
    Then User should see "<expected error message>"
""", """# Page object — {name}. Fill in selectors the framework can't infer by text.
# Most fields resolve by accessible label; add overrides here only when needed.
username field:
  css: "<css selector>"
password field:
  css: "<css selector>"
login button:
  css: "<css selector>"
""")

_SEARCH = ("""@web
Feature: {Title}

  @smoke
  Scenario: Search returns results
    Given User is on "{url}"
    When User enters "<search term>" in the search field
    And User clicks the search button
    Then User should see "<expected result text>"
""", """# Page object — {name}.
search field:
  css: "<css selector>"
search button:
  css: "<css selector>"
""")

_GENERIC = ("""@web
Feature: {Title}

  @smoke
  Scenario: {Title}
    Given User is on "{url}"
    Then User should see "<expected text>"
""", """# Page object — {name}. Add selectors as you flesh out the steps.
""")

_TEMPLATES = {"login": _LOGIN, "search": _SEARCH}


def pick_template(description: str):
    d = description.lower()
    if re.search(r"\b(login|log in|sign in|signin|authenticat)", d):
        return _LOGIN
    if "search" in d:
        return _SEARCH
    return _GENERIC


def _name_from(description: str, url: str) -> str:
    """Derive a short snake_case file stem from the description (or URL host)."""
    words = re.findall(r"[a-z0-9]+", description.lower())
    # drop filler so "create test for the login page" -> "login_page"
    stop = {"create", "test", "for", "the", "a", "an", "page", "at", "on", "of", "to"}
    words = [w for w in words if w not in stop]
    if not words:
        host = re.sub(r"^www\.", "", re.sub(r"^https?://", "", url)).split("/")[0]
        words = re.findall(r"[a-z0-9]+", host.split(".")[0]) or ["test"]
    return "_".join(words[:3])


def _app_from_url(url: str) -> str:
    """Derive the app-package folder name from the URL host, e.g.
    https://www.canadiantire.ca/... -> canadiantire, http://localhost:3333 -> localhost.
    Each app-under-test gets its own package folder (see docs/feature-packages.md)."""
    host = re.sub(r"^www\.", "", re.sub(r"^https?://", "", url)).split("/")[0]
    host = host.split(":")[0].split(".")[0]
    return re.sub(r"[^a-z0-9]+", "_", host.lower()) or "app"


def generate(description: str, url: str, workspace_cfg: dict, workspace: str = "."):
    """Write <features_dir>/<app>/<name>.feature + pageobjects/<name>_pom.yaml,
    where <app> is derived from the URL's host — each app-under-test gets its
    own package folder (docs/feature-packages.md). Returns paths."""
    name = _name_from(description, url)
    app = _app_from_url(url)
    title = name.replace("_", " ").title()
    feature_tpl, pom_tpl = pick_template(description)
    feature = feature_tpl.format(url=url, name=name, Title=title)
    pom = pom_tpl.format(url=url, name=name, Title=title)

    app_dir = Path(workspace) / workspace_cfg["features_dir"] / app
    feat_path = app_dir / f"{name}.feature"
    pom_path = app_dir / "pageobjects" / f"{name}_pom.yaml"
    for p, text in [(feat_path, feature), (pom_path, pom)]:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    return feat_path, pom_path


def _strip_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\n|\n```$", "", text)
    return text


def generate_llm(description: str, url: str, workspace_cfg: dict, workspace: str = "."):
    """Opt-in: a local Ollama / paid model writes the Gherkin instead of a template.
    Routes through litellm (noodle.llm.client), so --llm ollama|claude all work.

    NOOD_0007: the output is validated against the pattern table before it's
    written. Steps the deterministic resolver can't handle get ONE repair pass
    (the model is shown the misses + the canonical vocabulary), then the file
    is written either way with a per-step report — never a silent skeleton
    that only works with a runtime LLM.
    """
    from noodle.llm.client import ask
    from noodle.agent import prompts, validate

    name = _name_from(description, url)
    feature = _strip_fence(ask(prompts.generation_prompt(description, url)))
    result = validate.check_feature(feature)
    if result["error"] or validate.unmatched(result):
        repaired = _strip_fence(ask(prompts.repair_prompt(
            feature, validate.unmatched(result) or ["<file did not parse as Gherkin>"])))
        re_result = validate.check_feature(repaired)
        # Keep the repair only if it's an improvement — a model that mangles
        # the file on retry shouldn't overwrite a mostly-good first draft.
        if not re_result["error"] and \
                len(validate.unmatched(re_result)) < len(validate.unmatched(result)):
            feature, result = repaired, re_result

    app_dir = Path(workspace) / workspace_cfg["features_dir"] / _app_from_url(url)
    feat_path = app_dir / f"{name}.feature"
    feat_path.parent.mkdir(parents=True, exist_ok=True)
    feat_path.write_text(feature + "\n")
    # POM still skeletoned from the template — the LLM doesn't know real selectors.
    _, pom_tpl = pick_template(description)
    pom_path = app_dir / "pageobjects" / f"{name}_pom.yaml"
    pom_path.parent.mkdir(parents=True, exist_ok=True)
    pom_path.write_text(pom_tpl.format(url=url, name=name, Title=name.title()))
    print(validate.render(result))
    return feat_path, pom_path
