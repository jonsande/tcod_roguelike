"""Simple JSON-based translation helper.

Usage:
    from i18n import _
    _("Hello")

Keep translations in data/i18n/<lang>.json with keys as source strings.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

import settings


I18N_DIR = Path(__file__).parent / "data" / "i18n"

_catalog: Dict[str, str] = {}
_fallback_catalog: Dict[str, str] = {}


def _load_catalog(language: str) -> Dict[str, str]:
    """Load a JSON catalog for the given language or return an empty one."""
    path = I18N_DIR / f"{language}.json"
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def set_language(language: str | None = None) -> None:
    """Reload translation catalogs based on the given or configured language."""
    global _catalog, _fallback_catalog

    selected_language = language or getattr(settings, "LANGUAGE", "en")
    fallback_language = getattr(settings, "FALLBACK_LANGUAGE", "en")

    _catalog = _load_catalog(selected_language)
    _fallback_catalog = (
        {}
        if fallback_language == selected_language
        else _load_catalog(fallback_language)
    )


def _(message: str | None) -> str:
    """Return the translated string or the original message as a fallback."""
    if not message:
        return ""
    return _catalog.get(message) or _fallback_catalog.get(message) or message


# Load catalogs once at import time.
set_language()
