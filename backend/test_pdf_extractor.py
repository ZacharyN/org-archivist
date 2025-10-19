"""
Test script for PDF extractor

Creates a simple test PDF and validates extraction
"""

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import io
from app.services.extractors.pdf_extractor import PDFExtractor


def create_test_pdf():
    """Create a simple multi-page test PDF"""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    # Page 1
    c.drawString(100, 750, "Test Document - Page 1")
    c.drawString(100, 700, "This is a test PDF document for the Org Archivist system.")
    c.drawString(100, 680, "It contains multiple pages with sample text.")
    c.showPage()

    # Page 2
    c.drawString(100, 750, "Test Document - Page 2")
    c.drawString(100, 700, "This is the second page.")
    c.drawString(100, 680, "We use this to test multi-page PDF extraction.")
    c.showPage()

    c.save()
    return buffer.getvalue()


def main():
    print("Creating test PDF...")
    pdf_content = create_test_pdf()
    print(f"Created PDF ({len(pdf_content)} bytes)")

    print("\nInitializing PDF extractor...")
    extractor = PDFExtractor()

    print("\nValidating PDF...")
    is_valid, error = extractor.validate(pdf_content)
    print(f"Valid: {is_valid}")
    if error:
        print(f"Error: {error}")
        return

    print("\nExtracting text...")
    try:
        text = extractor.extract(pdf_content, "test.pdf")
        print(f"\nExtracted text ({len(text)} characters):")
        print("-" * 60)
        print(text)
        print("-" * 60)

        print("\nExtracting metadata...")
        metadata = extractor.get_metadata(pdf_content)
        print(f"Metadata: {metadata}")

        print("\n[PASS] PDF extraction test completed successfully")

    except Exception as e:
        print(f"\n[FAIL] PDF extraction test failed: {e}")


if __name__ == "__main__":
    main()
