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
