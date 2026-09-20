"""
GET /api/catalog/standards - every standard in the KB (for the Explore
Standards page - browsing, not tied to a single matched product).

GET /api/catalog/labs - every active testing lab in the KB.

Both reuse data already loaded by ProductIntelligencePipeline / the labs
loader in dependencies.py - no separate ingestion needed, and both
automatically reflect whatever Person 4 adds to knowledge_base/ next.
"""

import pandas as pd
from fastapi import APIRouter

from .models import CatalogStandardOut, CatalogLabOut
from .dependencies import get_product_pipeline, get_labs_df, get_ah_centres_df

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
    any NaN/NaT to a real None."""
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

@router.get("/catalog/hallmarking-centres")
def list_hallmarking_centres():
    df = get_ah_centres_df()

    return [
        {
            "ah_centre_id": row["ah_centre_id"],
            "centre_name": row["centre_name"],
            "recognition_number": _safe(row.get("recognition_number")),
            "centre_type": _safe(row.get("centre_type")),
            "address": _safe(row.get("address")),
            "state": _safe(row.get("state")),
            "district": _safe(row.get("district")),
            "city": _safe(row.get("city")),
            "contact": _safe(row.get("contact")),
            "email": _safe(row.get("email")),
            "phone": _safe(row.get("phone")),
            "gold_hallmarking": row.get("gold_hallmarking"),
            "silver_hallmarking": row.get("silver_hallmarking"),
            "recognition_status": _safe(row.get("recognition_status")),
            "validity_date": _safe(row.get("validity_date")),
            "source_url": _safe(row.get("source_url")),
        }
        for _, row in df.iterrows()
    ]