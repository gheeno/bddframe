"""
BDDFrame Language Server
Validates .feature steps against patterns.py and provides tag/variable completions.
"""
import os
import re
from pathlib import Path
from urllib.parse import urlparse, unquote

from lsprotocol import types as lsp
from pygls.lsp.server import LanguageServer

from bddframe.resolver.patterns import match as pattern_match, normalize_subject

server = LanguageServer("bddframe-lsp", "v0.1")

_SEVERITY_MAP = {
    "warning":     lsp.DiagnosticSeverity.Warning,
    "information": lsp.DiagnosticSeverity.Information,
    "none":        None,
}
_UNKNOWN_STEP_SEVERITY = _SEVERITY_MAP.get(
    os.getenv("BDDFRAME_UNKNOWN_STEP_SEVERITY", "warning"),
    lsp.DiagnosticSeverity.Warning,
)

STEP_KEYWORDS = ("Given ", "When ", "Then ", "And ", "But ")

KNOWN_TAGS = [
    ("web",          "Run with Playwright browser"),
    ("headless",     "No visible browser — CI mode"),
    ("visual",       "Run with OpenCV desktop agent"),
    ("mobile",       "Run with Appium"),
    ("smoke",        "Include in smoke test subset"),
    ("retry(3)",     "Retry up to N times on failure"),
    ("record_video", "Record a video of this scenario"),
    ("baseline",     "Force a fresh visual baseline screenshot"),
]


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _validate(source: str) -> list[lsp.Diagnostic]:
    diagnostics = []
    for i, line in enumerate(source.splitlines()):
        stripped = line.strip()
        for kw in STEP_KEYWORDS:
            if stripped.startswith(kw):
                step_text = stripped[len(kw):]
                normalized = normalize_subject(step_text)
                if pattern_match(normalized) is None and _UNKNOWN_STEP_SEVERITY is not None:
                    col = len(line) - len(line.lstrip())
                    diagnostics.append(lsp.Diagnostic(
                        range=lsp.Range(
                            start=lsp.Position(line=i, character=col),
                            end=lsp.Position(line=i, character=len(line.rstrip())),
                        ),
                        message="No built-in pattern matched — LLM will resolve at runtime.",
                        severity=_UNKNOWN_STEP_SEVERITY,
                        source="bddframe",
                        code="llm-fallback",
                    ))
                break
    return diagnostics


@server.feature(lsp.TEXT_DOCUMENT_DID_OPEN)
def did_open(ls: LanguageServer, params: lsp.DidOpenTextDocumentParams):
    diags = _validate(params.text_document.text)
    ls.text_document_publish_diagnostics(
        lsp.PublishDiagnosticsParams(uri=params.text_document.uri, diagnostics=diags)
    )


@server.feature(lsp.TEXT_DOCUMENT_DID_CHANGE)
def did_change(ls: LanguageServer, params: lsp.DidChangeTextDocumentParams):
    doc = ls.workspace.get_document(params.text_document.uri)
    diags = _validate(doc.source)
    ls.text_document_publish_diagnostics(
        lsp.PublishDiagnosticsParams(uri=params.text_document.uri, diagnostics=diags)
    )


@server.feature(lsp.TEXT_DOCUMENT_DID_SAVE)
def did_save(ls: LanguageServer, params: lsp.DidSaveTextDocumentParams):
    doc = ls.workspace.get_document(params.text_document.uri)
    diags = _validate(doc.source)
    ls.text_document_publish_diagnostics(
        lsp.PublishDiagnosticsParams(uri=params.text_document.uri, diagnostics=diags)
    )


# ---------------------------------------------------------------------------
# Completions — @tags and [variables]
# ---------------------------------------------------------------------------

@server.feature(
    lsp.TEXT_DOCUMENT_COMPLETION,
    lsp.CompletionOptions(trigger_characters=["@", "["]),
)
def completion(ls: LanguageServer, params: lsp.CompletionParams) -> lsp.CompletionList:
    doc = ls.workspace.get_document(params.text_document.uri)
    line = doc.lines[params.position.line]
    prefix = line[: params.position.character]
    items = []

    if re.search(r"@\w*$", prefix):
        for tag, detail in KNOWN_TAGS:
            items.append(lsp.CompletionItem(
                label=f"@{tag}",
                kind=lsp.CompletionItemKind.EnumMember,
                detail=detail,
                insert_text=tag,  # @ is already typed as the trigger character
            ))

    elif "[" in prefix and "]" not in prefix[prefix.rfind("["):]:
        uri_path = unquote(urlparse(params.text_document.uri).path)
        for name in _env_var_names(uri_path):
            items.append(lsp.CompletionItem(
                label=f"[{name}]",
                kind=lsp.CompletionItemKind.Variable,
                detail="from .env",
                insert_text=name + "]",  # [ is already typed
            ))

    return lsp.CompletionList(is_incomplete=False, items=items)


def _env_var_names(doc_path: str) -> list[str]:
    """Walk up from the document directory, find .env, return variable name suggestions."""
    start = Path(doc_path).parent if doc_path else Path.cwd()
    for directory in [start, *start.parents]:
        env_file = directory / ".env"
        if env_file.exists():
            names = []
            for line in env_file.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key = line.split("=", 1)[0].strip()
                    names.append(key)
                    names.append(key.lower().replace("_", " "))
            return names
    return []


# ---------------------------------------------------------------------------

def main():
    server.start_io()


if __name__ == "__main__":
    main()
