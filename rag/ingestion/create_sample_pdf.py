from pathlib import Path
import pymupdf

# Navigate from rag/ingestion/ to the project root (SIH_2026-BIS_Navigator)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
output_path = PROJECT_ROOT / "data" / "raw" / "sample_bis.pdf"

# Ensure the 'data/raw' directories exist before saving
output_path.parent.mkdir(parents=True, exist_ok=True)

document = pymupdf.open()

page = document.new_page()

text = """
Sample BIS Product Standard
Testing Document

Clause 5 — Product Requirements

5.1 The product shall be manufactured using suitable materials.

5.2 The product shall satisfy the specified dimensional requirements.

5.3 The product shall undergo the applicable quality and safety tests.

Clause 6 — Testing Requirements

6.1 Testing shall be carried out using the prescribed test procedure.

6.2 Test results shall be recorded and maintained for verification.

Clause 7 — Marking Requirements

7.1 The product shall carry the required identification and marking information.
"""

page.insert_text((72, 72), text, fontsize=12)

document.save(output_path)
document.close()

print(f"Sample PDF created: {output_path}")