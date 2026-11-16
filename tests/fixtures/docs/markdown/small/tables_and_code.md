# Structured Markdown

| Component | Responsibility | Status |
|---|---|---|
| Loader | Extract source text | Ready |
| Registry | Select loader | Ready |
| Chunker | Split extracted text | Planned |

Inline code: `loader.load(path)`.

```python
def normalize_text(value: str) -> str:
    return value.strip()
```

[Project documentation](https://example.invalid/docs)

![Illustrative image reference](assets/architecture.png)
