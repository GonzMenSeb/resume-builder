#!/usr/bin/env python3
"""Simple end-to-end test with real resume data from resumes/ directory.

This test validates the ingestion layer with real PDFs without needing Claude API access.
"""

from pathlib import Path
from resume_generator.ingestion.loader import DataLoader
from resume_generator.config import Settings, ClaudeModel

RESUMES_DIR = Path("resumes")
OUTPUT_DIR = Path("output/e2e_test")


def test_pdf_ingestion():
    """Test that we can successfully load and extract text from real PDF files."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    pdf_files = list(RESUMES_DIR.glob("*.pdf"))
    if not pdf_files:
        print(f"❌ No PDF files found in {RESUMES_DIR}")
        return False

    print(f"📁 Found {len(pdf_files)} PDF files:")
    for pdf in pdf_files:
        print(f"  • {pdf.name}")

    settings = Settings(
        anthropic_api_key="sk-ant-test-key-e2e",
        claude_model=ClaudeModel.SONNET,
        output_dir=OUTPUT_DIR,
        verbose=True,
    )
    settings.ensure_directories()

    all_success = True
    loader = DataLoader()

    for pdf_file in pdf_files:
        print(f"\n{'='*60}")
        print(f"Testing ingestion: {pdf_file.name}")
        print(f"{'='*60}\n")

        try:
            result = loader.load([pdf_file])

            if result.failed_sources:
                print(f"⚠️  Some sources failed for {pdf_file.name}")
                for path, error in result.failed_sources:
                    print(f"   Failed: {path} - {error}")

            text_length = len(result.unified_text)
            print(f"✅ Successfully extracted text from {pdf_file.name}")
            print(f"   Sources processed: {len(result.sources)}")
            print(f"   Text length: {text_length:,} characters")

            if text_length == 0:
                print(f"   ⚠️  Warning: No text extracted")
                all_success = False
                continue

            preview = result.unified_text[:200].replace('\n', ' ')
            print(f"   Preview: {preview}...")

            output_file = OUTPUT_DIR / f"{pdf_file.stem}_extracted.txt"
            output_file.write_text(result.unified_text, encoding='utf-8')
            print(f"   Saved to: {output_file}")

        except Exception as e:
            print(f"❌ Exception while processing {pdf_file.name}: {e}")
            import traceback
            traceback.print_exc()
            all_success = False

    print(f"\n{'='*60}")
    if all_success:
        print("✅ All ingestion tests PASSED")
        print(f"\nExtracted text files saved to: {OUTPUT_DIR}")
    else:
        print("❌ Some ingestion tests FAILED")
    print(f"{'='*60}\n")

    return all_success


if __name__ == "__main__":
    import sys
    success = test_pdf_ingestion()
    sys.exit(0 if success else 1)
