"""bddframe-agent — an interactive shell that maps plain English to engine
commands. Keyword matching, no LLM required (Phase 2). `create test` uses the
rule-based generator (Phase 3); `--llm ollama|claude` upgrades generation and
summaries to a model (Phases 3/5). All it does is shell out to `bddframe ...`.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

from bddframe import config

# --llm name -> default model string litellm understands. User can override
# with --model. Paid providers still need the matching API key in the env.
_LLM_MODELS = {
    "ollama": "ollama/llama3.2",
    "claude": "anthropic/claude-sonnet-4-6",
    "gemini": "gemini/gemini-1.5-flash",
}

HELP = """commands (plain English works too):
  run [all]                 run every feature
  run <name|tag>            run a feature file or a tag
  list / what tests         list scenarios
  create test for <desc> at <url>   scaffold a feature + POM
  summary / what failed     summarise the last run
  help                      this message
  quit / exit               leave
"""


def _bddframe(*args, workspace="."):
    """Invoke the engine CLI in the workspace dir so it finds the right config."""
    subprocess.run([sys.executable, "-m", "bddframe.cli", *args], cwd=workspace)


def _features(cfg, workspace):
    return Path(workspace) / cfg["features_dir"]


def _find_feature(cfg, workspace, name) -> str | None:
    fdir = _features(cfg, workspace)
    if not fdir.is_dir():
        return None
    for f in fdir.rglob("*.feature"):
        if name.lower() in f.stem.lower():
            return str(f.relative_to(workspace))
    return None


def dispatch(line: str, cfg: dict, workspace: str, llm: str | None) -> bool:
    """Run one command. Returns False to exit the REPL, True to keep going."""
    text = line.strip()
    low = text.lower()
    if not text:
        return True
    if low in {"quit", "exit", "q"}:
        return False
    if low in {"help", "?"}:
        print(HELP)
        return True

    if low in {"list", "what tests", "what tests do we have", "list all scenarios"}:
        _bddframe("list", cfg["features_dir"], workspace=workspace)
        return True

    if re.search(r"\b(summary|what failed|report)\b", low):
        _bddframe("summary", "--llm", llm or "none", workspace=workspace)
        return True

    m = re.search(r"create (?:a )?test (?:for )?(.+?)(?: at | on )(https?://\S+)", text, re.I)
    if m:
        from bddframe.agent import generate
        desc, url = m.group(1).strip(), m.group(2).strip()
        gen = generate.generate_llm if llm else generate.generate
        feat, pom = gen(desc, url, cfg, workspace)
        print(f"→ Wrote {feat}\n→ Wrote {pom}\n→ Run: bddframe run {feat}")
        return True

    if low.startswith("run"):
        rest = text[3:].strip()
        if not rest or rest.lower() in {"all", "all tests", "the tests", "everything"}:
            _bddframe("run", cfg["features_dir"], workspace=workspace)
            return True
        # strip filler: "run the smoke tests" -> "smoke"
        target = re.sub(r"\b(the|tests?|test|please)\b", "", rest, flags=re.I).strip()
        feat = _find_feature(cfg, workspace, target)
        if feat:
            _bddframe("run", feat, workspace=workspace)
        else:
            _bddframe("run", cfg["features_dir"], "--tag", target, workspace=workspace)
        return True

    print(f"Don't understand: {text!r}. Type 'help'.")
    return True


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    workspace, llm, model = ".", None, None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--workspace":
            workspace = argv[i + 1]; i += 2
        elif a == "--llm":
            llm = argv[i + 1]; i += 2
        elif a == "--model":
            model = argv[i + 1]; i += 2
        else:
            i += 1

    if llm:
        os.environ["BDDFRAME_MODEL"] = model or _LLM_MODELS.get(llm, llm)
        if llm == "ollama":
            os.environ.setdefault("BDDFRAME_LLM_URL", "http://localhost:11434")

    cfg = config.load(workspace)
    print(f"bddframe-agent — workspace: {Path(workspace).resolve()}"
          + (f"  llm: {os.environ['BDDFRAME_MODEL']}" if llm else "  (rule-based, no LLM)"))
    print("Type 'help' for commands, 'quit' to exit.\n")
    try:
        while True:
            try:
                line = input("bddframe> ")
            except EOFError:
                break
            if not dispatch(line, cfg, workspace, llm):
                break
    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()
