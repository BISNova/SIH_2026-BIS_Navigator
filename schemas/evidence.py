from typing import Optional
from pydantic import BaseModel


class EvidenceRecord(BaseModel):
    chunk_id: str

    standard_id: str
    document_id: str
    document_title: str

    document_type: Optional[str] = None
    section_header: Optional[str] = None

    text: str

    source_url: Optional[str] = None
    version: Optional[str] = None

    authority_level: Optional[str] = None