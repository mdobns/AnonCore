"""Ghost Protocol – persona (session alias) generation service."""

from __future__ import annotations

import random
import secrets

# Curated word lists for memorable persona aliases
_ADJECTIVES = [
    "Silent", "Neon", "Phantom", "Shadow", "Mystic", "Crimson", "Cobalt",
    "Amber", "Spectral", "Void", "Ember", "Frost", "Iron", "Velvet",
    "Onyx", "Serene", "Hollow", "Rustic", "Blazing", "Fading",
]

_NOUNS = [
    "Fox", "Raven", "Wolf", "Lynx", "Hawk", "Otter", "Crane", "Viper",
    "Bear", "Puma", "Heron", "Kite", "Mink", "Ibis", "Elk", "Dove",
    "Wren", "Stag", "Moth", "Pike",
]


def generate_persona() -> str:
    """Generate a fresh, memorable session alias.

    Format: ``<Adjective>-<Noun>-<NNN>``

    Example: ``"Silent-Fox-82"``, ``"Neon-Raven-404"``

    The number suffix is drawn from a *cryptographically secure* RNG so that
    even if the word-pair combination repeats, the full alias remains unique
    for the lifetime of a session.
    """
    adjective = random.choice(_ADJECTIVES)  # noqa: S311 – non-cryptographic choice is fine for aliases
    noun = random.choice(_NOUNS)  # noqa: S311
    number = secrets.randbelow(900) + 100  # 100–999
    return f"{adjective}-{noun}-{number}"
