# POM Key Mapping — Feature File to pom.yaml

The POM key is whatever the step pattern extracts as the `locator` after stripping the grammatical subject (`User`, `I`), the article `the`, and the type suffix (`button`, `field`, `input`, `box`).

---

## How the extraction works

```
Step:    "User clicks the search button"
         ↓ strip subject
         "clicks the search button"
         ↓ pattern: clicks? (?:the )?(.+?) button$
         ↓ captures
locator: "search"
         ↓ pom.locate(page, "search")
YAML:    search: { css: "..." }
```

---

## Cheat sheet

| Step wording | POM key |
|---|---|
| `clicks the login button` | `login` |
| `clicks the first result` | `first result` |
| `clicks "Add to Cart"` | `Add to Cart` *(quoted = exact, no stripping)* |
| `enters X in the username field` | `username` |
| `enters X in the search input` | `search` |
| `fills in the search bar with X` | `search bar` |

---

## Working examples

### Ambiguous button — two search buttons on the page

```gherkin
# Feature file
When User clicks the header search button
```

```yaml
# pom.yaml
header search:          # "the" and "button" are stripped by the pattern
  css: "header button[aria-label='Search']"
```

---

### Unlabelled input — no placeholder, no aria-label

```gherkin
# Feature file
When User enters "mastercraft tool box" in the search input
```

```yaml
# pom.yaml
search:                 # "the" and "input" are stripped by the pattern
  css: "input[name='q']"
```

---

### Click a card/div with no accessible text

```gherkin
# Feature file
And User clicks the first product result
```

```yaml
# pom.yaml
first product result:   # "the" is stripped; no type suffix here
  css: ".product-tile:first-of-type a"
```

---

## Why not use `button_1` or arbitrary keys?

It works — `When User clicks button_1` maps to YAML key `button_1` — but the
feature file becomes unreadable and defeats the point of the framework. Use a
descriptive human name in the step; the same name (minus stripped words) is
the YAML key.

---

## Words stripped by each pattern

| Action | Stripped prefix | Stripped suffix |
|---|---|---|
| `clicks` | `the` | `button`, `link` |
| `enters … in` | `the` | `field`, `box`, `input` |
| `fills in` | `the` | *(none)* |
| `clicks "…"` | *(none — quoted, exact match)* | *(none)* |

When in doubt: run the step, watch the failure message — it prints the exact
string that was passed to the POM lookup, e.g.:

```
No match found for 'header search'
```

That string is your YAML key.

---

## The page-blindness problem

The POM lookup (`pom.py:_lookup`) is a **flat key scan** — it has no concept of
which page the browser is currently on. It iterates every key in the YAML and
returns the first match.

This creates two concrete problems:

**1. YAML silently drops duplicate keys.**

```yaml
# BAD — second entry overwrites the first. The home page search is gone.
search:
  css: "input.home-search"
search:
  css: "input.results-filter"
```

**2. A key written for one page will fire on a different page if the locator
happens to match.**

---

## How to handle the same element on different pages

### Fix 1 — page-prefixed keys (recommended, works today)

Include the page or section in the key name. The feature file step must use the
same prefix so the extracted locator matches.

```yaml
# pom.yaml
home search:
  css: "input.home-search"

results search:
  css: "input.results-filter"
```

```gherkin
# Feature file — home page step
When User enters "mastercraft tool box" in the home search input

# Feature file — search results page step
When User clears the results search input
```

The pattern strips `the` and `input` — so `home search input` → key `home search`. ✓

---

### Fix 2 — XPath axis selectors (scope by container, not position)

When elements are structurally identical but live inside different containers,
use an XPath axis to scope to the right parent. This is safer than positional
index (`[1]`, `[2]`) because it survives DOM reordering.

```yaml
# Scope to the page header
header search:
  xpath: "//header//input[@type='search']"

# Scope to the sidebar filter panel
sidebar search:
  xpath: "//aside//input[@type='search']"

# Positional index — last resort, fragile if layout changes
first search bar:
  xpath: "(//input[@type='search'])[1]"
```

```gherkin
When User enters "drill" in the header search input
When User enters "cordless" in the sidebar search input
```

---

### Comparison

| Approach | Readable step? | Stable? | When to use |
|---|---|---|---|
| Page-prefixed key | ✅ | ✅ | Default — always try this first |
| XPath axis (container) | ✅ | ✅ | Two identical elements in different containers |
| XPath positional `[1]` | ⚠️ | ❌ fragile | Last resort — no other structural difference |
| Arbitrary key (`search_2`) | ❌ | ✅ | Never — makes feature file unreadable |

---

## Current limitation — no URL-based page scoping

There is no mechanism today to say "use this selector only when the browser is
on `/search`." The `_lookup` function in `pom.py` receives only a text key — it
does not have access to the current page URL.

A page-scoped YAML structure would look like this, but **it is not implemented**:

```yaml
# Proposed — not implemented
pages:
  home:
    url_contains: "canadiantire.ca/$"
    search:
      css: "input.home-search"

  search results:
    url_contains: "/search"
    search:
      css: "input.results-filter"
```

For this to work, `pom.py` would need the current `page.url` passed in at
lookup time so it could filter by `url_contains` before scanning keys.

Until that is built, **page-prefixed key naming is the correct workaround.**
The naming convention is explicit, requires no code change, and makes the
feature file self-documenting about which page the step is acting on.
