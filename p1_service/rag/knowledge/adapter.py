from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class P4KnowledgeAdapter:
    """
    Read-only adapter for the structured BIS knowledge base.

    Reads directly from the project's shared knowledge base - no
    separate copy is kept inside p1_service/. Whatever P2/P4 write to
    these files is what P1 sees on its next restart:

        repo_root/
        └── knowledge_base/
            ├── structured/
            │   ├── products.json
            │   ├── standards.json
            │   ├── product_standard_mapping.json
            │   ├── product_attributes.json
            │   ├── tests.json
            │   ├── labs.json
            │   ├── lab_scope.json
            │   ├── qcos.json
            │   ├── schemes.json
            │   ├── conformity_routes.json
            │   ├── certification_steps.json
            │   ├── ah_centres.json
            │   └── inspection_requirements.json
            ├── documents/
            │   └── documents.json
            └── manifest.csv
    """

    def __init__(self, data_dir: Optional[str | Path] = None):
        if data_dir is None:
            # adapter.py -> knowledge -> rag -> p1_service -> repo root
            project_root = Path(__file__).resolve().parents[3]
            data_dir = project_root / "knowledge_base" / "structured"

        self.data_dir = Path(data_dir)

        if not self.data_dir.exists():
            raise FileNotFoundError(
                f"knowledge_base/structured not found: {self.data_dir}"
            )

        project_root = Path(__file__).resolve().parents[3]
        self.documents_path = (
            project_root / "knowledge_base" / "documents" / "documents.json"
        )
        self.manifest_path = project_root / "knowledge_base" / "manifest.csv"

        # Raw structured datasets
        self.products = self._load_json("products.json")
        self.standards = self._load_json("standards.json")
        self.product_standard_mapping = self._load_json(
            "product_standard_mapping.json"
        )
        self.product_attributes = self._load_json("product_attributes.json")
        self.tests = self._load_json("tests.json")
        self.labs = self._load_json("labs.json")
        self.lab_scope = self._load_json("lab_scope.json")
        self.qcos = self._load_json("qcos.json")
        self.schemes = self._load_json("schemes.json")
        self.conformity_routes = self._load_json(
            "conformity_routes.json"
        )
        self.certification_steps = self._load_json(
            "certification_steps.json"
        )
        self.documents = self._load_json_at(self.documents_path)
        self.ah_centres = self._load_json("ah_centres.json")

        # This file is currently empty. Empty is a valid state.
        self.inspection_requirements = self._load_json(
            "inspection_requirements.json"
        )

        self.manifest = self._load_csv_at(self.manifest_path)

        # Build indexes for fast lookup.
        self._build_indexes()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load_json(self, filename: str) -> List[Dict[str, Any]]:
        return self._load_json_at(self.data_dir / filename)

    def _load_json_at(self, path: Path) -> List[Dict[str, Any]]:
        if not path.exists():
            raise FileNotFoundError(
                f"Required knowledge base file not found: {path}"
            )

        # inspection_requirements.json is currently empty.
        if path.stat().st_size == 0:
            return []

        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if data is None:
            return []

        if not isinstance(data, list):
            raise ValueError(
                f"Expected a JSON array in {path}, "
                f"got {type(data).__name__}"
            )

        return data

    def _load_csv(self, filename: str) -> List[Dict[str, Any]]:
        return self._load_csv_at(self.data_dir / filename)

    def _load_csv_at(self, path: Path) -> List[Dict[str, Any]]:
        if not path.exists():
            raise FileNotFoundError(
                f"Required knowledge base file not found: {path}"
            )

        with path.open("r", encoding="utf-8-sig", newline="") as file:
            return list(csv.DictReader(file))

    # ------------------------------------------------------------------
    # Indexes
    # ------------------------------------------------------------------

    def _build_indexes(self) -> None:
        self._products_by_id = self._index_by_id(
            self.products, "product_id"
        )

        self._standards_by_id = self._index_by_id(
            self.standards, "standard_id"
        )

        self._documents_by_id = self._index_by_id(
            self.documents, "document_id"
        )

        self._labs_by_id = self._index_by_id(
            self.labs, "lab_id"
        )

        self._attributes_by_product = self._group_by(
            self.product_attributes, "product_id"
        )

        self._mapping_by_product = self._group_by(
            self.product_standard_mapping, "product_id"
        )

        self._tests_by_standard = self._group_by(
            self.tests, "standard_id"
        )

        self._lab_scope_by_standard = self._group_by(
            self.lab_scope, "standard_id"
        )

        self._qcos_by_standard = self._group_by(
            self.qcos, "standard_id"
        )

        self._routes_by_standard = self._group_by(
            self.conformity_routes, "standard_id"
        )

        self._steps_by_standard = self._group_by(
            self.certification_steps, "standard_id"
        )

        self._inspection_by_standard = self._group_by(
            self.inspection_requirements, "standard_id"
        )

    @staticmethod
    def _index_by_id(
        records: List[Dict[str, Any]],
        key: str,
    ) -> Dict[str, Dict[str, Any]]:
        return {
            record[key]: record
            for record in records
            if key in record
        }

    @staticmethod
    def _group_by(
        records: List[Dict[str, Any]],
        key: str,
    ) -> Dict[str, List[Dict[str, Any]]]:
        grouped: Dict[str, List[Dict[str, Any]]] = {}

        for record in records:
            value = record.get(key)

            if value is None:
                continue

            grouped.setdefault(value, []).append(record)

        return grouped

    # ------------------------------------------------------------------
    # Product knowledge
    # ------------------------------------------------------------------

    def get_product(
        self,
        product_id: str,
    ) -> Optional[Dict[str, Any]]:
        return self._products_by_id.get(product_id)

    def get_product_attributes(
        self,
        product_id: str,
    ) -> List[Dict[str, Any]]:
        return self._attributes_by_product.get(product_id, [])

    def get_standards_for_product(
        self,
        product_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Return normalized product → standard relationships.

        The mapping file is treated as the authoritative relationship
        source instead of relying on combined manifest strings.
        """
        mappings = self._mapping_by_product.get(product_id, [])

        results = []

        for mapping in mappings:
            standard_id = mapping.get("standard_id")

            if not standard_id:
                continue

            standard = self.get_standard(standard_id)

            results.append(
                {
                    "standard_id": standard_id,
                    "relationship_type": mapping.get(
                        "relationship_type"
                    ),
                    "curated_confidence": mapping.get(
                        "curated_confidence"
                    ),
                    "clarification_required": mapping.get(
                        "clarification_required",
                        False,
                    ),
                    "active": mapping.get("active", True),
                    "source_document_id": mapping.get(
                        "source_document_id"
                    ),
                    "standard": standard,
                }
            )

        return results

    # ------------------------------------------------------------------
    # Standard knowledge
    # ------------------------------------------------------------------

    def get_standard(
        self,
        standard_id: str,
    ) -> Optional[Dict[str, Any]]:
        return self._standards_by_id.get(standard_id)

    def get_tests(
        self,
        standard_id: str,
    ) -> List[Dict[str, Any]]:
        return self._tests_by_standard.get(standard_id, [])

    def get_inspection_requirements(
        self,
        standard_id: str,
    ) -> List[Dict[str, Any]]:
        return self._inspection_by_standard.get(
            standard_id,
            [],
        )

    def get_certification_steps(
        self,
        standard_id: str,
    ) -> List[Dict[str, Any]]:
        return self._steps_by_standard.get(
            standard_id,
            [],
        )

    # ------------------------------------------------------------------
    # QCO / scheme / conformity knowledge
    # ------------------------------------------------------------------

    def get_qcos(
        self,
        standard_id: str,
    ) -> List[Dict[str, Any]]:
        return self._qcos_by_standard.get(
            standard_id,
            [],
        )

    def get_conformity_routes(
        self,
        standard_id: str,
    ) -> List[Dict[str, Any]]:
        return self._routes_by_standard.get(
            standard_id,
            [],
        )

    def get_schemes(self) -> List[Dict[str, Any]]:
        return self.schemes

    # ------------------------------------------------------------------
    # Laboratory knowledge
    # ------------------------------------------------------------------

    def get_labs(self) -> List[Dict[str, Any]]:
        return self.labs

    def get_lab_scope(
        self,
        standard_id: str,
    ) -> List[Dict[str, Any]]:
        return self._lab_scope_by_standard.get(
            standard_id,
            [],
        )

    def get_labs_for_test(
        self,
        standard_id: str,
        test_name: str,
    ) -> List[Dict[str, Any]]:
        """
        Find lab-scope records capable of performing a specific test.
        """
        matches = []

        for scope in self.get_lab_scope(standard_id):
            if scope.get("test_name", "").strip().lower() == (
                test_name.strip().lower()
            ):
                lab_id = scope.get("lab_id")
                lab = self._labs_by_id.get(lab_id)

                matches.append(
                    {
                        "lab": lab,
                        "scope": scope,
                    }
                )

        return matches

    # ------------------------------------------------------------------
    # Documents / provenance
    # ------------------------------------------------------------------

    def get_documents(
        self,
        standard_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if standard_id is None:
            return self.documents

        return [
            document
            for document in self.documents
            if document.get("standard_id") == standard_id
        ]

    # ------------------------------------------------------------------
    # Hallmarking
    # ------------------------------------------------------------------

    def get_ah_centres(self) -> List[Dict[str, Any]]:
        return self.ah_centres

    # ------------------------------------------------------------------
    # Manifest
    # ------------------------------------------------------------------

    def get_manifest(self) -> List[Dict[str, Any]]:
        return self.manifest

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def get_knowledge_for_product(
        self,
        product_id: str,
    ) -> Dict[str, Any]:
        """
        Return the complete structured knowledge available for a product.
        """
        product = self.get_product(product_id)

        if product is None:
            return {}

        standards = self.get_standards_for_product(product_id)

        return {
            "product": product,
            "attributes": self.get_product_attributes(product_id),
            "standards": standards,
            "documents": [
                document
                for standard_info in standards
                for document in self.get_documents(
                    standard_info["standard_id"]
                )
            ],
        }