# BDDFrame — Claude Instructions

## Commit message format

Every commit must follow this format exactly:

```
JIRA_ID worktype:Title of work

Short description of what this commit does
- did this
- did that
- fix this
- adds documentation
```

**JIRA_ID** — the ticket number (e.g. `BFRAME_0019`). Always ask the user if not clear from context.

**worktype** — one of:
- `feature` — new capability
- `fix` — bug fix
- `docs` — documentation only
- `refactor` — code restructure, no behaviour change
- `perf` — performance improvement
- `test` — test additions or changes
- `chore` — config, deps, tooling

**Gate: never push until the commit message matches this format.** If the format is wrong, fix the commit message before pushing.

Example:
```
BFRAME_0001 feature:adds baseline framework

this commit adds
- playwright
- selenium-like capabilities
- behave BDD runner
```

---

## Squash rule

**Max 1 commit per branch.** Whenever a branch has more than one commit, squash them all into one before doing any further work or pushing. The squashed commit message must still follow the format above, summarising all the work done.

To squash: `git reset --soft $(git merge-base HEAD main) && git commit` — or `git rebase -i HEAD~N` where N is the number of commits on the branch since it diverged from main.

---

## Branch naming

Branches follow the pattern `feature/BFRAME_XXXX` or `patch/BFRAME_XXXX`.

---

## General workflow rules

- Do not push to remote unless the user explicitly asks.
- Do not force-push to main/master.
- Always confirm before destructive git operations (reset --hard, branch -D, etc.).
