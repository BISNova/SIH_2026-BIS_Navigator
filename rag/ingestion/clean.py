import re


def clean_text(text: str) -> str:
    """
    Clean extracted document text while preserving
    clause numbers and meaningful content.
    """

    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Fix words broken across lines by a hyphen
    # Example: "require-\nment" -> "requirement"
    text = re.sub(r"-\n(?=\w)", "", text)

    # Replace multiple spaces/tabs with a single space
    text = re.sub(r"[ \t]+", " ", text)

    # Remove excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Remove spaces at the beginning/end of each line
    lines = [line.strip() for line in text.split("\n")]

    # Remove empty lines at the beginning/end
    text = "\n".join(lines).strip()

    return text


if __name__ == "__main__":
    sample_text = """
    Clause 5 · Product Requirements


    5.1 The product shall be manufactured using suitable materials.

    5.2 The product shall satisfy the specified dimensional
    requirements.
    """

    cleaned = clean_text(sample_text)

    print("Cleaned text:")
    print(cleaned)