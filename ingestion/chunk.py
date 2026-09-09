import re


def chunk_text(text: str) -> list[dict]:
    """
    Split cleaned BIS text into clause-aware chunks.
    """

    # Split before numbered clauses such as:
    # 5.1, 5.2, 6.1, 6.2, etc.
    parts = re.split(
        r"(?=\n?\d+\.\d+(?:\.\d+)*\s)",
        text
    )

    chunks = []
    chunk_number = 1

    for part in parts:
        part = part.strip()

        if not part:
            continue

        clause_match = re.match(
            r"(\d+\.\d+(?:\.\d+)*)\s",
            part
        )

        if clause_match:
            section = clause_match.group(1)
        else:
            section = "general"

        chunks.append({
            "chunk_id": f"chunk_{chunk_number}",
            "section": section,
            "text": part
        })

        chunk_number += 1

    return chunks


if __name__ == "__main__":

    sample_text = """
Clause 5 · Product Requirements

5.1 The product shall be manufactured using suitable materials.

5.2 The product shall satisfy the specified dimensional requirements.

5.3 The product shall undergo the applicable quality and safety tests.

Clause 6 · Testing Requirements

6.1 Testing shall be carried out using the prescribed test procedure.

6.2 Test results shall be recorded and maintained for verification.

Clause 7 · Marking Requirements

7.1 The product shall carry the required identification and marking information.
"""

    chunks = chunk_text(sample_text)

    print(f"Created {len(chunks)} chunks:\n")

    for chunk in chunks:
        print("=" * 60)
        print(f"ID: {chunk['chunk_id']}")
        print(f"Section: {chunk['section']}")
        print(chunk["text"])