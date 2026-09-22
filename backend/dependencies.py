"""
Builds the ProductIntelligencePipeline singleton (expensive to
construct - KB loading - built once, cached for the process lifetime).

P1 is no longer imported in-process at all - it's a separate HTTP
service now (see integration/p1_client.py). There's nothing to cache
here for it beyond the base URL, which lives in config.py.
"""

import sys
import json
from pathlib import Path
from functools import lru_cache

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

KB_DIR = PROJECT_ROOT / "knowledge_base"
LABS_PATH = KB_DIR / "structured" / "labs.json"

TESTS_PATH = KB_DIR / "structured" / "tests.json"
CERTIFICATION_STEPS_PATH = KB_DIR / "structured" / "certification_steps.json"
INSPECTION_REQUIREMENTS_PATH = KB_DIR / "structured" / "inspection_requirements.json"
SCHEMES_PATH = KB_DIR / "structured" / "schemes.json"


def _load_json_df(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    with open(path, encoding="utf-8") as f:
        records = json.load(f)
    return pd.DataFrame(records) if records else pd.DataFrame()


@lru_cache
def get_tests_df() -> pd.DataFrame:
    return _load_json_df(TESTS_PATH)


@lru_cache
def get_certification_steps_df() -> pd.DataFrame:
    return _load_json_df(CERTIFICATION_STEPS_PATH)


@lru_cache
def get_inspection_requirements_df() -> pd.DataFrame:
    return _load_json_df(INSPECTION_REQUIREMENTS_PATH)


@lru_cache
def get_schemes_df() -> pd.DataFrame:
    return _load_json_df(SCHEMES_PATH)





@lru_cache
def get_product_pipeline():
    from product_intelligence.src.pipeline import ProductIntelligencePipeline
    return ProductIntelligencePipeline()


@lru_cache
def get_labs_df() -> pd.DataFrame:
    """
    Labs aren't part of product matching, so they're not loaded by
    ProductIntelligencePipeline - this is a separate, small, direct
    load straight from the shared knowledge_base/, only for the catalog
    endpoints in routers_catalog.py.
    """
    with open(LABS_PATH, encoding="utf-8") as f:
        records = json.load(f)
    df = pd.DataFrame(records)
    if "status" in df.columns:
        df = df[df["status"] == "active"].reset_index(drop=True)
    return df


@lru_cache
def get_session_store():
    from .session_store import ConversationSessionStore
    return ConversationSessionStore()


@lru_cache
def get_query_cache():
    from .query_cache import QueryResultCache
    return QueryResultCache()


@lru_cache
def get_feedback_store():
    from .feedback_store import FeedbackStore
    return FeedbackStore()


@lru_cache
def get_staging_queue():
    from .kb_updater.staging import ChangeStagingQueue
    return ChangeStagingQueue()

