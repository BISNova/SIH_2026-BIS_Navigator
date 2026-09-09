import pymupdf
from pathlib import Path


def extract_text_from_pdf(pdf_path: str) -> list[dict]:
    """
    Extract text from every page of a PDF.

    Returns a list containing:
    - page number
    - extracted text
    """

    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    document = pymupdf.open(pdf_path)

    pages = []

    for page_number, page in enumerate(document, start=1):
        text = page.get_text()

        pages.append({
            "page_number": page_number,
            "text": text
        })

    document.close()

    return pages


if __name__ == "__main__":
    pdf_file = "data/raw/sample_bis.pdf"

    pages = extract_text_from_pdf(pdf_file)

    for page in pages:
        print(f"\n--- Page {page['page_number']} ---")
        print(page["text"])