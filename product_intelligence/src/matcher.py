"""
Matching engine.

DESIGN DECISION (documented here on purpose - read this before changing it):

The master plan says "pick ONE approach - rapidfuzz OR embeddings - don't
build both." We picked TF-IDF + cosine similarity (scikit-learn) as the
middle ground:

  - rapidfuzz alone = pure string/typo similarity, no notion of "these
    words mean similar things" - "cooker" vs "cookware" would score low.
  - sentence-transformers embeddings = better semantic understanding, but
    downloads a ~90MB model from the internet on first run. At a hackathon
    venue with unreliable wifi, that's a real risk for something you need
    working in a live demo.
  - TF-IDF + cosine similarity = no external download, pure scikit-learn,
    deterministic, fast, and still respects word overlap/importance rather
    than raw character distance. It's the safer default for a time-boxed
    build.

If you have reliable internet and want better semantic matching later,
swapping this out means changing ONLY this file - `match()`'s input/output
shape stays identical, so nothing else breaks. That's the whole point of
keeping this behind one function.
"""

from typing import List, Tuple
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .normalize import normalize


class ProductMatcher:
    """
    Matches a free-text query against the `products` table (not directly
    against standards - see pipeline.py for why this is now a two-stage
    process: identify the product first, then look up its standards).
    """

    def __init__(self, products_df: pd.DataFrame):
        self.df = products_df.reset_index(drop=True)
        # ngram_range=(1,2): unigrams AND word-pairs. This matters more than
        # it looks - with unigrams only, "stainless steel cooker" and
        # "steel pipe" both light up on the lone word "steel" and can tie.
        # Bigrams let "stainless steel" and "steel pipe" be different,
        # more specific signals instead of colliding on one shared word.
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2))
        self._matrix = self.vectorizer.fit_transform(self.df["search_text"])

    def rank(self, query: str) -> List[Tuple[int, float]]:
        """
        Returns [(row_index, score), ...] sorted by score descending,
        for every category in the mapping table (score in [0, 1]).
        """
        norm_query = normalize(query)
        if not norm_query:
            # Nothing left after stripping filler words - no signal at all
            return [(i, 0.0) for i in range(len(self.df))]

        query_vec = self.vectorizer.transform([norm_query])
        scores = cosine_similarity(query_vec, self._matrix)[0]
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        return ranked

    def reload(self, products_df: pd.DataFrame):
        """Call this after Person 4 updates the CSV, instead of restarting."""
        self.__init__(products_df)
