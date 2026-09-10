"""
Given the two products that are currently tied/ambiguous, find the best
clarification question to ask. Prefers a specific, pre-written question for
that exact pair (data/clarification_bank.json); falls back to a generic one
so the system never has "no question to show" as a failure mode.
"""

from typing import List, Tuple
from .schemas import ClarificationOption


def _pair_key(id_1: str, id_2: str) -> str:
    return ",".join(sorted([id_1, id_2]))


def get_clarification(
    top_two_product_ids: Tuple[str, str],
    clarification_bank: dict,
) -> Tuple[str, List[ClarificationOption]]:
    key = _pair_key(*top_two_product_ids)
    entry = clarification_bank.get(key, clarification_bank["_default"])

    question = entry["question"]
    options = [ClarificationOption(**opt) for opt in entry.get("options", [])]
    return question, options
