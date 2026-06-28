# BDDFrame Steps Dictionary

Steps are written in plain English and prefixed with `Given`, `When`, `Then`, or `And`.
The subject (`User`, `I`, `The user`) is stripped before matching, so all three forms are equivalent:

```gherkin
When User clicks the login button
When I click the login button
When The user clicks the login button
```

Variable substitution happens before matching:
- `` `VAR` `` → value captured during the run (e.g. stored from a previous step)
- `[VAR]` → value from `.env` or `environments.yaml`

---

## Navigation

```gherkin
Given User navigates to '[BASE_URL]/path'
Given User is on '[BASE_URL]/path'
Given User opens '[BASE_URL]/path'
Given User goes to '[BASE_URL]/path'
```

---

## Clicking

```gherkin
When User clicks the 'Login' button
When User clicks the 'Sign in' link
When User clicks 'Add to cart'
When User clicks the submit button
When User double-clicks 'Item Name'
When User right-clicks 'Context Menu'
When User taps 'Continue'
```

Scoped to a row or section:
```gherkin
When User clicks 'Edit' in the row containing 'Order #123'
When User clicks 'Delete' in the 'Actions' section
```

---

## Keyboard

```gherkin
When User presses 'Enter'
When User presses 'Tab'
When User presses 'Escape'
When User presses 'ArrowDown'
```

Supported keys: `Enter`, `Return`, `Tab`, `Escape`, `Space`, `Backspace`, `Delete`, `ArrowUp`, `ArrowDown`, `ArrowLeft`, `ArrowRight`, `Home`, `End`, `PageUp`, `PageDown`

---

## Forms

```gherkin
When User enters 'john@example.com' in the email field
When User types 'hunter2' into the password field
When User fills in the username with 'admin'
When User clears the search field
When User selects 'Canada' from the country dropdown
When User checks the 'Remember me' checkbox
When User unchecks the 'Subscribe' checkbox
When User submits the login form
```

---

## Hovering & Scrolling

```gherkin
When User hovers over the profile menu
When User scrolls down
When User scrolls up
When User scrolls to 'Footer'
```

---

## Browser History & Tabs

```gherkin
When User goes back
When User goes forward
When User reloads the page
When User refreshes the page
Then a new tab should open
When User switches to the new tab
When User switches to the original tab
When User closes the current tab
```

---

## Waits

```gherkin
When User waits for the page to load
When User waits for the page to fully load
When User waits for the network to be idle
When User waits until 'Welcome' is visible
When User waits until 'Spinner' disappears
When User waits 3 seconds
```

---

## Assertions — Visibility

```gherkin
Then User should see 'Welcome back'
Then User should not see 'Error'
Then User should see 3 'product' items
Then User should be on the dashboard page
Then User should have url containing '/checkout'
Then the page title should contain 'My App'
```

---

## Assertions — Element State

```gherkin
Then the 'Submit' button should be disabled
Then the 'Email' field should contain 'user@example.com'
Then the 'Email' field should have value 'user@example.com'
Then the 'username' should have attribute 'placeholder' equal to 'Enter name'
```

Supported states: `enabled`, `disabled`, `checked`, `unchecked`, `selected`, `editable`, `read-only`

---

## Assertions — Table / Grid

```gherkin
Then the table should have 5 rows
Then the cell in row 'Alice' column 'Role' should be 'Admin'
```

---

## Assertions — Value Comparison

Used to compare stored variables against expected values.

```gherkin
Then `PRICE` should equal '9.99'
Then `PRICE` should not equal '0.00'
Then `COUNT` should be greater than '0'
Then `COUNT` should be less than '100'
Then `COUNT` should be at least '1'
Then `RESPONSE` should contain 'success'
```

---

## Variables

Seed a literal value:
```gherkin
Given sets `BASE_PRICE` to '29.99'
```

Capture element text:
```gherkin
When User stores the total price in `TOTAL`
When User grabs the order number in `ORDER_ID`
```

Capture an element attribute:
```gherkin
When User stores attribute 'href' of the download link in `LINK_URL`
```

---

## Screenshots & Visual

```gherkin
When User takes a screenshot
When User takes a screenshot 'checkout-complete'
Then the screen should match the pixel baseline
Then the 'header' screen should match the pixel baseline
Then the screen should look the same as before
Then the screen should look the same as before ignoring the banner
```

---

## Search

```gherkin
When User searches for 'blue running shoes'
```

---

## Popups / Modals

```gherkin
When User closes all popups
When User closes the modal
When User closes the banner
```

---

## iFrames

```gherkin
When User switches to the 'payment-frame' iframe
```

---

## REST API Testing

### Setup

```gherkin
Given sets `REST_BASE_URL` to '[API_BASE_URL]'
Given sets request header 'Authorization' to 'Bearer token123'
Given sets request header 'X-Api-Key' to '[API_KEY]'
```

### Requests

Paths starting with `/` are appended to `REST_BASE_URL`. Absolute `https://` paths are used as-is.

```gherkin
When performs a GET call at '/objects'
When performs a GET call at '/objects/1'
When performs a GET call at '/objects' storing response in `LIST_RESP`

When performs a POST call at '/objects' with body '{"name": "My Item"}'
When performs a POST call at '/objects' with body '{"name": "My Item"}' storing response in `CREATED`

When performs a PUT call at '/objects/`OBJ_ID`' with body '{"name": "Updated"}'
When performs a PATCH call at '/objects/`OBJ_ID`' with body '{"name": "Patched"}'
When performs a DELETE call at '/objects/`OBJ_ID`'
When performs a DELETE call at '/objects/`OBJ_ID`' storing response in `DEL_RESP`
```

