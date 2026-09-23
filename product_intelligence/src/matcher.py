"""
Matching engine.

Uses TF-IDF + cosine similarity as the base matcher, with an additional
product-identity compatibility check so generic material words such as
"steel" do not incorrectly identify an unrelated product.

The matcher returns the same [(row_index, score), ...] shape expected by
the rest of the Product Intelligence pipeline.
"""

from typing import List, Tuple
import re

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .normalize import normalize


class ProductMatcher:
    """
    Matches a free-text query against the products table.

    Matching is two-stage:

    1. TF-IDF + cosine similarity provides the base lexical score.
    2. Product-identity compatibility prevents a generic material term
       from being treated as sufficient evidence for a product match.

    Material is deliberately excluded from product-identity evidence.
    """

    def __init__(self, products_df: pd.DataFrame):
        self.df = products_df.reset_index(drop=True)

        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2))
        self._matrix = self.vectorizer.fit_transform(self.df["search_text"])

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        """Return normalized alphanumeric tokens."""
        text = normalize(text)
        return set(re.findall(r"[a-z0-9]+", text))

    @classmethod
    def _tokens_from_field(cls, value) -> set[str]:
        """Extract tokens from either a scalar field or a list-like field."""
        tokens: set[str] = set()

        if isinstance(value, (list, tuple, set)):
            for item in value:
                tokens.update(cls._tokenize(str(item)))
        elif value is not None:
            tokens.update(cls._tokenize(str(value)))

        return tokens

    @classmethod
    def _product_identity_tokens(cls, row: pd.Series) -> set[str]:
        """
        Build product-identity vocabulary from product-defining fields.

        Material is explicitly excluded because words such as "steel" can
        occur across many unrelated product categories.
        """
        identity_tokens: set[str] = set()

        for field in (
            "canonical_name",
            "product_type",
            "keywords",
            "synonyms",
        ):
            identity_tokens.update(cls._tokens_from_field(row.get(field, "")))

        # Remove generic material vocabulary from identity evidence.
        material_tokens = cls._tokens_from_field(row.get("material", ""))

        return identity_tokens - material_tokens

    @classmethod
    def _identity_overlap(
        cls,
        query: str,
        row: pd.Series,
    ) -> tuple[set[str], set[str]]:
        """
        Return query tokens and the subset that overlap with product
        identity fields after material terms have been removed.
        """
        query_tokens = cls._tokenize(query)
        identity_tokens = cls._product_identity_tokens(row)
        overlap = query_tokens.intersection(identity_tokens)

        return query_tokens, overlap

    def _identity_compatible(self, query: str, row: pd.Series) -> bool:
        """
        Require at least one product-identity token from the query.

        This prevents a generic material-only query such as "steel bottle"
        from being accepted as a steel-bar product merely because "steel"
        appears in that product's description.

        Legitimate queries such as "steel rebar" still work because "rebar"
        is a product-identity term.
        """
        query_tokens, overlap = self._identity_overlap(query, row)

        if not query_tokens:
            return False

        return bool(overlap)

    def rank(self, query: str) -> List[Tuple[int, float]]:
        """
        Returns [(row_index, score), ...] sorted by score descending.

        Candidates without product-identity compatibility receive 0.0.
        """
        norm_query = normalize(query)

        if not norm_query:
            return [(i, 0.0) for i in range(len(self.df))]

        query_vec = self.vectorizer.transform([norm_query])
        scores = cosine_similarity(query_vec, self._matrix)[0]

        adjusted_scores = []

        for index, score in enumerate(scores):
            row = self.df.iloc[index]

            if not self._identity_compatible(norm_query, row):
                score = 0.0

            adjusted_scores.append((index, float(score)))

        ranked = sorted(
            adjusted_scores,
            key=lambda x: x[1],
            reverse=True,
        )

        return ranked

    def reload(self, products_df: pd.DataFrame):
        """Reload the product catalogue after KB updates."""
        self.__init__(products_df)