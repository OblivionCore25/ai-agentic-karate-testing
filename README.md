# AI Agentic Karate Testing

An AI-driven test generation system for the [Karate framework](https://github.com/karatelabs/karate). It ingests OpenAPI specs, Java source code, and existing Karate tests into a multi-source RAG knowledge base, then uses semantic retrieval to provide rich context for automated test generation.

---

## Prerequisites

| Tool | Version | Check |
|---|---|---|
| **Python** | ≥ 3.11 | `python3 --version` |
| **pip** | latest | `pip3 --version` |
| **Java** (optional, for running Karate tests) | 21 | `java --version` |
| **Maven** (optional, for running Karate tests) | ≥ 3.9 | `mvn --version` |

> **Note:** Java and Maven are only needed if you plan to _execute_ the generated Karate tests. The AI ingestion and retrieval pipeline is pure Python.

---

## Quick Start

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd karate-automation-project
```

### 2. Create and activate a virtual environment (recommended)

```bash
python3 -m venv .venv
source .venv/bin/activate   # macOS / Linux
# .venv\Scripts\activate    # Windows
```

### 3. Install dependencies

```bash
# Core + dev dependencies (uses local embedding model)
make install

# If you want OpenAI embedding support as well:
make install-openai
```

This runs `pip install -e ".[dev]"` which installs:
- **LangChain** + **LangGraph** (agent orchestration)
- **ChromaDB** (vector database)
- **sentence-transformers** (local embedding model)
- **tree-sitter** + **tree-sitter-java** (Java AST parsing)
- **prance** (OpenAPI spec parsing)
- **Typer** + **Rich** (CLI)
- **pytest** (testing)

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your keys:

```dotenv
# Required for Week 2+ (AI test generation)
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Embeddings — works out of the box with "local" (no API key needed)
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Only needed if you switch to OpenAI embeddings
# EMBEDDING_PROVIDER=openai
# EMBEDDING_MODEL=text-embedding-3-small
# OPENAI_API_KEY=sk-your-openai-key
```

> **For Week 1 testing, you don't need any API keys.** The local embedding model (`all-MiniLM-L6-v2`) runs entirely on your machine and downloads automatically on first use (~22MB).

### 5. Run the tests

```bash
make test
```

Expected output: all tests pass.

### 6. Ingest the sample data

```bash
make ingest
```

This parses the sample OpenAPI spec, Java source code, and Karate feature files, then stores their embeddings in a local ChromaDB database (`./chroma_data/`).

### 7. Try a semantic search

```bash
make search QUERY="create order with discount"
```

---

## Project Structure

```
karate-automation-project/
├── cli/                        # Typer CLI application
│   └── app.py                  #   CLI commands (ingest, search, stats)
├── config/                     # Configuration
│   ├── settings.py             #   Pydantic settings (loads from .env)
│   ├── logging_config.py       #   Rich logging setup
│   └── karate_project.yaml     #   Target API metadata
├── data/                       # Sample data (client-agnostic)
│   ├── sample_specs/           #   OpenAPI specs
│   ├── sample_source/          #   Java source code
│   ├── sample_features/        #   Existing Karate .feature files
│   └── karate_syntax_examples/ #   Karate syntax reference
├── ingestion/                  # Data ingestion adapters
│   ├── base_adapter.py         #   Abstract adapter + IngestedChunk model
│   ├── openapi_adapter.py      #   OpenAPI 3.0 spec parser
│   ├── source_code_adapter.py  #   Java AST parser (tree-sitter)
│   └── existing_tests_adapter.py # Karate .feature file parser
├── rag/                        # RAG (Retrieval-Augmented Generation)
│   ├── embeddings.py           #   Provider-agnostic embedding layer
│   ├── vector_store.py         #   ChromaDB wrapper
│   ├── chunking.py             #   Text chunking strategies
│   ├── reranker.py             #   Source-weighted reranking
│   └── retriever.py            #   Multi-index context retriever
├── karate_project/             # Minimal Karate scaffold (Java 21)
│   ├── pom.xml                 #   Maven config with Karate dependency
│   └── src/test/java/karate/   #   Test runner + generated tests folder
├── tests/                      # Python test suite
│   ├── test_rag/               #   Vector store & retriever tests
│   └── test_ingestion/         #   Adapter tests
├── pyproject.toml              # Project metadata & dependencies
├── Makefile                    # Dev workflow shortcuts
├── .env.example                # Environment variable template
└── .gitignore
```

---

## Available Commands

| Command | Description |
|---|---|
| `make install` | Install core + dev dependencies |
| `make install-openai` | Install with OpenAI embedding support |
| `make test` | Run the full test suite |
| `make ingest` | Ingest sample data into ChromaDB |
| `make search QUERY="..."` | Semantic search across the knowledge base |
| `make clean` | Remove caches and ChromaDB data |

### CLI directly

```bash
python3 -m cli.app --help              # Show all commands
python3 -m cli.app stats               # Show knowledge base statistics
python3 -m cli.app ingest-spec <path>  # Ingest a single OpenAPI spec
python3 -m cli.app ingest-source <path> # Ingest Java source directory
python3 -m cli.app ingest-tests <path>  # Ingest .feature files
python3 -m cli.app retrieve "query"     # Semantic search
```

---

## Embedding Provider Configuration

The system supports two embedding providers, configurable via `.env`:

### Local (default — no API key required)

```dotenv
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

The model downloads automatically on first use and runs on CPU/GPU locally.

### OpenAI

```bash
# First, install the optional OpenAI dependencies
make install-openai
```

```dotenv
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
OPENAI_API_KEY=sk-your-key
```

> ⚠️ **Important:** If you switch embedding models after ingestion, you must re-ingest (`make clean && make ingest`). The system has a mismatch guard that prevents querying with a different model than what was used for ingestion.

---

## Troubleshooting

| Issue | Solution |
|---|---|
| `ModuleNotFoundError: No module named 'rag'` | Make sure you ran `make install` (editable install) |
| `python: No such file or directory` | Use `python3` instead of `python`, or create an alias |
| `Embedding model mismatch` | Run `make clean && make ingest` to re-ingest with the current model |
| HuggingFace `HF_TOKEN` warning | Harmless — model is cached locally after first download |
| ChromaDB `readonly database` error | Ensure no other process is using `./chroma_data/` |
