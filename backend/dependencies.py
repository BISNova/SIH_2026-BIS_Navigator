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

