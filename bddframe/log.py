"""Structured logging for BDDFrame.

One logger, level from BDDFRAME_LOG_LEVEL (default INFO). Messages keep the
emoji breadcrumbs that the runtime always printed — the formatter just passes
them through, so console output looks the same but is now level-gated and
silenceable (BDDFRAME_LOG_LEVEL=WARNING in noisy CI).

ponytail: the handler writes to the *live* sys.stdout on every emit (not the
sys.stdout captured at import) so pytest's capsys still sees our output and
behave's own stdout interleaving stays correct.
"""
import logging
import os
import sys

logger = logging.getLogger("bddframe")


class _LiveStdoutHandler(logging.StreamHandler):
    """StreamHandler that always targets the current sys.stdout."""

    @property
    def stream(self):
        return sys.stdout

    @stream.setter
    def stream(self, _value):
        pass  # ignore the base class's captured stream


def _configure():
    if getattr(logger, "_bddframe_configured", False):
        return
    handler = _LiveStdoutHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.propagate = False
    set_level(os.getenv("BDDFRAME_LOG_LEVEL", "INFO"))
    logger._bddframe_configured = True


def set_level(level: str):
    """Set the bddframe log level from a name ('INFO', 'WARNING', ...)."""
    logger.setLevel(getattr(logging, str(level).upper(), logging.INFO))


_configure()
