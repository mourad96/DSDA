"""Text normalization utilities for robust toponym matching."""

from __future__ import annotations

import re
import unicodedata


def strip_accents(text: str) -> str:
    """Remove diacritics/accents from characters (e.g. 'Béni' -> 'Beni')."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalize_toponym(text: str) -> str:
    """Normalize a toponym for string distance matching.

    Performs accent removal, lowercasing, abbreviation dot normalization,
    and whitespace collapsing.
    """
    if not text:
        return ""
    text = strip_accents(text).lower()
    # Normalize common abbreviations like 'b.' or 'st.' -> keep single spaced token
    text = re.sub(r"[._\-/]", " ", text)
    # Remove any character that is not alphanumeric or whitespace
    text = re.sub(r"[^\w\s]", "", text)
    # Collapse multiple spaces
    text = re.sub(r"\s+", " ", text).strip()
    return text
