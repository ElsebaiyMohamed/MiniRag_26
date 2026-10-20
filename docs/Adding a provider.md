# Adding a provider

MiniRag_26 talks to language models and vector databases through interfaces and factories, so adding a new one touches a small, predictable set of files. This guide covers:

- [Adding an LLM provider](#adding-an-llm-provider) (generation and embeddings)
- [Adding a vector store](#adding-a-vector-store)
- [Adding a prompt language](#adding-a-prompt-language)

Before you start, read the code of the existing providers next to the interface. They are the best reference:

| Kind | Interface | Existing providers |
|---|---|---|
| LLM | `src/stores/llm/LLMInterface.py` | `CohereProvider`, `OpenAiProvider` |
| Vector store | `src/stores/vectordb/VectorDBInterface.py` | `PgVector`|

If your LLM server speaks the OpenAI API (Ollama, vLLM, LM Studio, and others), you do not need a new provider. Set `OPENAI_API_URL`. See [Configuration](configuration.md).

## How providers are wired

```text
.env  ->  Settings (helpers/config.py)
                |
                v
main.py lifespan --> LLMProviderFactory.create(GENERATION_BACKEND)   -> app.generation_client
                 --> LLMProviderFactory.create(EMBEDDING_BACKEND)    -> app.embedding_client
                 --> VectorDBProviderFactory.create(VECTORDB_BACKEND) -> app.vectordb_client
                                    |
                                    v
              NLPController uses the clients through the interfaces only
```

Controllers never import a concrete provider. They only call interface methods, which is why a new provider needs no controller changes.

## Adding an LLM provider

The example adds a hypothetical provider called `Acme`.

### 1. Register the name

In `src/models/enums/LLMEnums.py`, add the provider to `LLMEnum`, and define a role enum if its role names differ:

```python
class LLMEnum(Enum):
    OPENAI = 'OPENAI'
    COHERE = 'COHERE'
    ACME = 'ACME'          # value users put in GENERATION_BACKEND / EMBEDDING_BACKEND

class AcmeEnum(Enum):
    SYSTEM = 'system'
    USER = 'user'
    ASSISTANT = 'assistant'
```

Export the new enum in `src/models/enums/__init__.py`.

### 2. Implement the provider

Create `src/stores/llm/providers/AcmeProvider.py`:

```python
import logging
from typing import Union, List

from ..LLMInterface import LLMInterface
from models.enums import AcmeEnum, DocumentTypeEnum


class AcmeProvider(LLMInterface):
    def __init__(self, api_key: str, default_max_char: int = 1000,
                 default_output_max_tokens: int = 1000,
                 default_generation_temperature: float = 0.1):
        super().__init__()
        self.api_key = api_key
        self.default_max_char = default_max_char
        self.default_max_output_tokens = default_output_max_tokens
        self.default_generation_temperature = default_generation_temperature
        self.generation_model_id = None
        self.embedding_model_id = None
        self.embedding_size = None
        self.enum = AcmeEnum                      # controllers read provider.enum.SYSTEM.value
        self.client = ...                         # your SDK client
        self.logger = logging.getLogger(__name__)

    def set_generation_model(self, model_id: str):
        self.generation_model_id = model_id

    def set_embedding_model(self, model_id: str, embedding_size: int):
        self.embedding_model_id = model_id
        self.embedding_size = embedding_size

    def generate_text(self, prompt: str, max_output_tokens: int = None,
                      temperature: float = None, *args, **kwargs):
        chat_history = kwargs.get('chat_history', [])
        messages = chat_history.copy()
        messages.append(self.construct_prompt(prompt=prompt, role=self.enum.USER.value))
        # call your API; return the answer text, or None on failure
        ...

    def embed_text(self, prompts: Union[List, str], document_type: str = None, *args, 
                   **kwargs):
        # return one vector (list of floats) or list of vectors for many inputs, or 
        None on failure
        ...


    def construct_prompt(self, prompt: str, role: str, *args, **kwargs):
        return {'role': role, 'content': self.process_text(prompt)}

    def process_text(self, prompt: str):
        return prompt
```

The contract the controllers rely on:

| Method | Must do |
|---|---|
| `set_generation_model(model_id)` | Store the model name. Called once at startup |
| `set_embedding_model(model_id, embedding_size)` | Store the model name and its dimension. Called with both arguments at startup |
| `generate_text(prompt, ..., chat_history=[...])` | Return the answer as a plain `str`. Return `None` on any failure. Prefer copying `chat_history` rather than mutating it |
| `embed_text(prompt, document_type)` | Return `list[float]` or `list[list[float], list[float], ...]`. `document_type` is `DocumentTypeEnum.DOCUMENT` when indexing and `QUERY` when searching |
| `construct_prompt(prompt, role)` | Return a message dict in your API's format |
| `enum` attribute | An enum with `SYSTEM`, `USER`, `ASSISTANT` values used to build `chat_history` |
| `embedding_size` attribute | Read by indexing to create the collection |

Notes:

- If your embedding model treats queries and documents differently (as Cohere does with `input_type`), map `document_type` accordingly. If it does not, ignore the argument.
- Log the real error and return `None`. Routes turn a falsy result into a clean `4xx` signal.

### 3. Export it

In `src/stores/llm/providers/__init__.py`:

```python
from .AcmeProvider import AcmeProvider
```

`src/stores/llm/__init__.py` only exports the factory, so nothing else needs to change there.

### 4. Register it in the factory

In `src/stores/llm/LLMProviderFactory.py`:

```python
elif provider == LLMEnum.ACME.value:
    return AcmeProvider(
        api_key=self.config.ACME_API_KEY,
        default_max_char=self.config.INPUT_DEFAULT_MAX_CHAR,
        default_output_max_tokens=self.config.DEAFAULT_MAX_OUTPUT_TOKENS,
        default_generation_temperature=self.config.GENERATION_DEFAULT_TEMPERATURE,
    )
```

### 5. Add configuration

- Add `ACME_API_KEY: str` to `Settings` in `src/helpers/config.py`.
- Add it to `src/.env.example` and `docker/envv/.env.example.app`.
- Add the dependency with `uv add <sdk>`.

Users then select the provider with `GENERATION_BACKEND="ACME"` and/or `EMBEDDING_BACKEND="ACME"`.

### 6. Verify

There is no automated test suite yet. Run the end-to-end flow from the README against the new provider:

1. Start the API with the new backend selected.
2. Upload a small file, process it, and push it. A successful push proves embeddings work and have the right dimension.
3. Call search, then answer. A successful answer proves generation works.
4. Check that failures (a wrong key, an unknown model) produce a logged error and a clean `4xx` response, not a crash.

### 7. Document it

- Add a row to the variable tables in [Configuration](configuration.md), and a provider example.
- Add its badge to the README tech stack.
- Add an entry to `CHANGELOG.md` under *Unreleased*.

## Adding a vector store

The example adds a hypothetical store called `Acme`.

### 1. Register the name

In `src/models/enums/VectorDBEnums.py`:

```python
class VectorDBEnums(Enum):
    PGVECTOR = 'PGVECTOR'
    ACME = 'ACME'
```

### 2. Implement the provider

Create `src/stores/vectordb/providers/AcmeDB.py` subclassing `VectorDBInterface`. **All methods are `async`**, because the controllers `await` them.

```python
from ..VectorDBInterface import VectorDBInterface
from models.schemas import RetrievedDocument


class AcmeDB(VectorDBInterface):
    def __init__(self, ..., distance_method: str = None):
        ...

    async def connect(self): ...
    async def disconnect(self): ...
    async def is_collection_existed(self, collection_name: str) -> bool: ...
    async def list_all_collections(self) -> list: ...
    async def get_collection_info(self, collection_name: str) -> dict: ...
    async def delete_collection(self, collection_name: str): ...
    async def create_collection(self, collection_name: str, embedding_size: int,
                                do_reset: bool = False) -> bool: ...
    async def insert_one(self, collection_name: str, text: str, vector: list,
                         metadata: dict = None, record_id: str = None,
                         asset_id: int = None): ...
    async def insert_many(self, collection_name: str, texts: list, vectors: list,
                          metadatas: list = None, record_ids: list = None,
                          asset_ids: list = None, batch_size: int = 50): ...
    async def search_by_vector(self, collection_name: str, vector: list, limit: int = 10): ...
    async def delete_embeddings_by_asset_id(self, collection_name: str,
                                            asset_id: int) -> int: ...
```

Behavior the controllers depend on:

| Method | Contract |
|---|---|
| `connect` / `disconnect` | Called once at startup and shutdown from the FastAPI lifespan |
| `create_collection(name, embedding_size, do_reset)` | If `do_reset` is true, drop first. Ensure the collection exists and return `True` when it is available for inserts, whether newly created or already present; return `False` if creation fails |
| `delete_collection(name)` | Used by reset. Must be safe when the collection does not exist |
| `get_collection_info(name)` | Return something JSON-serializable. The info route serializes it |
| `insert_one(..., record_id, asset_id)` | Store the vector with its chunk ID and owning asset ID. Both IDs are required for project/asset cleanup and traceability |
| `insert_many(..., record_ids, asset_ids)` | `record_ids` are the chunk IDs and `asset_ids` are the owning asset IDs. Both lists must align one-to-one with `texts`, `vectors`, and `metadatas`. Persist the asset ID with each vector and return `{'success': n, 'failed': m}` |
| `delete_embeddings_by_asset_id(name, asset_id)` | Delete only vectors belonging to that asset and return the number deleted. Used to clean up an asset when indexing fails; do not delete other assets' vectors |
| `search_by_vector(name, vector, limit)` | Return a list of `RetrievedDocument(text=..., score=...)` sorted best first, where a higher score is better. Return `False` or `None` when the collection is missing |

Collection names are `collection_{project_id}`, one per project. Keep projects isolated from each other.

The asset ID must be stored in a field that can be filtered during deletion. For example, PgVector stores it in an `asset_id` column; a document-oriented store could store it in each point's payload. Ensure collection creation establishes the field/indexing needed by your backend's deletion operation.

`chunk_id` also links each vector to its source chunk. In PgVector, the collection's foreign key uses `ON DELETE CASCADE`, so deleting a chunk automatically removes its vector. If your store does not support that kind of cascade, ensure project and asset reset/deletion paths explicitly remove the corresponding vectors.

Two pitfalls that bit existing code:

- Calling an `async` method without `await` returns a coroutine, which is always truthy. Every internal call such as `is_collection_existed(...)` needs `await`.
- Compare enum values using the names that actually exist in `DistanceMethodEnums` (`COSINE`, `DOT`).

### 3. Export and register

Export it in `src/stores/vectordb/providers/__init__.py`, then add a branch to `VectorDBProviderFactory.create` that builds it from settings.

### 4. Configure, verify, document

Follow steps 5 to 7 of the LLM guide, using `VECTORDB_BACKEND="ACME"`. When verifying, also run a push with `"do_reset": 1` twice in a row and check that no duplicate records appear.

## Adding a prompt language

Prompts live in `src/stores/llm/templates/locales/<language>/rag.py` and define three `string.Template` objects: `system_prompt`, `document_prompt`, and `footer_prompt`.

1. Copy `locales/en/` to `locales/<code>/` (including `__init__.py`).
2. Translate the three templates. Keep the placeholders `$doc_num`, `$chunk_text`, and `$query` unchanged.
3. Set `PRIMARY_LANG="<code>"` in your env file.

If a locale folder or template is missing, the parser falls back to `DEFAULT_LANG`.

## Contribution checklist

- [ ] Interface fully implemented, including `asset_id` on insert methods and `delete_embeddings_by_asset_id`
- [ ] Failures are logged and return `None` or `False`, not raised to the route
- [ ] Exported and registered in the factory
- [ ] New settings added to `config.py` and both example env files
- [ ] End-to-end flow verified (upload, process, push, search, answer)
- [ ] [Configuration](configuration.md) updated
- [ ] README tech stack and `CHANGELOG.md` updated
