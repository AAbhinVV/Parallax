"""K3.1 task identity: a stable operational fingerprint for a task prompt.

Two phrasings of the same operational task must resolve to the same
fingerprint so later assignments can be recognized without the user
repeating all the context.
"""

import hashlib


def normalize_task_prompt(prompt: str) -> str:
    """Case- and whitespace-insensitive normalization of a task prompt."""
    return " ".join(prompt.lower().split())


def task_fingerprint(prompt: str) -> str:
    """SHA-256 of the normalized prompt: same operational task -> same fingerprint."""
    return hashlib.sha256(normalize_task_prompt(prompt).encode("utf-8")).hexdigest()
