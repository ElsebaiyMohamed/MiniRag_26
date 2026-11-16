# Fixture manifest

| File                                                   | Format | Size (bytes) | Language                                     | Category | Purpose                                                           |
|--------------------------------------------------------|-------:|-------------:|----------------------------------------------|----------|-------------------------------------------------------------------|
| docs/markdown/edge_cases/empty.md                      |     MD |            0 | English (unless content indicates otherwise) | Edge     | edge_cases scenario fixture for MD ingestion                      |
| docs/markdown/edge_cases/html_comments_and_raw_html.md |     MD |          147 | English (unless content indicates otherwise) | Edge     | edge_cases scenario fixture for MD ingestion                      |
| docs/markdown/edge_cases/unclosed_fence.md             |     MD |           72 | English (unless content indicates otherwise) | Edge     | edge_cases scenario fixture for MD ingestion                      |
| docs/markdown/large/large_reference.md                 |     MD |      3017417 | English (unless content indicates otherwise) | Normal   | large scenario fixture for MD ingestion                           |
| docs/markdown/medium/engineering_handbook.md           |     MD |        73219 | English (unless content indicates otherwise) | Normal   | medium scenario fixture for MD ingestion                          |
| docs/markdown/multilingual/arabic_and_english.md       |     MD |         1276 | Arabic / English                             | Normal   | multilingual scenario fixture for MD ingestion                    |
| docs/markdown/small/basic_document.md                  |     MD |          506 | English (unless content indicates otherwise) | Normal   | small scenario fixture for MD ingestion                           |
| docs/markdown/small/tables_and_code.md                 |     MD |          427 | English (unless content indicates otherwise) | Normal   | small scenario fixture for MD ingestion                           |
| docs/markdown/stress/stress_markdown.md                |     MD |      4915470 | English (unless content indicates otherwise) | Stress   | stress scenario fixture for MD ingestion                          |
| docs/markdown/tiny/minimal.md                          |     MD |           31 | English (unless content indicates otherwise) | Normal   | tiny scenario fixture for MD ingestion                            |
| docs/pdf/edge_cases/blank_pages.pdf                    |    PDF |        24345 | English (unless content indicates otherwise) | Edge     | edge_cases scenario fixture for PDF ingestion                     |
| docs/pdf/edge_cases/corrupted.pdf                      |    PDF |           72 | English (unless content indicates otherwise) | Edge     | Intentionally malformed PDF for error handling                    |
| docs/pdf/edge_cases/encrypted_password_fixture.pdf     |    PDF |        22682 | English (unless content indicates otherwise) | Edge     | Encrypted PDF candidate; password fixture-password if encrypted   |
| docs/pdf/edge_cases/image_only_no_ocr.pdf              |    PDF |         9660 | English (unless content indicates otherwise) | Edge     | Image-only scan-style PDF; graceful empty extraction only, no OCR |
| docs/pdf/edge_cases/unusual_page_sizes.pdf             |    PDF |        23325 | English (unless content indicates otherwise) | Edge     | edge_cases scenario fixture for PDF ingestion                     |
| docs/pdf/large/large_120_pages.pdf                     |    PDF |       181056 | English (unless content indicates otherwise) | Normal   | large scenario fixture for PDF ingestion                          |
| docs/pdf/medium/dense_30_pages.pdf                     |    PDF |        59526 | English (unless content indicates otherwise) | Normal   | medium scenario fixture for PDF ingestion                         |
| docs/pdf/multilingual/arabic_mixed_6_pages.pdf         |    PDF |        29515 | Arabic / English                             | Normal   | multilingual scenario fixture for PDF ingestion                   |
| docs/pdf/multipage/multipage_extractable_text.pdf      |    PDF |        27949 | English (unless content indicates otherwise) | Normal   | Required #99 multi-page PDF with extractable text on every page   |
| docs/pdf/small/single_page_report.pdf                  |    PDF |        22857 | English (unless content indicates otherwise) | Normal   | small scenario fixture for PDF ingestion                          |
| docs/pdf/stress/stress_300_pages.pdf                   |    PDF |       430819 | English (unless content indicates otherwise) | Stress   | stress scenario fixture for PDF ingestion                         |
| docs/pdf/tiny/single_page_tiny.pdf                     |    PDF |        22587 | English (unless content indicates otherwise) | Normal   | tiny scenario fixture for PDF ingestion                           |
| docs/txt/edge_cases/crlf_lines.txt                     |    TXT |           49 | English (unless content indicates otherwise) | Edge     | edge_cases scenario fixture for TXT ingestion                     |
| docs/txt/edge_cases/empty.txt                          |    TXT |            0 | English (unless content indicates otherwise) | Edge     | Required #99 empty TXT edge case                                  |
| docs/txt/edge_cases/long_single_line.txt               |    TXT |        75630 | English (unless content indicates otherwise) | Edge     | Required #99 very long uninterrupted line                         |
| docs/txt/edge_cases/no_trailing_newline.txt            |    TXT |           49 | English (unless content indicates otherwise) | Edge     | edge_cases scenario fixture for TXT ingestion                     |
| docs/txt/edge_cases/symbols_and_punctuation.txt        |    TXT |          145 | English (unless content indicates otherwise) | Edge     | edge_cases scenario fixture for TXT ingestion                     |
| docs/txt/edge_cases/utf8_bom.txt                       |    TXT |           68 | English (unless content indicates otherwise) | Edge     | edge_cases scenario fixture for TXT ingestion                     |
| docs/txt/edge_cases/whitespace_only.txt                |    TXT |           11 | English (unless content indicates otherwise) | Edge     | edge_cases scenario fixture for TXT ingestion                     |
| docs/txt/large/large_research_notes.txt                |    TXT |      3142896 | English (unless content indicates otherwise) | Normal   | large scenario fixture for TXT ingestion                          |
| docs/txt/medium/technical_report.txt                   |    TXT |       314407 | English (unless content indicates otherwise) | Normal   | medium scenario fixture for TXT ingestion                         |
| docs/txt/multilingual/arabic_utf8.txt                  |    TXT |          874 | Arabic / English                             | Normal   | Required #99 Arabic UTF-8 TXT fixture                             |
| docs/txt/multilingual/mixed_arabic_english.txt         |    TXT |          387 | Arabic / English                             | Normal   | multilingual scenario fixture for TXT ingestion                   |
| docs/txt/small/english_utf8.txt                        |    TXT |          928 | English (unless content indicates otherwise) | Normal   | Required #99 English UTF-8 TXT fixture                            |
| docs/txt/small/technical_log.txt                       |    TXT |          243 | English (unless content indicates otherwise) | Normal   | small scenario fixture for TXT ingestion                          |
| docs/txt/stress/stress_5mb.txt                         |    TXT |     73332095 | English (unless content indicates otherwise) | Stress   | stress scenario fixture for TXT ingestion                         |
| docs/txt/tiny/one_character.txt                        |    TXT |            1 | English (unless content indicates otherwise) | Normal   | tiny scenario fixture for TXT ingestion                           |
| docs/txt/tiny/tiny_utf8.txt                            |    TXT |            5 | English (unless content indicates otherwise) | Normal   | tiny scenario fixture for TXT ingestion                           |
