from __future__ import annotations

from typing import Any, Dict, List, Optional

from rag.knowledge.adapter import P4KnowledgeAdapter
from rag.schemas.evidence import EvidenceRecord


class P4EvidenceBuilder:
    """
    Converts structured P4 knowledge into P1-compatible evidence records.

    P4 remains responsible for structured BIS knowledge.
    P1 remains responsible for retrieval, reranking,
    sufficiency, confidence, answer generation, and citations.
    """

    def __init__(
        self,
        adapter: Optional[P4KnowledgeAdapter] = None,
    ):
        self.adapter = adapter or P4KnowledgeAdapter()

    def build_for_standard(
        self,
        standard_id: str,
    ) -> List[EvidenceRecord]:
        """
        Build evidence records for one BIS standard.

        Evidence is created from the structured P4 knowledge sources:
        - tests
        - conformity routes
        - certification steps
        - QCOs
        - laboratory scope
        - source documents
        """

        evidence: List[EvidenceRecord] = []

        standard = self.adapter.get_standard(standard_id)

        if standard is None:
            return evidence

        evidence.extend(
            self._build_test_evidence(standard_id)
        )

        evidence.extend(
            self._build_route_evidence(standard_id)
        )

        evidence.extend(
            self._build_certification_step_evidence(
                standard_id
            )
        )

        evidence.extend(
            self._build_qco_evidence(standard_id)
        )

        evidence.extend(
            self._build_lab_scope_evidence(standard_id)
        )

        evidence.extend(
            self._build_document_evidence(standard_id)
        )

        return evidence

    @staticmethod
    def _document_title(
        document: Optional[Dict[str, Any]],
        fallback: str,
    ) -> str:
        """
        Safely resolve a document title.

        P4 document records may expose the title under
        different keys, so never pass None into EvidenceRecord.
        """

        if document:
            title = (
                document.get("document_title")
                or document.get("title")
            )

            if title:
                return str(title)

        return fallback

    def _build_test_evidence(
        self,
        standard_id: str,
    ) -> List[EvidenceRecord]:

        records = self.adapter.get_tests(standard_id)

        evidence: List[EvidenceRecord] = []

        for record in records:

            test_id = record.get("test_id")

            if not test_id:
                continue

            text = self._test_to_text(record)

            document = self.adapter._documents_by_id.get(
                record.get("source_document_id")
            )

            evidence.append(
                EvidenceRecord(
                    chunk_id=f"P4-{test_id}",
                    standard_id=standard_id,
                    document_id=(
                        record.get("source_document_id")
                        or f"P4-{test_id}"
                    ),
                    document_title=self._document_title(
                        document,
                        (
                            f"P4 Test Requirement - "
                            f"{record.get('test_name', '')}"
                        ),
                    ),
                    document_type=(
                        document.get("document_type")
                        if document
                        else "TEST_REQUIREMENT"
                    ),
                    section=record.get("clause_reference"),
                    section_header=record.get("test_category"),
                    page_number=None,
                    text=text,
                    source_url=(
                        document.get("source_url")
                        if document
                        else None
                    ),
                    version=None,
                    authority_level=(
                        document.get("authority_level")
                        if document
                        else None
                    ),
                )
            )

        return evidence

    def _build_route_evidence(
        self,
        standard_id: str,
    ) -> List[EvidenceRecord]:

        records = self.adapter.get_conformity_routes(
            standard_id
        )

        evidence: List[EvidenceRecord] = []

        for index, record in enumerate(records):

            route_id = (
                record.get("route_id")
                or f"{standard_id}-ROUTE-{index + 1}"
            )

            text = self._record_to_text(
                "Conformity route",
                record,
            )

            document = self.adapter._documents_by_id.get(
                record.get("source_document_id")
            )

            evidence.append(
                EvidenceRecord(
                    chunk_id=f"P4-{route_id}",
                    standard_id=standard_id,
                    document_id=(
                        record.get("source_document_id")
                        or route_id
                    ),
                    document_title=self._document_title(
                        document,
                        "P4 Conformity Route",
                    ),
                    document_type=(
                        document.get("document_type")
                        if document
                        else "CONFORMITY_ROUTE"
                    ),
                    text=text,
                    source_url=(
                        document.get("source_url")
                        if document
                        else None
                    ),
                    authority_level=(
                        document.get("authority_level")
                        if document
                        else None
                    ),
                )
            )

        return evidence

    def _build_certification_step_evidence(
        self,
        standard_id: str,
    ) -> List[EvidenceRecord]:

        records = self.adapter.get_certification_steps(
            standard_id
        )

        evidence: List[EvidenceRecord] = []

        for record in records:

            steps = record.get("steps", [])

            if not isinstance(steps, list):
                continue

            for index, step in enumerate(steps):

                step_no = step.get(
                    "step_no",
                    index + 1,
                )

                title = step.get(
                    "title",
                    f"Step {step_no}",
                )

                description = step.get(
                    "description",
                    "",
                )

                source_document_id = step.get(
                    "source_document_id"
                )

                document = self.adapter._documents_by_id.get(
                    source_document_id
                )

                text_parts = [
                    f"Certification step {step_no}: {title}"
                ]

                if description:
                    text_parts.append(
                        f"Description: {description}"
                    )

                text = "\n".join(text_parts)

                evidence.append(
                    EvidenceRecord(
                        chunk_id=(
                            f"P4-STEP-"
                            f"{standard_id}-"
                            f"{step_no}"
                        ),
                        standard_id=standard_id,
                        document_id=(
                            source_document_id
                            or (
                                f"P4-STEP-"
                                f"{standard_id}-"
                                f"{step_no}"
                            )
                        ),
                        document_title=self._document_title(
                            document,
                            "P4 Certification Steps",
                        ),
                        document_type=(
                            document.get("document_type")
                            if document
                            else "CERTIFICATION_GUIDELINE"
                        ),
                        section=str(step_no),
                        section_header=title,
                        page_number=None,
                        text=text,
                        source_url=(
                            document.get("source_url")
                            if document
                            else None
                        ),
                        version=None,
                        authority_level=(
                            document.get("authority_level")
                            if document
                            else None
                        ),
                    )
                )

        return evidence

    def _build_qco_evidence(
        self,
        standard_id: str,
    ) -> List[EvidenceRecord]:

        records = self.adapter.get_qcos(standard_id)

        evidence: List[EvidenceRecord] = []

        for record in records:

            qco_id = record.get("qco_id")

            if not qco_id:
                continue

            text = self._record_to_text(
                "Quality Control Order",
                record,
            )

            source_document_id = record.get(
                "source_document_id"
            )

            document = self.adapter._documents_by_id.get(
                source_document_id
            )

            # QCO records contain their own authoritative source URL.
            source_url = (
                record.get("source_url")
                or (
                    document.get("source_url")
                    if document
                    else None
                )
            )

            evidence.append(
                EvidenceRecord(
                    chunk_id=f"P4-{qco_id}",
                    standard_id=standard_id,
                    document_id=(
                        source_document_id
                        or qco_id
                    ),
                    document_title=self._document_title(
                        document,
                        (
                            record.get("qco_name")
                            or "P4 Quality Control Order"
                        ),
                    ),
                    document_type="QCO",
                    section=None,
                    section_header=None,
                    page_number=None,
                    text=text,
                    source_url=source_url,
                    version=None,
                    authority_level=(
                        document.get("authority_level")
                        if document
                        else None
                    ),
                )
            )

        return evidence

    def _build_lab_scope_evidence(
        self,
        standard_id: str,
    ) -> List[EvidenceRecord]:

        records = self.adapter.get_lab_scope(standard_id)

        evidence: List[EvidenceRecord] = []

        for index, record in enumerate(records):

            lab_id = record.get(
                "lab_id",
                "UNKNOWN",
            )

            test_name = record.get(
                "test_name",
                "Unknown test",
            )

            chunk_id = (
                f"P4-LABSCOPE-{standard_id}-"
                f"{lab_id}-{index}"
            )

            text = self._record_to_text(
                "Laboratory testing scope",
                record,
            )

            evidence.append(
                EvidenceRecord(
                    chunk_id=chunk_id,
                    standard_id=standard_id,
                    document_id=(
                        record.get("source_document_id")
                        or chunk_id
                    ),
                    document_title=(
                        f"Laboratory scope - "
                        f"{lab_id}"
                    ),
                    document_type="LAB_SCOPE",
                    section=test_name,
                    section_header=None,
                    page_number=None,
                    text=text,
                    source_url=record.get("source_url"),
                    version=None,
                    authority_level=None,
                )
            )

        return evidence

    def _build_document_evidence(
        self,
        standard_id: str,
    ) -> List[EvidenceRecord]:

        records = self.adapter.get_documents(
            standard_id
        )

        evidence: List[EvidenceRecord] = []

        for record in records:

            document_id = record.get("document_id")

            if not document_id:
                continue

            text = self._record_to_text(
                "BIS knowledge document",
                record,
            )

            evidence.append(
                EvidenceRecord(
                    chunk_id=f"P4-DOC-{document_id}",
                    standard_id=standard_id,
                    document_id=document_id,
                    document_title=(
                        record.get("document_title")
                        or record.get("title")
                        or document_id
                    ),
                    document_type=record.get(
                        "document_type"
                    ),
                    section=None,
                    section_header=None,
                    page_number=None,
                    text=text,
                    source_url=record.get(
                        "source_url"
                    ),
                    version=None,
                    authority_level=record.get(
                        "authority_level"
                    ),
                )
            )

        return evidence

    @staticmethod
    def _test_to_text(
        record: Dict[str, Any],
    ) -> str:

        parts = [
            f"Test: {record.get('test_name', '')}",
            f"Category: {record.get('test_category', '')}",
            f"Method: {record.get('test_method', '')}",
            f"Requirement: {record.get('requirement', '')}",
            (
                f"Acceptance criteria: "
                f"{record.get('acceptance_criteria', '')}"
            ),
            (
                f"Sample requirement: "
                f"{record.get('sample_requirement', '')}"
            ),
            f"Frequency: {record.get('frequency', '')}",
            (
                f"Facility requirement: "
                f"{record.get('facility_requirement', '')}"
            ),
        ]

        return "\n".join(
            part
            for part in parts
            if part.split(":", 1)[-1].strip()
        )

    @staticmethod
    def _record_to_text(
        label: str,
        record: Dict[str, Any],
    ) -> str:

        parts = [label]

        for key, value in record.items():

            if key in {
                "source_url",
                "source_document_id",
            }:
                continue

            if value is None or value == "":
                continue

            parts.append(
                f"{key.replace('_', ' ').title()}: {value}"
            )

        return "\n".join(parts)