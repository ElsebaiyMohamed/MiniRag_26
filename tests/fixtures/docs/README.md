# MiniRag_26 v1.3.0 ingestion fixtures

This archive contains a deterministic fixture corpus for the v1.3.0 ingestion formats:
**TXT, PDF, and Markdown only**.

## Layout

- `docs/txt/`: plain-text fixtures
- `docs/pdf/`: extractable, multilingual, multipage, edge-case, and stress PDFs
- `docs/markdown/`: Markdown structures, multilingual content, and size variants
- `golden/`: reserved directories for issue #100. No golden outputs are included.


## Fixture categories

- `tiny`: minimal files for low-overhead boundary checks
- `small`: ordinary short documents
- `medium`: representative multi-section documents
- `large`: larger realistic documents
- `stress`: deliberately heavy inputs for workload testing
- `multilingual`: Arabic, English, and mixed-language content
- `edge_cases`: unusual but useful inputs

## Notes

- TXT files are UTF-8 unless their filename explicitly describes a byte-level edge case.
- The long-line TXT has no embedded line breaks; the final newline is intentionally absent.
- The CRLF fixture uses Windows line endings.
- PDF page markers identify page boundaries. The multipage acceptance fixture has extractable text on every page.
- `image_only_no_ocr.pdf` is an image-only scan-style document with no OCR text layer. It is for graceful handling, not OCR validation.
- `corrupted.pdf` is intentionally invalid and should not be treated as a valid source document.
- `encrypted_password_fixture.pdf` is encrypted with password `fixture-password` if the optional `pypdf` library was available during generation. Check PDF metadata before relying on encryption-specific behavior.
- Arabic PDF glyph rendering depends on the PDF library/font environment. The Arabic TXT and Markdown fixtures are the reliable Unicode source fixtures.
- Stress files are intentionally sizable. Tests should not load every stress fixture in every fast unit-test run; mark heavy tests separately where appropriate.
- All content is synthetic and contains no personal data.

## Regeneration

The included files are the fixture snapshot for this delivery. No regeneration script is included in this archive.