### Response Assertions

```gherkin
Then the response status should be 200
Then the response status code should be 404

Then the response body should contain 'id'
Then the response body should contain 'error'

Then the response body should contain:
  | Key       | Value      |
  | id        |            |
  | name      | My Item    |
  | createdAt |            |
```

Empty `Value` = key-exists check only. Non-empty `Value` = key and value both checked.

```gherkin
Then the response header 'Content-Type' should contain 'application/json'
Then the response header 'X-Auth' should be 'token123'

Then the response headers should contain:
  | Header       | Value            |
  | Content-Type | application/json |
```

### Extracting values from the response

```gherkin
Then extracts 'id' from response storing in `OBJ_ID`
Then extracts json key 'token' from response body storing in `AUTH_TOKEN`
```

After extraction, the value is available as a runtime variable for later steps:
```gherkin
When performs a DELETE call at '/objects/`OBJ_ID`'
```

### Full pattern example

```gherkin
Given sets `REST_BASE_URL` to '[API_BASE_URL]'
When performs a POST call at '/users' with body '{"name": "Alice"}' storing response in `USER_RESP`
Then the response status should be 200
And extracts 'id' from response storing in `USER_ID`
When performs a GET call at '/users/`USER_ID`'
Then the response status should be 200
And the response body should contain 'Alice'
When performs a DELETE call at '/users/`USER_ID`'
Then the response status should be 200
```

---

## API Setup / Teardown (Playwright-backed)

These use Playwright's request context (shares browser cookies) and only assert 2xx — no body access.

```gherkin
When User calls GET '[API_URL]/reset'
When User calls POST '[API_URL]/seed' with body '{"id": 1}'
When User calls DELETE '[API_URL]/items/1'
```

---

## Network Mocking

```gherkin
When User mocks '/api/products' with status 200 and body '[{"id":1}]'
When User mocks '/api/auth' with status 401
When User blocks requests to '**/analytics/**'
```

---

## Test Data

Load a YAML or JSON fixture file into the variable store:
```gherkin
Given User loads test data from 'fixtures/user.yaml'
```

Each top-level key becomes a `[KEY]` variable (uppercased, spaces → underscores).

---

## Scripts & Shell Commands

```gherkin
When User runs the script 'scripts/seed_db.py'
When User runs the script 'scripts/seed_db.py' with args '--env staging'
When User runs the script 'scripts/seed_db.py' storing output in `SEED_OUTPUT`

When User runs the command 'curl -s https://example.com/status'
When User runs the command 'npm run build' storing output in `BUILD_LOG`
```

stdout is always stored in `SCRIPT_OUTPUT`. Named `storing output in` stores it additionally under that name.

---

## Adding a new step

### Why the editor never warns

`cucumberautocomplete` (`.vscode/settings.json`) points at `.cucumber_stubs.py`, which registers three wildcard `.*` patterns — one each for `Given`, `When`, `Then`. Every step matches, so the LSP **never** reports "undefined step" warnings regardless of whether the step is implemented.

### What actually validates a step

The check happens at **runtime**. `bddframe/steps/catch_all.py` intercepts every step and hands it to `bddframe/resolver/patterns.py`. If no regex there matches, the scenario fails (see *What happens when a step is not found* below).

### How to add a new pattern

**1. Write the step** in your `.feature` file — the editor accepts it immediately.

**2. Add a regex** to `bddframe/resolver/patterns.py` → `PATTERNS` list:

```python
(r'^your pattern here (.+)$',  'your_action',  lambda m: {'param': m.group(1)}),
```

Patterns are tried top-to-bottom; first match wins — insert at the right priority position.

**3. Add an action handler** in `bddframe/agents/web/actions.py`:

```python
def your_action(page: Page, param: str):
    ...
```

**4. Wire the dispatch** in `bddframe/orchestrator/runner.py` → `execute_step()`:

```python
elif t == 'your_action':
    actions.your_action(page, **params)
```

No LSP changes needed — the wildcard stubs already cover every possible step text.

---

## What happens when a step is not found

When a step doesn't match any known pattern, the framework tries two things in order:

### 1. Pattern match fails

The step text is normalised (subject stripped, verb normalised to 3rd person) and compared against every regex in `patterns.py`. If nothing matches, you get:

```
AssertionError: No pattern matched: "User frobnicates the widget"
  Normalized to: "frobnicates the widget"
  → Add a pattern to bddframe/resolver/patterns.py
  → OR set BDDFRAME_MODEL in .env to enable LLM fallback
```

The scenario stops at that step and is marked **FAILED**.

### 2. LLM fallback (optional)

If `BDDFRAME_MODEL` is set in `.env`, the framework sends the unmatched step to the configured LLM and asks it to infer the action. The model picks from the known action types (click, fill, assert_visible, etc.) and constructs the parameter dict. This is a best-effort recovery — it works well for standard UI interactions phrased unusually, but won't invent new action types.

To enable:
```env
BDDFRAME_MODEL=claude-sonnet-4-6   # or any litellm-compatible model id
```

Requires the llm extra:
```
pip install bddframe[llm]
```

If the LLM returns something unparseable or an unknown action type, the step still fails with a clear error.

### Common reasons a step doesn't match

| Symptom | Likely cause |
|---|---|
| Step uses `[VAR]` but value is empty | Variable not defined in `.env` or `environments.yaml` |
| Step with backticks like `` `VAR` `` not substituted | Variable not yet set by a prior step |
| REST step not matching | Body contains single quotes — use double quotes inside JSON |
| "performs a X call at Y" not matching | Path must be in single quotes: `'/objects'` |
| Table step not matching | Step must end with `:` — e.g. `the response body should contain:` |
