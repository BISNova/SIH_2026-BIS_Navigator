from pathlib import Path
import json

# from sentence_transformers import SentenceTransformer
from fastembed import TextEmbedding

# ============================================================
# PATHS
# ============================================================

PROCESSED_DIR = Path("data/processed")
EMBEDDINGS_DIR = Path("data/embeddings")

EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# MODEL
# ============================================================

MODEL_NAME = "all-MiniLM-L6-v2"


# ============================================================
# LOAD PROCESSED CHUNKS
# ============================================================

def load_chunks():
    """
    Load all processed chunk JSON files.
    """

    json_files = sorted(
        PROCESSED_DIR.glob("*_chunks.json")
    )

    if not json_files:
        raise FileNotFoundError(
            "No processed chunk JSON files found in "
            f"{PROCESSED_DIR}"
        )

    all_chunks = []

    for json_file in json_files:

        print(f"Loading: {json_file.name}")

        with open(
            json_file,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        chunks = data.get("chunks", [])

        if not chunks:
            print(
                f"  Warning: no chunks found in "
                f"{json_file.name}"
            )
            continue

        all_chunks.extend(chunks)

        print(
            f"  Loaded {len(chunks)} chunks"
        )

    return all_chunks


# ============================================================
# BUILD EMBEDDING TEXT
# ============================================================

def build_embedding_text(chunk: dict) -> str:
    """
    Build the text that will be converted into an embedding.

    We include the section header because it provides useful
    context for semantic retrieval.

    The original chunk['text'] remains unchanged and will later
    be used for evidence/citations.
    """

    section_header = chunk.get(
        "section_header"
    )

    text = chunk.get(
        "text",
        ""
    ).strip()

    if section_header:
        return (
            f"{section_header}\n"
            f"{text}"
        )

    return text


# ============================================================
# GENERATE EMBEDDINGS
# ============================================================

def generate_embeddings(chunks: list[dict]):
    """
    Generate normalized embeddings using
    all-MiniLM-L6-v2.
    """

    print("\nLoading embedding model:")
    print(f"  {MODEL_NAME}")

    # model = SentenceTransformer(
    #     MODEL_NAME
    # )

    model = TextEmbedding(model_name=f"sentence-transformers/{MODEL_NAME}")

    embedding_texts = [
        build_embedding_text(chunk)
        for chunk in chunks
    ]

    print(
        f"\nGenerating embeddings for "
        f"{len(embedding_texts)} chunks..."
    )

    # embeddings = model.encode(
    #     embedding_texts,
    #     normalize_embeddings=True,
    #     show_progress_bar=True
    # )
    embeddings = list(model.embed(embedding_texts))

    return embeddings


# ============================================================
# VALIDATE EMBEDDINGS
# ============================================================

def validate_embeddings(
    chunks: list[dict],
    embeddings
):
    """
    Verify that the generated embeddings match
    the chunks and have the expected dimension.
    """

    errors = []

    # --------------------------------------------------------
    # Count check
    # --------------------------------------------------------

    if len(chunks) != len(embeddings):

        errors.append(
            "Number of chunks does not match "
            "number of embeddings."
        )

    # --------------------------------------------------------
    # Dimension check
    # --------------------------------------------------------

    if len(embeddings) > 0:

        dimension = len(embeddings[0])

        if dimension != 384:

            errors.append(
                f"Expected embedding dimension 384, "
                f"got {dimension}."
            )

    # --------------------------------------------------------
    # Duplicate chunk IDs
    # --------------------------------------------------------

    chunk_ids = [
        chunk.get("chunk_id")
        for chunk in chunks
    ]

    if len(chunk_ids) != len(set(chunk_ids)):

        errors.append(
            "Duplicate chunk IDs detected."
        )

    return errors


# ============================================================
# SAVE EMBEDDINGS
# ============================================================

def save_embeddings(
    chunks: list[dict],
    embeddings
):
    """
    Save chunks + embeddings together.

    This keeps the embedding associated with its
    original evidence metadata.
    """

    records = []

    for chunk, embedding in zip(
        chunks,
        embeddings
    ):

        records.append({
            "chunk_id": chunk["chunk_id"],
            "embedding": embedding.tolist(),
            "text": chunk["text"],
            "embedding_text": build_embedding_text(chunk),

            "section": chunk["section"],
            "section_header": chunk["section_header"],

            "document_id": chunk["document_id"],
            "standard_id": chunk["standard_id"],
            "document_title": chunk["document_title"],
            "document_type": chunk["document_type"],
            "version": chunk["version"],
            "authority_level": chunk["authority_level"],
            "source_url": chunk["source_url"],
            "page_number": chunk["page_number"],
        })

    output_path = (
        EMBEDDINGS_DIR /
        "all_embeddings.json"
    )

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            records,
            file,
            indent=2,
            ensure_ascii=False
        )

    return output_path


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n")
    print("=" * 70)
    print("BIS NAVIGATOR — EMBEDDING GENERATION")
    print("=" * 70)

    # --------------------------------------------------------
    # 1. Load chunks
    # --------------------------------------------------------

    chunks = load_chunks()

    print(
        f"\nTotal chunks loaded: {len(chunks)}"
    )

    # --------------------------------------------------------
    # 2. Generate embeddings
    # --------------------------------------------------------

    embeddings = generate_embeddings(
        chunks
    )

    # --------------------------------------------------------
    # 3. Validate
    # --------------------------------------------------------

    errors = validate_embeddings(
        chunks,
        embeddings
    )

    # --------------------------------------------------------
    # 4. Stop if validation fails
    # --------------------------------------------------------

    if errors:

        print("\n" + "!" * 70)
        print("EMBEDDING VALIDATION FAILED")
        print("!" * 70)

        for error in errors:
            print(f"  - {error}")

        raise RuntimeError(
            "Embedding validation failed."
        )

    # --------------------------------------------------------
    # 5. Display embedding information
    # --------------------------------------------------------

    dimension = len(embeddings[0])

    print("\nEmbedding validation:")
    print(
        f"  Chunks:              {len(chunks)}"
    )
    print(
        f"  Embeddings:          {len(embeddings)}"
    )
    print(
        f"  Vector dimension:    {dimension}"
    )
    print(
        f"  Model:               {MODEL_NAME}"
    )
    print(
        f"  Normalized vectors:  Yes"
    )

    # --------------------------------------------------------
    # 6. Save
    # --------------------------------------------------------

    output_path = save_embeddings(
        chunks,
        embeddings
    )

    print("\n✓ Embeddings generated successfully.")

    print("\nSaved to:")
    print(
        f"  {output_path}"
    )

    # --------------------------------------------------------
    # 7. Show sample
    # --------------------------------------------------------

    print("\nSample embedding:")
    print(
        f"  Chunk ID: {chunks[0]['chunk_id']}"
    )
    print(
        f"  Section:  {chunks[0]['section']}"
    )
    print(
        f"  Standard: {chunks[0]['standard_id']}"
    )
    print(
        f"  Vector:   {embeddings[0][:5].tolist()} ..."
    )

    print("\n" + "=" * 70)
    print("EMBEDDING PHASE PASSED")
    print("=" * 70)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()