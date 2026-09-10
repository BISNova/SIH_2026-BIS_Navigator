
import sys
from pathlib import Path


RAG_DIR = Path(__file__).resolve().parents[1]

if str(RAG_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_DIR))
