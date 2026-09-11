"""
Builds the ProductIntelligencePipeline singleton (expensive to
construct - KB loading - built once, cached for the process lifetime).

P1 is no longer imported in-process at all - it's a separate HTTP
service now (see integration/p1_client.py). There's nothing to cache
here for it beyond the base URL, which lives in config.py.
"""

import sys
from pathlib import Path
from functools import lru_cache

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@lru_cache
def get_product_pipeline():
    from product_intelligence.src.pipeline import ProductIntelligencePipeline
    return ProductIntelligencePipeline()
