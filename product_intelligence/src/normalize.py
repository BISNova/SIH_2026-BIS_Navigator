"""
Text normalization for incoming product descriptions.

Kept deliberately simple (no stemming/lemmatization library) so it has
zero extra dependencies and is easy to reason about under time pressure.
If Day 2 testing shows real queries need it, this is the one place to
extend (e.g. add a stemmer here) - nothing else in the pipeline should
need to change.
"""

import re
from .config import FILLER_WORDS


def normalize(text: str) -> str:
    """
    'I want to manufacture Stainless Steel Pressure Cookers!!'
      -> 'stainless steel pressure cookers'
    """
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)  # strip punctuation
    tokens = text.split()
    tokens = [t for t in tokens if t not in FILLER_WORDS]
    return " ".join(tokens).strip()
