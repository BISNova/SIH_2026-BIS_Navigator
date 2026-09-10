"""
Loads Person 4's REAL KB (JSON), not placeholder CSVs.

Real-data quirks handled here, deliberately isolated to this one file:
  - keywords/synonyms are JSON arrays, not comma-strings
  - typical_use is sometimes a string, sometimes a list (inconsistent
    across product rows in the real data) - _as_text() below normalizes
    either shape into a flat string for search_text construction
  - relationship_type values are "primary"/"secondary" (not the
    "mandatory"/"related" the placeholder data used)
  - "legally mandatory" is NOT on the mapping row at all - it lives in
    conformity_routes.json, joined here by standard_id
"""

import json
import pandas as pd
from .config import (
    PRODUCTS_PATH,
    STANDARDS_PATH,
    MAPPING_PATH,
    DOCUMENTS_PATH,
    CONFORMITY_ROUTES_PATH,
    CLARIFICATION_BANK_PATH,
)

REQUIRED_PRODUCT_COLUMNS = {
    "product_id", "canonical_name", "category", "subcategory",
    "keywords", "synonyms", "typical_use", "material", "active",
}
REQUIRED_STANDARD_COLUMNS = {
    "standard_id", "is_number", "title", "status", "scope_summary",
}
REQUIRED_MAPPING_COLUMNS = {
    "mapping_id", "product_id", "standard_id", "relationship_type",
    "clarification_required", "source_document_id",
}


def _as_text(value) -> str:
    """Real data has typical_use as either a string or a list - and
    keywords/synonyms are always lists. Normalize any of these into one
    flat, lowercased string for the search index."""
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(str(v) for v in value)
    return str(value)


def _load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_products(path=PRODUCTS_PATH) -> pd.DataFrame:
    records = _load_json(path)
    df = pd.DataFrame(records)

    missing = REQUIRED_PRODUCT_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"products.json missing required columns: {missing}")

    df = df[df["active"] == True].reset_index(drop=True)  # noqa: E712

    for col in ["subcategory", "material"]:
        df[col] = df[col].fillna("")

    # search_text is what gets vectorized - flatten list-typed fields first
    df["search_text"] = (
        df["canonical_name"].apply(_as_text) + " "
        + df["category"].apply(_as_text) + " "
        + df["subcategory"].apply(_as_text) + " "
        + df["keywords"].apply(_as_text) + " "
        + df["synonyms"].apply(_as_text) + " "
        + df["typical_use"].apply(_as_text) + " "
        + df["material"].apply(_as_text)
    ).str.lower()

    # keep flattened, display-friendly versions of the list fields too,
    # so the pipeline doesn't need to know about the raw JSON shape
    df["material_display"] = df["material"].apply(_as_text)
    df["typical_use_display"] = df["typical_use"].apply(_as_text)

    return df


def load_standards(path=STANDARDS_PATH) -> pd.DataFrame:
    records = _load_json(path)
    df = pd.DataFrame(records)
    missing = REQUIRED_STANDARD_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"standards.json missing required columns: {missing}")

    # Real data stores is_number as a bare number ("2347") and the full
    # designation needs the edition year: "IS 2347:2023". Some standards
    # share an is_number+year but differ by part/section (e.g. IS 302
    # Part 1 vs Part 2 Section 21) - include those when present so two
    # genuinely different standards don't display identically.
    def _build_display(r):
        display = f"IS {r['is_number']}"
        if pd.notna(r.get("edition_year")):
            display += f":{int(r['edition_year'])}"
        if pd.notna(r.get("part")) and r.get("part"):
            display += f" ({r['part']}"
            if pd.notna(r.get("section")) and r.get("section"):
                display += f", {r['section']}"
            display += ")"
        return display

    df["is_number_display"] = df.apply(_build_display, axis=1)
    return df


def load_mapping(path=MAPPING_PATH) -> pd.DataFrame:
    records = _load_json(path)
    df = pd.DataFrame(records)
    missing = REQUIRED_MAPPING_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"product_standard_mapping.json missing required columns: {missing}")
    if "active" in df.columns:
        df = df[df["active"] == True].reset_index(drop=True)  # noqa: E712
    return df


def load_documents(path=DOCUMENTS_PATH) -> pd.DataFrame:
    records = _load_json(path)
    return pd.DataFrame(records)


def load_conformity_routes(path=CONFORMITY_ROUTES_PATH) -> pd.DataFrame:
    """Real 'is this legally mandatory' signal - NOT on the mapping row.
    Only some standards have a route entry in this sample; standards
    without one get is_mandatory=None (unknown), not False."""
    records = _load_json(path)
    return pd.DataFrame(records)


def load_clarification_bank(path=CLARIFICATION_BANK_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
