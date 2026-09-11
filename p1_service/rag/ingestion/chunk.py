import re


# Matches clause numbers such as:
# 5.1
# 5.2
# 10.1
# 10.2
# 11.3.2
CLAUSE_RE = re.compile(
    r"^(\d+\.\d+(?:\.\d+)*)\s+(.+)$"
)

# Matches headings such as:
# Clause 5 · Product Requirements
# Clause 6 · Testing Requirements
# Clause 7 · Marking Requirements
CLAUSE_HEADING_RE = re.compile(
    r"^Clause\s+(\d+)\s*[·.-]\s*(.+)$",
    re.IGNORECASE
)

# Matches page-number lines such as:
# Page 1
# Page 2
PAGE_RE = re.compile(
    r"^Page\s+\d+$",
    re.IGNORECASE
)


def _is_noise_line(line: str) -> bool:
    """
    Identify lines that are repeated PDF headers/footers
    or page-number artifacts.

    These are removed because they are not useful evidence.
    """

    normalized = line.strip()

    if not normalized:
        return True

    # Synthetic dataset header.
    if normalized.lower() == (
        "synthetic bis navigator test document — not official"
    ).lower():
        return True

    # Page number.
    if PAGE_RE.match(normalized):
        return True

    return False


def chunk_text(text: str) -> list[dict]:
    """
    Split cleaned BIS text into clause-aware chunks.

    Features:
    - Detects numbered clauses safely.
    - Handles two-digit clauses such as 10.1 correctly.
    - Separates Clause headings from evidence text.
    - Removes known synthetic PDF header/footer noise.
    - Preserves useful general text.
    - Stores the parent section heading as section_header.
    """

    lines = text.splitlines()

    chunks = []

    current_chunk = None
    current_section_header = None
    general_lines = []

    def flush_general():
        """
        Save accumulated general text as one general chunk.
        """
        nonlocal general_lines

        if not general_lines:
            return

        general_text = "\n".join(general_lines).strip()

        if general_text:
            chunks.append({
                "section": "general",
                "section_header": None,
                "text": general_text
            })

        general_lines = []

    def flush_clause():
        """
        Save the current clause chunk.
        """
        nonlocal current_chunk

        if current_chunk is None:
            return

        current_chunk["text"] = current_chunk["text"].strip()

        if current_chunk["text"]:
            chunks.append(current_chunk)

        current_chunk = None

    for raw_line in lines:

        line = raw_line.strip()

        # Ignore empty/noise lines.
        if _is_noise_line(line):
            continue

        # ---------------------------------------------------------
        # Clause heading
        # Example:
        # Clause 5 · Product Requirements
        # ---------------------------------------------------------
        heading_match = CLAUSE_HEADING_RE.match(line)

        if heading_match:

            # Finish anything currently being built.
            flush_clause()
            flush_general()

            current_section_header = line
            continue

        # ---------------------------------------------------------
        # Numbered clause
        # Example:
        # 10.1 The product shall...
        #
        # IMPORTANT:
        # Matching is anchored at the START of the line.
        # Therefore 10.1 can never become 0.1.
        # ---------------------------------------------------------
        clause_match = CLAUSE_RE.match(line)

        if clause_match:

            # Finish previous clause.
            flush_clause()
            flush_general()

            section_number = clause_match.group(1)
            clause_text = clause_match.group(2)

            current_chunk = {
                "section": section_number,
                "section_header": current_section_header,
                "text": f"{section_number} {clause_text}"
            }

            continue

        # ---------------------------------------------------------
        # Normal continuation line
        # ---------------------------------------------------------
        if current_chunk is not None:

            current_chunk["text"] += "\n" + line

        else:

            # Text before the first numbered clause.
            general_lines.append(line)

    # Flush anything remaining.
    flush_clause()
    flush_general()

    # Add deterministic chunk IDs.
    final_chunks = []

    for index, chunk in enumerate(chunks, start=1):

        final_chunks.append({
            "chunk_id": f"chunk_{index}",
            "section": chunk["section"],
            "section_header": chunk["section_header"],
            "text": chunk["text"]
        })

    return final_chunks


if __name__ == "__main__":

    sample_text = """
    Synthetic BIS Navigator test document — NOT OFFICIAL

    Page 1

    Clause 5 · Product Requirements

    5.1 The product shall be manufactured using suitable materials.

    5.2 The product shall satisfy the specified dimensional requirements.

    5.3 The product shall undergo the applicable quality and safety tests.

    Clause 6 · Testing Requirements

    6.1 Testing shall be carried out using the prescribed test procedure.

    6.2 Test results shall be recorded and maintained for verification.

    Clause 7 · Marking Requirements

    7.1 The product shall carry the required identification and marking information.

    Clause 10 · Additional Requirements

    10.1 The manufacturer shall maintain required records.

    10.2 The manufacturer shall perform periodic verification.

    10.3 The manufacturer shall retain evidence of compliance.
    """

    chunks = chunk_text(sample_text)

    print(f"Created {len(chunks)} chunks:\n")

    for chunk in chunks:

        print("=" * 60)
        print(f"ID: {chunk['chunk_id']}")
        print(f"Section: {chunk['section']}")
        print(f"Header: {chunk['section_header']}")
        print(chunk["text"])