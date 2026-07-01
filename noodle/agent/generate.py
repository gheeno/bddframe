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


def generate(description: str, url: str, workspace_cfg: dict, workspace: str = "."):
    """Write features/<name>.feature + pageobjects/<name>_pom.yaml. Returns paths."""
    name = _name_from(description, url)
    title = name.replace("_", " ").title()
    feature_tpl, pom_tpl = pick_template(description)
    feature = feature_tpl.format(url=url, name=name, Title=title)
    pom = pom_tpl.format(url=url, name=name, Title=title)

    root = Path(workspace)
    feat_path = root / workspace_cfg["features_dir"] / f"{name}.feature"
    pom_path = root / workspace_cfg["pageobjects_dir"] / f"{name}_pom.yaml"
    for p, text in [(feat_path, feature), (pom_path, pom)]:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    return feat_path, pom_path


def generate_llm(description: str, url: str, workspace_cfg: dict, workspace: str = "."):
    """Opt-in: a local Ollama / paid model writes the Gherkin instead of a template.
    Routes through litellm (noodle.llm.client), so --llm ollama|claude all work."""
    from noodle.llm.client import ask
    name = _name_from(description, url)
    prompt = (
        "Write a Behave .feature file in Gherkin for this test. Use steps phrased "
        "like 'Given User is on \"<url>\"', 'When User enters \"x\" in the y field', "
        "'And User clicks the z button', 'Then User should see \"text\"'. "
        f"URL: {url}\nDescription: {description}\n"
        "Output only the .feature content, no commentary."
    )
    feature = ask(prompt).strip()
    if feature.startswith("```"):
        feature = re.sub(r"^```[a-z]*\n|\n```$", "", feature)
    root = Path(workspace)
    feat_path = root / workspace_cfg["features_dir"] / f"{name}.feature"
    feat_path.parent.mkdir(parents=True, exist_ok=True)
    feat_path.write_text(feature + "\n")
    # POM still skeletoned from the template — the LLM doesn't know real selectors.
    _, pom_tpl = pick_template(description)
    pom_path = root / workspace_cfg["pageobjects_dir"] / f"{name}_pom.yaml"
    pom_path.parent.mkdir(parents=True, exist_ok=True)
    pom_path.write_text(pom_tpl.format(url=url, name=name, Title=name.title()))
    return feat_path, pom_path
