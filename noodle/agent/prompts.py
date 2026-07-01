"""Prompt templates for agent test generation (NOOD_0007).

One place for every prompt the agent sends to a model, so wording is tuned
here — not scattered through generate.py. Templates embed STEP_VOCABULARY,
the canonical pattern phrasings, so even a small local model (the primary
target — Ollama-class, per decision #2) writes steps the deterministic
resolver understands instead of inventing its own grammar.
"""

# Canonical phrasings from noodle/resolver/patterns.py — the vocabulary the
# engine resolves without an LLM. Curated, not generated: the point is to show
# the model one good example per action family, not all 100+ regexes.
# ponytail: hand-kept list; extend when a generated suite misses a family.
STEP_VOCABULARY = """\
Navigation / setup:
  Given User is on "https://example.com"
  When User reloads the page
  When User goes back
  When User sets the viewport to "1920x1080"

Interaction:
  When User clicks the login button
  When User double-clicks "Row 3"
  When User enters "value" in the username field
  When User selects "Blue" from the color dropdown
  When User checks the "Remember me" checkbox
  When User hovers over the "Products" menu
  When User presses "Enter"
  When User submits the login form
  When User scrolls down

Waiting:
  When User waits for "Loading" to disappear
  When User waits for the page to load

Assertions:
  Then User should see "Welcome"
  Then User should not see "Error"
  Then the url should contain "/dashboard"
  Then the page title should be "Home"
  Then the "username" field should contain "Alice"
  Then the "Submit" button should be enabled

Variables:
  When User stores the text of the "total" element as `total`
  Then `total` should be greater than "0"

REST API:
  When User sets a request header 'Accept' to 'application/json'
  When User sets the bearer token to '[API_TOKEN]'
  When User performs a GET request at '/users/1'
  When User performs a POST request at '/users' with body '{"name": "Ada"}'
  Then the response status should be 200
  Then the response body should contain 'Ada'
  When User extracts 'id' from the response and stores it as `user_id`
"""

GENERATION = """\
You write Behave .feature files for the Noodle test framework.

Rules:
- Output ONLY the .feature file content — no commentary, no markdown fence.
- Start with the @web tag line, then "Feature:", then one or more scenarios.
- Every step MUST use one of the sentence shapes below (change only the
  quoted values, field names, and URLs). Do not invent other phrasings.
- Values that are credentials or environment-specific go in [BRACKETS],
  e.g. [USERNAME], so they resolve from config at run time.

Sentence shapes the framework understands:
{vocabulary}

Application under test: {url}
Test description: {description}
"""

REPAIR = """\
You wrote a Behave .feature file, but these steps do not match any sentence
shape the framework understands:

{unmatched}

Rewrite the COMPLETE .feature file, replacing only those steps with the
closest sentence shape from this list (keep everything else unchanged):

{vocabulary}

Output ONLY the corrected .feature content — no commentary, no markdown fence.

Current file:
{feature}
"""


def generation_prompt(description: str, url: str) -> str:
    return GENERATION.format(vocabulary=STEP_VOCABULARY, url=url,
                             description=description)


def repair_prompt(feature_text: str, unmatched: list[str]) -> str:
    lines = "\n".join(f"  - {s}" for s in unmatched)
    return REPAIR.format(unmatched=lines, vocabulary=STEP_VOCABULARY,
                         feature=feature_text)
