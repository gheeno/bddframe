# Writing a Test — Step by Step

Two walkthroughs: a **happy path** where every element resolves on its own, and
a **problematic-locator** path where you have to help the framework. Both use
the public saucedemo site and run as-is.

Prereqs: `pip install -e .`, Playwright browsers installed
(`playwright install chromium`), and a `.env` with `SAUCE_USERNAME` /
`SAUCE_PASSWORD` (saucedemo creds are `standard_user` / `secret_sauce`).

---

## Part 1 — Happy path

Goal: log in, confirm the products page. Every element here has visible text or
a placeholder, so the accessibility tree finds it. **No pom.yaml needed.**

### Step 1 — make a folder and a feature file

```
features/login/login.feature
```

### Step 2 — write the scenario in plain sentences

```gherkin
@web @headless
Feature: Login

  Scenario: Standard user logs in
    Given User is on "https://www.saucedemo.com"
    When User enters [SAUCE_USERNAME] in the username field
    And User enters [SAUCE_PASSWORD] in the password field
    And User clicks the login button
    Then User should see "Products"
```

Why each step resolves with zero config:

| Step | Resolves via |
|------|--------------|
| `... username field` | input placeholder "Username" |
| `... password field` | input placeholder "Password" |
| `clicks the login button` | button accessible name "Login" |
| `should see "Products"` | plain DOM text |

`[SAUCE_USERNAME]` is replaced from `.env` at runtime (`[VAR]` → env `VAR`).

### Step 3 — run it

```
behave features/login --no-capture
```

Expect `1 scenario passed`. Done — that is a complete, real test with no
selectors and no Python.

---

## Part 2 — Problematic locators

Three problems you will actually hit, and the fix for each. Problem A runs live
in `features/fallback-demo/`; Problem B reproduces on the saucedemo products
page; Problem C's selectors are illustrative (saucedemo has no second search).

### Problem A — element has no readable label (icon-only button)

Saucedemo's burger menu is `<button id="react-burger-menu-btn">Open Menu</button>`
— the text is visually hidden, so `clicks the burger menu` finds **nothing** on
the accessibility tree.

**Symptom when you run it:**
```
Assertion Failed: Could not find element to click: 'burger menu'
```

**Fix:** add a `pom.yaml` next to the feature with the explicit selector. The
key is the step label minus `the` (see [pom-key-mapping.md](pom-key-mapping.md)).

```yaml
# features/fallback-demo/pom.yaml
burger menu:
  id: react-burger-menu-btn
```

Re-run — now you see the fallback fire:
```
📋 POM: resolved 'burger menu' via pom.yaml
```

### Problem B — the label matches MANY elements (ambiguous)

The products page has six identical "Add to cart" buttons. `clicks "Add to cart"`
matches all six. By default the framework warns and clicks the first:

```
⚠️  Ambiguous locator 'Add to cart' — matched multiple elements:
    [0] <button> 'Add to cart'
    [1] <button> 'Add to cart'
    ...
```

**Two ways to handle it:**

1. **Make CI strict** so ambiguity fails instead of guessing — add the
   `@strict` tag (or set `BDDFRAME_STRICT_LOCATOR=true`). The step then fails
   with the candidate list above, telling you to disambiguate.

2. **Scope it in pom.yaml** with an xpath/css that targets the one you mean:

   ```yaml
   add to cart:
     xpath: "(//button[contains(.,'Add to cart')])[1]"   # or a container scope
   ```

   A POM entry is always used *before* the blind first-match, so this wins.

### Problem C — same label, different element per page

`search` means the home search bar on `/` but the results filter on `/search`.
A flat key can't be both. Scope by URL:

```yaml
pages:
  home:
    match: { url_contains: "saucedemo.com/$" }
    search: { css: "input.home-search" }
  results:
    match: { url_contains: "/inventory" }
    search: { css: "input.results-filter" }
```

The framework reads the live URL and picks the right block automatically.
For single-page apps where the URL never changes, pin it instead:

```gherkin
Given User is on the "results" page
```

---

## The resolution order (what the framework tries, in order)

```
1. Accessibility tree — role / label / placeholder / text   (Problem-free case)
2. If MANY match → ambiguity: POM scoped entry, else warn/fail   (Problem B)
3. Self-heal: scroll, then partial-text retry
4. POM yaml — page-scoped block, then shared, then flat keys   (Problems A & C)
5. Vision LLM (only if BDDFRAME_MODEL is set)
```

Write the happy-path steps first and run them. Only reach for `pom.yaml` when a
step actually fails or warns — the failure message prints the exact key to use.
