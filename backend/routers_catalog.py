"""
GET /api/catalog/standards - every standard in the KB (for the Explore
Standards page - browsing, not tied to a single matched product).

GET /api/catalog/labs - every active testing lab in the KB.

Both reuse data already loaded by ProductIntelligencePipeline / the labs
loader in dependencies.py - no separate ingestion needed, and both
automatically reflect whatever Person 4 adds to knowledge_base/ next.
"""

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from backend.auth.dependencies import get_current_user
from backend.database import supabase

from .models import (
    CatalogStandardOut,
    CatalogLabOut,
    ChecklistResponse,
    ChecklistCertificationStepOut,
    ChecklistTestOut,
    ChecklistProgressRequest,
    ChecklistProgressResponse,
)

from .dependencies import (
    get_product_pipeline,
    get_labs_df,
    get_ah_centres_df,
    get_certification_steps,
    get_tests,
    get_inspection_requirements,
    get_schemes_df,
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


def _clean_records(records: list[dict]) -> list[dict]:
    return [{k: _safe(v) for k, v in r.items()} for r in records]


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

@router.get("/catalog/products")
def list_products():
    """Needed by the Dashboard's product picker - wasn't exposed before."""
    pipeline = get_product_pipeline()
    return [
        {"product_id": row["product_id"], "canonical_name": row["canonical_name"]}
        for _, row in pipeline.products_df.iterrows()
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

@router.get("/catalog/checklist/{product_id}", response_model=ChecklistResponse)
def get_checklist(product_id: str):
    pipeline = get_product_pipeline()

    # Find the requested product.
    product_matches = pipeline.products_df[
        pipeline.products_df["product_id"] == product_id
    ]

    if product_matches.empty:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=404,
            detail=f"Product '{product_id}' not found",
        )

    product_row = product_matches.iloc[0]
    product = product_row.to_dict()

    # Existing pipeline logic already knows how to map
    # product_id -> applicable standards.
    standards = pipeline._lookup_standards(product_id)

    # certification_steps.json is grouped by standard_id.
    certification_records = get_certification_steps()
    certification_steps = []

    standard_ids = {standard.standard_id for standard in standards}

    for record in certification_records:
        if record.get("standard_id") in standard_ids:
            certification_steps.extend(record.get("steps", []))

    # tests.json contains one test record per entry and has standard_id.
    test_records = get_tests()

    tests = [
        record
        for record in test_records
        if record.get("standard_id") in standard_ids
    ]

    # Currently the KB file is empty, so this naturally returns [].
    inspection_records = get_inspection_requirements()

    # Conformity routes (mandatory/voluntary + how-to-apply) and the
    # certification schemes they point at, scoped to this product's
    # standards - same conformity_routes_df the pipeline already uses
    # for the is_mandatory flag elsewhere.
    conformity_routes_df = pipeline.conformity_routes_df
    if not conformity_routes_df.empty and "standard_id" in conformity_routes_df.columns:
        route_rows = conformity_routes_df[conformity_routes_df["standard_id"].isin(standard_ids)]
    else:
        route_rows = conformity_routes_df.iloc[0:0]
    conformity_routes = route_rows.to_dict(orient="records")

    scheme_ids = {r.get("scheme_id") for r in conformity_routes if r.get("scheme_id")}
    schemes_df = get_schemes_df()
    if scheme_ids and not schemes_df.empty and "scheme_id" in schemes_df.columns:
        schemes = schemes_df[schemes_df["scheme_id"].isin(scheme_ids)].to_dict(orient="records")
    else:
        schemes = []

    return ChecklistResponse(
        product=product,
        standards=[standard.model_dump() for standard in standards],
        schemes=_clean_records(schemes),
        conformity_routes=_clean_records(conformity_routes),
        certification_steps=[
            ChecklistCertificationStepOut(**step)
            for step in certification_steps
        ],
        tests=[
            ChecklistTestOut(**test)
            for test in tests
        ],
        inspection_requirements=inspection_records,
    )

@router.post(
    "/checklist/progress",
    response_model=ChecklistProgressResponse,
)
def save_checklist_progress(
    request: ChecklistProgressRequest,
    current_user=Depends(get_current_user),
):
    user_id = str(current_user["id"])

    progress = {
        "user_id": user_id,
        "product_id": request.product_id,
        "completed_step_ids": request.completed_step_ids,
    }

    try:
        result = (
            supabase
            .table("checklist_progress")
            .upsert(
                progress,
                on_conflict="user_id,product_id",
            )
            .execute()
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to save checklist progress",
        ) from exc

    if not result.data:
        raise HTTPException(
            status_code=500,
            detail="Checklist progress was not saved",
        )

    return result.data[0]
@router.get(
    "/checklist/progress",
    response_model=list[ChecklistProgressResponse],
)
def get_checklist_progress(
    product_id: str | None = None,
    current_user=Depends(get_current_user),
):
    user_id = str(current_user["id"])

    try:
        query = (
            supabase
            .table("checklist_progress")
            .select("*")
            .eq("user_id", user_id)
        )

        if product_id:
            query = query.eq("product_id", product_id)

        result = query.execute()

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch checklist progress",
        ) from exc

    return result.data
