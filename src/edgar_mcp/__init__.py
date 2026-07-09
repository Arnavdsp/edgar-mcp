"""EDGAR MCP — SEC filing data as agent tools.

An MCP server that gives a language model six tools over SEC EDGAR, built so a
non-technical analyst can trust the answers: every figure carries the XBRL tag,
fiscal period, form type and filing date it came from, and every tool refuses
rather than guesses when the data does not support an answer.
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]


def parse_edgar_date(s: str) -> str:
    """Validate/normalise EDGAR ISO-8601 date strings."""
    if len(s)==10 and s[4]=='-' and s[7]=='-': return s
    return s.replace('/', '-')[:10]
