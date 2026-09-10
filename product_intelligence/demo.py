"""
Quick interactive test loop against the REAL knowledge base.

Run:  python demo.py

Try (real products currently in the KB):
  "domestic pressure cooker"
  "electric geyser"
  "gold jewellery"
  "organic vegetables"   <- not_found, not in curated scope
"""

from src.pipeline import ProductIntelligencePipeline


def print_result(result):
    print(f"\nstatus: {result.status}  |  confidence: {result.confidence_label} ({result.confidence_score})")

    if result.product_candidates:
        print("top product candidates:")
        for c in result.product_candidates:
            print(f"   - {c.canonical_name} ({c.category})  score={c.score}")

    if result.status == "matched":
        p = result.matched_product
        print(f"\n✅ Identified product: {p.canonical_name}")
        if p.attributes:
            print(f"   (material: {p.attributes.material}, typical use: {p.attributes.typical_use})")
        print("   Applicable standards:")
        for s in result.applicable_standards:
            mandatory_note = {True: "MANDATORY", False: "not mandatory", None: "mandatory: unknown"}[s.is_mandatory]
            status_note = "" if s.status == "current" else f"  [STATUS: {s.status.upper()}]"
            print(f"   - [{s.relationship_type.upper()}] ({mandatory_note}) {s.is_number} - {s.title}{status_note}")
            print(f"       confidence={s.confidence}  source: {s.source_url}")

    elif result.status == "clarification_needed":
        print(f"\n❓ {result.clarification_question}")
        for opt in result.clarification_options:
            print(f"   [{opt.product_id}] {opt.label}")

    elif result.status == "not_found":
        print("\n🚫 Not covered in our current knowledge base - no confident match.")


if __name__ == "__main__":
    pipeline = ProductIntelligencePipeline()
    print("Product Intelligence demo (real KB). Type a product description (or 'quit').\n")

    while True:
        query = input("> ").strip()
        if query.lower() in {"quit", "exit"}:
            break
        if not query:
            continue
        result = pipeline.process(query)
        print_result(result)
