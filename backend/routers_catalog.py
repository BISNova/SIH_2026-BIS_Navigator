"""
GET /api/catalog/standards - every standard in the KB (for the Explore
Standards page - browsing, not tied to a single matched product).

GET /api/catalog/labs - every active testing lab in the KB.

Both reuse data already loaded by ProductIntelligencePipeline / the labs
loader in dependencies.py - no separate ingestion needed, and both
automatically reflect whatever Person 4 adds to knowledge_base/ next.
"""

import pandas as pd
from fastapi import APIRouter, HTTPException

from .models import CatalogStandardOut, CatalogLabOut
from .dependencies import (
    get_product_pipeline, get_labs_df,
    get_tests_df, get_certification_steps_df,
    get_inspection_requirements_df, get_schemes_df,
)

router = APIRouter()


def _is_mandatory(conformity_routes_df: pd.DataFrame, standard_id: str):
    """None means 'no conformity route on file yet', not 'not mandatory' -
    same convention used throughout product_intelligence/src/pipeline.py."""
    if conformity_routes_df.empty or "standard_id" not in conformity_routes_df.columns:
        return None
    match = conformity_routes_df[conformity_routes_df["standard_id"] == standard_id]
    if match.empty:
        return None
    return bool(match.iloc[0]["mandatory"])


def _safe(value):
    """pandas represents JSON null as NaN (a float) when a column has
    mixed types across rows - Optional[str] fields reject that. Convert
    any NaN/NaT to a real None. Lists/dicts (keywords, synonyms,
    variant_attributes, etc.) pass through unchanged - pd.isna() on a
    non-scalar raises ValueError, not something we ever want here."""
    if isinstance(value, (list, dict)):
        return value
    if pd.isna(value):
        return None
    return value


@router.get("/catalog/standards", response_model=list[CatalogStandardOut])
def list_standards():
    pipeline = get_product_pipeline()
    df = pipeline.standards_df

    return [
        CatalogStandardOut(
            standard_id=row["standard_id"],
            is_number=row["is_number_display"],
            title=row["title"],
            status=row["status"],
            scope_summary=_safe(row.get("scope_summary")),
            product_category=_safe(row.get("product_category")),
            is_mandatory=_is_mandatory(pipeline.conformity_routes_df, row["standard_id"]),
            source_url=_safe(row.get("source_url")),
            ask_query=f"Tell me about {row['is_number_display']} - {row['title']}",
        )
        for _, row in df.iterrows()
    ]


@router.get("/catalog/labs", response_model=list[CatalogLabOut])
def list_labs():
    df = get_labs_df()

    return [
        CatalogLabOut(
            lab_id=row["lab_id"],
            lab_name=row["lab_name"],
            lab_type=_safe(row.get("lab_type")),
            city=_safe(row.get("city")),
            district=_safe(row.get("district")),
            state=_safe(row.get("state")),
            contact=_safe(row.get("contact")),
            email=_safe(row.get("email")),
            phone=_safe(row.get("phone")),
            source_url=_safe(row.get("source_url")),
        )
        for _, row in df.iterrows()
    ]

def _records_for_standard(df: pd.DataFrame, standard_id: str) -> list[dict]:
    if df.empty or "standard_id" not in df.columns:
        return []
    return df[df["standard_id"] == standard_id].to_dict(orient="records")


def _clean(records: list[dict]) -> list[dict]:
    return [{k: _safe(v) for k, v in r.items()} for r in records]


@router.get("/catalog/checklist/{product_id}")
def get_product_checklist(product_id: str):
    pipeline = get_product_pipeline()

    product_row = pipeline.products_df[pipeline.products_df["product_id"] == product_id]
    if product_row.empty:
        raise HTTPException(status_code=404, detail="Product not found.")

    mapping_rows = pipeline.mapping_df[pipeline.mapping_df["product_id"] == product_id]
    standard_ids = mapping_rows["standard_id"].tolist()

    standards, conformity_routes = [], []
    tests, certification_steps, inspection_requirements = [], [], []
    scheme_ids = set()

    for std_id in standard_ids:
        std_row = pipeline.standards_df[pipeline.standards_df["standard_id"] == std_id]
        if not std_row.empty:
            standards.append(std_row.iloc[0].to_dict())

        tests += _records_for_standard(get_tests_df(), std_id)
        certification_steps += _records_for_standard(get_certification_steps_df(), std_id)
        inspection_requirements += _records_for_standard(get_inspection_requirements_df(), std_id)

        routes = _records_for_standard(pipeline.conformity_routes_df, std_id)
        conformity_routes += routes
        for r in routes:
            if r.get("scheme_id"):
                scheme_ids.add(r["scheme_id"])

    schemes_df = get_schemes_df()
    schemes = (
        schemes_df[schemes_df["scheme_id"].isin(scheme_ids)].to_dict(orient="records")
        if not schemes_df.empty and "scheme_id" in schemes_df.columns
        else []
    )

    return {
        "product": {k: _safe(v) for k, v in product_row.iloc[0].to_dict().items()},
        "standards": _clean(standards),
        "schemes": _clean(schemes),
        "conformity_routes": _clean(conformity_routes),
        "certification_steps": _clean(certification_steps),
        "tests": _clean(tests),
        "inspection_requirements": _clean(inspection_requirements),
    }


@router.get("/catalog/products")
def list_products():
    """Needed by the Dashboard's product picker - wasn't exposed before."""
    pipeline = get_product_pipeline()
    return [
        {"product_id": row["product_id"], "canonical_name": row["canonical_name"]}
        for _, row in pipeline.products_df.iterrows()
    ]