"""
Central configuration for the Product Intelligence module.

Data now comes directly from the shared knowledge_base/ folder (Person
4's real KB delivery), not from local placeholder CSVs. This is a
single source of truth - Person 4 updates knowledge_base/structured/*
and Product Intelligence picks it up on next reload(), no copying.
"""

from pathlib import Path

# ---- Paths -----------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent          # product_intelligence/
PROJECT_ROOT = BASE_DIR.parent                               # bis_navigator_v3/
KB_DIR = PROJECT_ROOT / "knowledge_base"

PRODUCTS_PATH = KB_DIR / "structured" / "products.json"
STANDARDS_PATH = KB_DIR / "structured" / "standards.json"
MAPPING_PATH = KB_DIR / "structured" / "product_standard_mapping.json"
DOCUMENTS_PATH = KB_DIR / "documents" / "documents.json"
CONFORMITY_ROUTES_PATH = KB_DIR / "structured" / "conformity_routes.json"

DATA_DIR = BASE_DIR / "data"  # still used for clarification_bank.json (P2-owned, not KB data)
CLARIFICATION_BANK_PATH = DATA_DIR / "clarification_bank.json"

# ---- Text normalization ------------------------------------------------
# Words that carry no signal about *which product* this is - strip them
# before matching so they don't dilute the vector.
FILLER_WORDS = {
    "i", "we", "am", "is", "are", "the", "a", "an", "of", "for", "to",
    "my", "our", "want", "would", "like", "need", "make", "makes",
    "making", "manufacture", "manufacturing", "manufacturer", "produce",
    "producing", "sell", "selling", "this", "that", "please", "help",
    "with", "and", "in", "on", "product", "company",
}

# ---- Confidence thresholds ---------------------------------------------
# top1_score below this -> we don't trust ANY candidate. Return "not_found"
# rather than forcing a clarification among categories that are all wrong.
# (This is the "absolute floor" - a relative gap alone is not enough,
# because two low, wrong scores can still be far apart from each other.)
ABSOLUTE_CONFIDENCE_FLOOR = 0.12

# top1_score above this -> confident enough to label "high" without asking
HIGH_CONFIDENCE_THRESHOLD = 0.45

# If (top1_score - top2_score) is smaller than this, the top two candidates
# are too close together to pick automatically -> trigger clarification.
AMBIGUITY_GAP_THRESHOLD = 0.09

# How many candidates to keep/report alongside the top pick
TOP_K_CANDIDATES = 3
