from rag.pipeline.evidence_pipeline import EvidencePipeline
p = EvidencePipeline()
result = p.run(query="pressure cooker safety valve testing", standard_ids=None)
print(result["answer"][:300])
print([e["standard_id"] for e in result["evidence"]])