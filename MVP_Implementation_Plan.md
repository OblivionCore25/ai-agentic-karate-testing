# AI Agentic Karate Testing — MVP Implementation Plan

**Version:** 1.0  
**Date:** April 21, 2026  
**MVP Duration:** 4 Weeks  
**LLM Provider:** Claude API (Anthropic)  
**Based on:** AI Agentic Systems for Automation Testing with Karate Framework — Proposal v1.0

---

## 1. Repository Structure

```
karate-ai-agent/
├── README.md
├── pyproject.toml                  # Python project config (Poetry or pip)
├── .env.example                    # Template for API keys and config
├── .env                            # Local env (gitignored)
├── Makefile                        # Common commands: ingest, generate, execute, test
│
├── config/
│   ├── settings.py                 # Central config (LLM params, RAG settings, paths)
│   ├── logging_config.py           # Structured logging setup
│   └── karate_project.yaml         # Karate project paths, env targets, Maven coords
│
├── ingestion/                      # Knowledge ingestion adapters
│   ├── __init__.py
│   ├── base_adapter.py             # Abstract base class for all ingestion adapters
│   ├── openapi_adapter.py          # OpenAPI 3.0 spec parser
│   ├── source_code_adapter.py      # tree-sitter AST-based code parser
│   ├── existing_tests_adapter.py   # Existing .feature file indexer
│   └── db_schema_adapter.py        # (Stretch) SQLAlchemy introspection adapter
│
├── rag/                            # RAG knowledge base layer
│   ├── __init__.py
│   ├── vector_store.py             # ChromaDB initialization, collections, CRUD
│   ├── embeddings.py               # Embedding model wrapper (sentence-transformers)
│   ├── chunking.py                 # Source-aware chunking strategies
│   ├── retriever.py                # Multi-index retrieval with metadata filtering
│   └── reranker.py                 # Relevance reranking logic
│
├── agents/                         # LangGraph agent nodes
│   ├── __init__.py
│   ├── graph.py                    # Main LangGraph workflow definition
│   ├── state.py                    # Agent state schema (TypedDict)
│   ├── scenario_generator.py       # Generates test scenarios from context
│   ├── feature_writer.py           # Converts scenarios to .feature files
│   ├── result_analyzer.py          # Classifies test failures, suggests fixes
│   └── prompts/                    # Prompt templates
│       ├── scenario_generation.py
│       ├── feature_writing.py
│       └── result_analysis.py
│
├── executor/                       # Karate test execution bridge
│   ├── __init__.py
│   ├── runner.py                   # Triggers Karate CLI/Maven, captures results
│   └── report_parser.py            # Parses Karate JSON/HTML reports
│
├── cli/                            # Human-in-the-loop CLI interface
│   ├── __init__.py
│   └── app.py                      # Typer CLI app (ingest, generate, review, run)
│
├── karate_project/                 # Target Karate test project (Java/Maven)
│   ├── pom.xml
│   ├── src/
│   │   └── test/
│   │       └── java/
│   │           └── karate/
│   │               ├── karate-config.js
│   │               └── generated/  # Where AI-generated .feature files land
│   └── target/                     # Karate reports output (gitignored)
│
├── data/                           # Sample data for development & testing
│   ├── sample_specs/               # Sample OpenAPI specs
│   ├── sample_source/              # Sample Java service classes
│   ├── sample_features/            # Sample existing .feature files
│   └── karate_syntax_examples/     # Curated Karate DSL examples for RAG seeding
│
├── tests/                          # Python unit & integration tests
│   ├── test_ingestion/
│   ├── test_rag/
│   ├── test_agents/
│   └── test_executor/
│
└── docs/
    ├── architecture.md
    └── setup_guide.md
```

---

## 2. Prerequisites & Environment Setup (Day 0)

Complete these before Week 1 begins.

### 2.1 Accounts & Access

| Item | Action | Owner |
|------|--------|-------|
| Anthropic API key | Create account at console.anthropic.com, generate API key. Model: `claude-sonnet-4-20250514` for generation, `claude-haiku-4-5-20251001` for classification/analysis. Budget: ~$300–600 for MVP. | Lead Engineer |
| Target API source code access | Get read access to the 1–2 internal API repos selected for MVP. Identify the service layer classes (controllers, services, validators, mappers). | Backend Advisor |
| Target API OpenAPI spec | Export or locate the OpenAPI 3.0 JSON/YAML spec for each target API. | Backend Advisor |
| Karate project baseline | Confirm existing Karate project compiles and runs. Gather existing `.feature` files for RAG seeding. | QA/SDET |

### 2.2 Dev Environment

```bash
# Python 3.11+ required
python --version  # Verify >= 3.11

# Create project
mkdir karate-ai-agent && cd karate-ai-agent
git init

# Python environment
python -m venv .venv
source .venv/bin/activate

# Core dependencies (add to pyproject.toml or requirements.txt)
pip install \
  langchain>=0.2.0 \
  langgraph>=0.1.0 \
  langchain-anthropic>=0.1.0 \
  chromadb>=0.5.0 \
  sentence-transformers>=2.7.0 \
  tree-sitter>=0.22.0 \
  tree-sitter-java>=0.21.0 \
  tree-sitter-python>=0.21.0 \
  openapi-spec-validator>=0.7.0 \
  prance>=23.6.0 \
  typer>=0.12.0 \
  rich>=13.0 \
  pydantic>=2.0 \
  python-dotenv>=1.0

# Java/Maven for Karate (verify existing install)
java -version   # >= 11
mvn -version    # >= 3.8
```

### 2.3 `.env` File

```env
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL_GENERATION=claude-sonnet-4-20250514
CLAUDE_MODEL_ANALYSIS=claude-haiku-4-5-20251001
CHROMA_PERSIST_DIR=./chroma_data
KARATE_PROJECT_PATH=./karate_project
LOG_LEVEL=INFO
```

---

## 3. Week 1 — Foundation & Multi-Source Knowledge Base

**Goal:** Working RAG knowledge base with API specs + source code + existing tests indexed. Semantic search returning relevant cross-source context for a given endpoint.

### Day 1 (Mon): Project Scaffolding & ChromaDB Setup

**Tasks:**

1. **Create the full repo structure** as defined in Section 1. Initialize all `__init__.py` files, `pyproject.toml`, and the Makefile.

2. **Implement `config/settings.py`:**
   - Use Pydantic `BaseSettings` to load from `.env`.
   - Define all configurable params: LLM model names, temperature, max tokens, chunk sizes, top-k retrieval, ChromaDB path.

3. **Implement `rag/vector_store.py`:**
   - Initialize ChromaDB persistent client.
   - Create three collections with metadata schema:
     - `api_specs` — origin_type: "spec"
     - `source_code` — origin_type: "code"
     - `existing_tests` — origin_type: "test"
   - Each document stored with metadata: `origin_type`, `source_file`, `endpoint_tag`, `language`, `chunk_type`.
   - Implement `add_documents()`, `query()`, and `delete_collection()` methods.

4. **Implement `rag/embeddings.py`:**
   - Wrap `sentence-transformers/all-MiniLM-L6-v2` model.
   - Provide `embed_text(text) -> List[float]` and `embed_batch(texts) -> List[List[float]]`.
   - Use ChromaDB's built-in embedding function integration.

5. **Write unit tests** for vector store initialization and basic add/query cycle.

**Acceptance criteria:** `pytest tests/test_rag/` passes. ChromaDB persists to disk and survives restart. Can add a document and retrieve it by semantic similarity.

---

### Day 2 (Tue): OpenAPI Spec Ingestion Adapter

**Tasks:**

1. **Implement `ingestion/base_adapter.py`:**
   ```python
   from abc import ABC, abstractmethod
   from dataclasses import dataclass

   @dataclass
   class IngestedChunk:
       content: str
       origin_type: str        # "spec", "code", "test"
       source_file: str
       endpoint_tag: str       # e.g., "POST /orders"
       chunk_type: str         # e.g., "endpoint_definition", "service_method", "feature_scenario"
       metadata: dict          # Additional context

   class BaseAdapter(ABC):
       @abstractmethod
       def ingest(self, source_path: str) -> list[IngestedChunk]:
           pass
   ```

2. **Implement `ingestion/openapi_adapter.py`:**
   - Use `prance` for `$ref` resolution and `openapi-spec-validator` for validation.
   - For each endpoint, extract: HTTP method, path, summary, description, parameters, request body schema (resolved), response schemas, authentication requirements.
   - **Chunking strategy:** One chunk per endpoint. Each chunk is a structured text block containing all endpoint details in a readable format.
   - Tag each chunk with `endpoint_tag = "{METHOD} {path}"`.
   - Handle both JSON and YAML input.

3. **Implement `rag/chunking.py`** with a `chunk_for_spec()` function that formats endpoint data into a clean text representation optimized for embedding.

4. **Write integration test:** Ingest one of the sample OpenAPI specs from `data/sample_specs/`, verify chunks are created with correct metadata, verify semantic search retrieves the right endpoint when queried.

5. **Prepare sample data:** Place 1–2 OpenAPI specs in `data/sample_specs/`. If you don't have real specs yet, use the Petstore spec or create a mock `orders-api.yaml`.

**Acceptance criteria:** `python -m cli.app ingest-spec data/sample_specs/orders-api.yaml` populates ChromaDB. Querying "create order" returns the POST /orders endpoint chunk.

---

### Day 3 (Wed): Source Code Ingestion Adapter

**Tasks:**

1. **Implement `ingestion/source_code_adapter.py`:**
   - Initialize tree-sitter with Java grammar (primary) and Python grammar (secondary).
   - Parse source files into AST.
   - **Extraction targets (Java):**
     - Class-level: class name, annotations (`@RestController`, `@Service`, etc.), implemented interfaces.
     - Method-level: method name, annotations (`@PostMapping`, `@GetMapping`, etc.), parameters, return type, full method body.
     - Extract branching logic: `if/else`, `switch`, `try/catch` blocks within methods.
     - Extract validation annotations: `@NotNull`, `@Valid`, `@Size`, custom validators.
   - **Chunking strategy:** One chunk per method. Include the class context (class name, annotations) as a preamble to each method chunk.
   - **Endpoint-to-code mapping:** Match endpoint tags by:
     - Primary: `@RequestMapping`/`@PostMapping`/`@GetMapping` annotation values.
     - Fallback: Naming convention (e.g., `OrderController.createOrder` → `POST /orders`).
     - Store the mapping confidence level in metadata.

2. **Implement `rag/chunking.py` — add `chunk_for_code()`:**
   - Format: `[Class: OrderService] [Method: createOrder] [Annotations: @Transactional] \n {method body}`
   - Preserve enough context for the LLM to understand business logic.

3. **Write unit tests:** Parse a sample Java service class, verify correct method extraction, verify endpoint tag mapping from annotations.

4. **Prepare sample data:** Place 2–3 sample Java service/controller classes in `data/sample_source/`. Include at least one with business logic branching (discounts, validation, error handling).

**Acceptance criteria:** Source code adapter extracts method-level chunks from Java files. Each chunk is tagged with the correct endpoint. Querying "discount logic" retrieves the relevant service method.

---

### Day 4 (Thu): Existing Tests Adapter & Multi-Source Seeding

**Tasks:**

1. **Implement `ingestion/existing_tests_adapter.py`:**
   - Parse existing Karate `.feature` files.
   - Extract per-scenario chunks: scenario name, Given/When/Then steps, tags, data tables.
   - Tag with `endpoint_tag` by parsing the URL in the `Given url` or `When method` steps.
   - These serve as few-shot examples for the Feature Writer agent.

2. **Seed RAG with Karate DSL documentation:**
   - Curate 20–30 Karate syntax examples in `data/karate_syntax_examples/` covering: basic API calls, JSON assertions, JSONPath, data-driven scenarios (`Examples:`), `call` and `callonce`, JDBC database queries, match operators (`contains`, `==`, `!null`), headers/auth setup, `karate-config.js` patterns.
   - Ingest these as `origin_type: "reference"` for the Feature Writer to retrieve.

3. **Build the unified ingestion pipeline (`cli/app.py` — `ingest` command):**
   ```
   python -m cli.app ingest \
     --spec data/sample_specs/orders-api.yaml \
     --source data/sample_source/ \
     --tests data/sample_features/ \
     --karate-examples data/karate_syntax_examples/
   ```
   - Runs all adapters, populates ChromaDB, prints summary (chunks per source type, total docs).

4. **Write integration test:** Full ingestion pipeline → query an endpoint → verify results include chunks from spec, code, AND existing tests.

**Acceptance criteria:** `make ingest` populates the knowledge base from all three sources. `make search QUERY="POST /orders"` returns a mixed-source result set.

---

### Day 5 (Fri): Multi-Index Retriever & Context Packaging

**Tasks:**

1. **Implement `rag/retriever.py` — `ContextRetriever`:**
   - Input: endpoint tag (e.g., `"POST /orders"`) or natural language query.
   - Process:
     1. Query each ChromaDB collection separately with metadata filtering.
     2. Retrieve `top_k` results per source type (configurable, default: 5 spec, 10 code, 5 test).
     3. Deduplicate by content similarity threshold.
     4. Rerank combined results by relevance score.
   - Output: `ContextPackage` dataclass:
     ```python
     @dataclass
     class ContextPackage:
         endpoint_tag: str
         spec_context: list[IngestedChunk]      # API spec details
         code_context: list[IngestedChunk]       # Service methods, validators
         test_context: list[IngestedChunk]       # Existing test patterns
         reference_context: list[IngestedChunk]  # Karate syntax examples
     ```

2. **Implement `rag/reranker.py`:**
   - Simple relevance reranker: score = embedding similarity × source-priority weight.
   - Source priority weights (configurable): code > spec > test > reference.
   - Filter out chunks below a relevance threshold (default: 0.3).

3. **Add a `retrieve` CLI command:**
   ```
   python -m cli.app retrieve "POST /orders"
   ```
   - Prints the full context package in a readable format, showing source type labels.

4. **Write integration test:** Ingest all sample data → retrieve context for a known endpoint → verify the package contains spec details AND relevant code methods AND similar existing tests.

**Acceptance criteria:** Retriever returns a rich, multi-source context package. Code methods with business logic are ranked higher than generic spec definitions. Week 1 deliverable complete.

---

## 4. Week 2 — AI Agent: Context-Aware Test Generation

**Goal:** End-to-end: provide an endpoint → receive Karate `.feature` files that test business logic, not just contract shape.

### Day 6 (Mon): Agent State & LangGraph Skeleton

**Tasks:**

1. **Implement `agents/state.py`:**
   ```python
   from typing import TypedDict, Optional

   class AgentState(TypedDict):
       endpoint_tag: str
       context_package: Optional[ContextPackage]
       scenarios: Optional[list[TestScenario]]
       feature_files: Optional[list[GeneratedFeature]]
       execution_results: Optional[list[TestResult]]
       analysis: Optional[FailureAnalysis]
       retry_count: int
       reasoning_chain: list[str]  # Tracks which sources informed decisions
   ```

2. **Implement `agents/graph.py` — LangGraph workflow skeleton:**
   - Define the directed graph with nodes:
     - `retrieve_context` → `generate_scenarios` → `write_features` → `human_review` → `execute_tests` → `analyze_results` → (conditional: `retry` or `done`)
   - Use LangGraph's `StateGraph` with `AgentState`.
   - Wire conditional edge: if `analysis.has_test_issues` and `retry_count < 2`, loop back to `write_features`.
   - For now, implement only `retrieve_context` (calls the retriever from Week 1). Other nodes return placeholder state.

3. **Configure Claude API integration:**
   - Implement `langchain-anthropic` `ChatAnthropic` initialization in `config/settings.py`.
   - Use `claude-sonnet-4-20250514` for scenario generation and feature writing.
   - Use `claude-haiku-4-5-20251001` for result analysis (cheaper, faster).
   - Set temperature: 0.2 for feature writing (deterministic), 0.5 for scenario generation (creative).

4. **Write test:** Graph compiles and runs through retrieve_context node with sample data.

**Acceptance criteria:** LangGraph workflow compiles. Running it with an endpoint populates the context package in state. Graph visualization (via `graph.get_graph().draw_mermaid()`) shows the correct flow.

---

### Day 7 (Tue): Scenario Generator Agent

**Tasks:**

1. **Implement `agents/prompts/scenario_generation.py`:**
   - System prompt instructs Claude to act as a senior QA engineer with deep backend knowledge.
   - User prompt template:
     ```
     You are generating test scenarios for the endpoint: {endpoint_tag}

     ## API Specification Context
     {spec_context}

     ## Source Code Context (Business Logic)
     {code_context}

     ## Existing Test Patterns
     {test_context}

     Generate a comprehensive list of test scenarios. For each scenario provide:
     1. Scenario name (descriptive, Gherkin-style)
     2. Category: happy_path | business_rule | validation | error_handling | boundary | security
     3. Description of what is being tested and why
     4. Expected outcome
     5. Knowledge sources used (which spec/code/test chunks informed this scenario)
     6. Confidence level (high/medium/low) based on how well-grounded the scenario is

     IMPORTANT: Go beyond contract testing. Use the source code context to identify:
     - Business rule branches (if/else, switch)
     - Validation logic (custom validators, annotations)
     - Error handling paths (try/catch, custom exceptions)
     - Data transformation logic (mappers, converters)
     ```
   - Output format: structured JSON array of `TestScenario` objects.

2. **Implement `agents/scenario_generator.py`:**
   - LangGraph node function.
   - Takes `AgentState`, formats the prompt with the context package.
   - Calls Claude Sonnet via `ChatAnthropic` with structured output (Pydantic model).
   - Parses response into `list[TestScenario]`.
   - Appends to `reasoning_chain` which sources were used.

3. **Define `TestScenario` Pydantic model:**
   ```python
   class TestScenario(BaseModel):
       name: str
       category: Literal["happy_path", "business_rule", "validation", "error_handling", "boundary", "security"]
       description: str
       expected_outcome: str
       knowledge_sources: list[str]
       confidence: Literal["high", "medium", "low"]
       preconditions: list[str]
       test_data: dict  # Key-value pairs for data-driven testing
   ```

4. **Write test:** Generate scenarios for the sample `POST /orders` endpoint. Verify at least 5 scenarios are generated, including at least 1 `business_rule` category that references source code.

**Acceptance criteria:** Scenario generator produces diverse, categorized test scenarios. Business rule scenarios reference specific code branches. Output is structured and parseable.

---

### Day 8 (Wed): Karate Feature Writer Agent

**Tasks:**

1. **Implement `agents/prompts/feature_writing.py`:**
   - System prompt establishes Claude as a Karate Framework expert.
   - Include Karate DSL reference material (retrieved from RAG reference collection).
   - User prompt template:
     ```
     Convert the following test scenario into a valid Karate .feature file.

     ## Scenario
     {scenario_json}

     ## Karate Syntax Reference
     {karate_reference_chunks}

     ## Existing Test Patterns (for style consistency)
     {existing_test_chunks}

     Requirements:
     - Use proper Feature/Scenario/Given/When/Then structure
     - Include Background section for shared setup (auth, base URL)
     - Use Karate's match assertions (not generic assert)
     - Include data-driven Examples table where applicable
     - Add comments explaining which business rule is being tested
     - Use karate.callSingle() for shared auth setup
     - Use JSON embedded in the feature file for request bodies
     - Tag scenarios with @category (e.g., @business_rule, @happy_path)
     ```

2. **Implement `agents/feature_writer.py`:**
   - LangGraph node function.
   - Iterates over each `TestScenario` in state.
   - For each scenario, retrieves Karate syntax examples from RAG.
   - Calls Claude Sonnet to generate the `.feature` file content.
   - Basic syntax validation: check for `Feature:`, `Scenario:`, `Given`, `When`, `Then` keywords.
   - Output: `list[GeneratedFeature]` with `filename`, `content`, `scenario_ref`, `reasoning`.

3. **Implement `GeneratedFeature` model:**
   ```python
   class GeneratedFeature(BaseModel):
       filename: str          # e.g., "post-orders-gold-discount.feature"
       content: str           # Full .feature file content
       scenario_name: str
       knowledge_sources: list[str]
       reasoning: str         # Why this test was generated this way
   ```

4. **Write test:** Given a sample `TestScenario`, generate a `.feature` file. Verify it contains valid Karate DSL structure. Verify business rule comments are present.

**Acceptance criteria:** Feature writer produces syntactically plausible `.feature` files. Each file includes comments tracing back to the knowledge source. Files follow Karate conventions.

---

### Day 9 (Thu): End-to-End Agent Orchestration

**Tasks:**

1. **Wire the full LangGraph workflow in `agents/graph.py`:**
   - Connect all implemented nodes: `retrieve_context` → `generate_scenarios` → `write_features`.
   - Add the `human_review` node as a LangGraph `interrupt` (pause for approval before execution).
   - Implement state transitions and error handling at each node.

2. **Build the `generate` CLI command:**
   ```
   python -m cli.app generate "POST /orders"
   ```
   - Runs the graph up to `human_review`.
   - Prints each generated scenario with its reasoning chain.
   - Prints each generated `.feature` file.
   - Prompts: `[A]pprove / [R]eject / [E]dit for each feature`.
   - On approve: writes `.feature` file to `karate_project/src/test/java/karate/generated/`.

3. **Implement reasoning chain display:**
   - For each scenario and feature file, show:
     ```
     📋 Scenario: Gold customer discount applied
     📂 Sources: OrderService.createOrder() (code), POST /orders schema (spec)
     🎯 Confidence: HIGH
     ```

4. **Integration test:** Full end-to-end run from endpoint to generated `.feature` files on disk.

**Acceptance criteria:** `python -m cli.app generate "POST /orders"` produces reviewable `.feature` files with reasoning chains. Approved files are written to the Karate project directory.

---

### Day 10 (Fri): Prompt Tuning & Quality Iteration

**Tasks:**

1. **Run the generator against real target API endpoints** (or realistic sample data). Collect the first batch of generated scenarios and features.

2. **Quality review session with QA/SDET engineer:**
   - Compare generated scenarios against what a human tester would write.
   - Identify missing scenario categories.
   - Identify Karate syntax errors or anti-patterns.
   - Document feedback for prompt refinement.

3. **Iterate on prompts:**
   - Refine `scenario_generation.py` prompt based on missing categories.
   - Refine `feature_writing.py` prompt based on syntax issues.
   - Add negative examples ("do NOT generate tests like this") if needed.
   - Tune retrieval parameters: adjust `top_k`, chunk sizes, relevance thresholds.

4. **Add Karate syntax validation:**
   - Implement a basic linter in `agents/feature_writer.py` that checks:
     - Feature/Scenario structure is present.
     - `Given url` or `Given path` exists.
     - `When method` step exists.
     - `Then status` assertion exists.
     - JSON payloads are valid JSON.
   - If validation fails, auto-retry with the error message appended to the prompt (1 retry).

**Acceptance criteria:** Generated features pass basic syntax linting. QA engineer confirms ≥60% of scenarios are relevant and useful. At least one business-rule scenario per endpoint that would not have been generated from spec alone. Week 2 deliverable complete.

---

## 5. Week 3 — Execution, Analysis & Feedback Loop

**Goal:** Full loop: ingest → retrieve → generate → review → execute → analyze → self-correct.

### Day 11 (Mon): Karate Test Executor Integration

**Tasks:**

1. **Implement `executor/runner.py`:**
   - Trigger Karate test execution via Maven subprocess:
     ```python
     def run_tests(feature_path: str, env: str = "dev") -> ExecutionResult:
         cmd = f"mvn test -Dkarate.options='{feature_path}' -Dkarate.env={env}"
         result = subprocess.run(cmd, shell=True, capture_output=True, cwd=KARATE_PROJECT_PATH)
         return parse_execution(result)
     ```
   - Capture: exit code, stdout/stderr, path to generated report.
   - Support running individual feature files or a directory.

2. **Implement `executor/report_parser.py`:**
   - Parse Karate's JSON results file (`target/karate-reports/karate-summary-json.txt`).
   - Extract per-scenario: name, status (pass/fail), duration, failure message, failure step.
   - Map back to the `GeneratedFeature` that produced it.

3. **Verify the Karate project setup:**
   - Ensure `pom.xml` has Karate dependencies, test runner class, and report configuration.
   - Run an existing (manually written) `.feature` file to confirm the pipeline works.

4. **Add `execute` CLI command:**
   ```
   python -m cli.app execute --env dev
   python -m cli.app execute --feature generated/post-orders-gold-discount.feature
   ```

**Acceptance criteria:** Can execute generated `.feature` files via the CLI and get structured pass/fail results.

---

### Day 12 (Tue): Result Analyzer Agent

**Tasks:**

1. **Implement `agents/prompts/result_analysis.py`:**
   - Prompt Claude Haiku to classify each failure:
     ```
     Classify this test failure and suggest a fix.

     ## Failed Test
     Feature file: {feature_content}
     Failure message: {failure_message}
     Failed step: {failed_step}

     ## Relevant Knowledge Base Context
     {context_for_endpoint}

     Classify as one of:
     - test_issue: Bad assertion, wrong expected value, syntax error, invalid JSONPath
     - application_bug: The API behavior doesn't match the business logic in source code
     - data_issue: Test data is invalid or missing preconditions
     - environment_issue: Service unreachable, auth failure, timeout

     For test_issue: provide the corrected .feature file content.
     For application_bug: describe the suspected bug with evidence from source code.
     ```

2. **Implement `agents/result_analyzer.py`:**
   - LangGraph node function.
   - For each failed test, call Claude Haiku with the failure context.
   - Parse structured output into `FailureAnalysis`.
   - For `test_issue` classifications, include the suggested fix.

3. **Wire the retry loop in `agents/graph.py`:**
   - After `analyze_results`, if there are `test_issue` failures and `retry_count < 2`:
     - Feed the failure analysis back to `feature_writer` with the correction context.
     - Increment `retry_count`.
     - Re-execute the corrected features.
   - If not a test issue or retries exhausted, proceed to `done`.

4. **Write test:** Given a deliberately broken `.feature` file and its failure message, verify the analyzer correctly classifies it and suggests a valid fix.

**Acceptance criteria:** Analyzer correctly classifies test failures into the four categories. For `test_issue` failures, the suggested fix is valid Karate syntax.

---

### Day 13 (Wed): Human-in-the-Loop CLI

**Tasks:**

1. **Enhance `cli/app.py` with Rich-based interactive review UI:**
   - Display scenarios in a table with columns: Name, Category, Confidence, Sources.
   - For each feature file, display with syntax highlighting (Rich's `Syntax` class).
   - Show reasoning chain: "This scenario was generated because `OrderService.createOrder()` contains a branch: `if (customer.tier == 'gold' && total > 500)`."
   - Interactive commands: `[a]pprove`, `[r]eject`, `[e]dit` (opens in `$EDITOR`), `[s]kip`.

2. **Implement feedback storage:**
   - When engineer approves: store the feature file in RAG as a "verified" example (boosts future retrieval).
   - When engineer rejects with reason: store the rejection reason as negative feedback.
   - When engineer edits: store the edited version as the canonical example.

3. **Add a `run-full` CLI command that executes the entire loop:**
   ```
   python -m cli.app run-full "POST /orders" --env dev
   ```
   - Ingest (if not already done) → Retrieve → Generate → Review → Execute → Analyze → Display results.

**Acceptance criteria:** Engineer can review generated tests with full context, approve/reject/edit, and feedback is stored in RAG for future improvement.

---

### Day 14 (Thu): Self-Correction Loop & Continuous Learning

**Tasks:**

1. **Implement the full self-correction cycle:**
   - Generate → Execute → Analyze → if test_issue → Regenerate with failure context → Re-execute.
   - Log each correction: original feature, failure, corrected feature, success/failure.
   - Cap at 2 retries per feature file.

2. **Implement continuous learning storage:**
   - Approved tests are added to the `existing_tests` collection in ChromaDB.
   - Engineer corrections (edits) update the stored chunks.
   - Track "generation quality" over time: % of tests approved without edits.

3. **Run the full loop on sample data end-to-end.** Fix any issues with state management, error handling, or graph transitions.

**Acceptance criteria:** The self-correction loop resolves at least one test_issue failure automatically. Approved tests are discoverable in future RAG retrievals.

---

### Day 15 (Fri): Integration Testing & Bug Fixes

**Tasks:**

1. **End-to-end integration test against sample data:**
   - Ingest sample spec + source code + existing tests.
   - Generate tests for 2–3 endpoints.
   - Execute all generated tests.
   - Verify the full loop completes without crashes.

2. **Fix all discovered issues:** Prompt issues, retrieval quality, graph state bugs, Karate execution problems.

3. **Add error handling throughout:**
   - LLM API errors: retry with exponential backoff (3 attempts).
   - Karate execution timeouts: configurable timeout, graceful failure.
   - ChromaDB errors: log and continue with degraded results.
   - Invalid LLM output: fallback to re-prompting with stricter output format instructions.

**Acceptance criteria:** Full loop runs reliably on sample data. No unhandled exceptions. Week 3 deliverable complete.

---

## 6. Week 4 — Hardening, Metrics & Demo

**Goal:** Working MVP demo with real APIs. Side-by-side depth comparison. Metrics report. Stakeholder presentation.

### Day 16 (Mon): Real API Hardening

**Tasks:**

1. **Ingest real target API knowledge:**
   - Ingest the actual OpenAPI spec(s) for the 1–2 selected internal APIs.
   - Ingest the corresponding service layer source code (controllers, services, validators, mappers).
   - Ingest any existing Karate test suites for these APIs.

2. **Run the generator against real endpoints.** Document all issues:
   - Retrieval misses (wrong code chunks returned).
   - Scenario gaps (missing obvious test cases).
   - Syntax errors in generated features.
   - Endpoint-to-code mapping failures.

3. **Tune and fix:**
   - Adjust endpoint-to-code mapping logic for real annotation patterns.
   - Tune `top_k` and relevance thresholds based on real data.
   - Add domain-specific context to prompts if needed (e.g., naming conventions, auth patterns).

**Acceptance criteria:** Generator produces useful tests for at least 3 real endpoints. Business logic scenarios are present that wouldn't come from spec-only generation.

---

### Day 17 (Tue): Metrics Dashboard

**Tasks:**

1. **Implement metrics collection** (add to `agents/graph.py` and `cli/app.py`):
   - **Test generation speed:** Time from endpoint selection to `.feature` files on disk.
   - **Syntactic accuracy:** % of generated features that pass Karate execution on first run.
   - **Business logic coverage ratio:** Count of scenarios per category (business_rule vs. happy_path vs. validation, etc.).
   - **Knowledge source utilization:** % of scenarios referencing 2+ knowledge sources.
   - **Self-correction rate:** % of test_issue failures auto-fixed in retry loop.
   - **Scenario completeness:** (Manual) Expert comparison score.

2. **Build a `metrics` CLI command:**
   ```
   python -m cli.app metrics
   ```
   - Reads stored generation logs and displays a summary table via Rich.

3. **Run generation + execution on all target endpoints. Collect metrics.**

**Acceptance criteria:** Metrics are tracked and displayable. Initial numbers for all 6 quantitative metrics are captured.

---

### Day 18 (Wed): DB Schema Adapter (Stretch) or Additional Hardening

**If ahead of schedule — implement the stretch goal:**

1. **Implement `ingestion/db_schema_adapter.py`:**
   - Use SQLAlchemy's `inspect` module with a read-only connection to a dev/staging database.
   - Extract: table names, column definitions (name, type, nullable, default), primary keys, foreign key relationships, unique constraints, check constraints, indexes.
   - Chunking: one chunk per table, including all constraints and relationships.
   - Tag with endpoint by matching table names to service code references.

2. **Update the retriever** to include DB context in the `ContextPackage`.

3. **Update scenario generator prompt** to use DB context for generating JDBC verification scenarios.

**If not ahead of schedule — use this day for additional hardening:**
- Fix remaining issues from Day 16.
- Add more Karate syntax examples to RAG.
- Improve prompt engineering based on real results.
- Add comprehensive error handling and logging.

---

### Day 19 (Thu): Demo Preparation

**Tasks:**

1. **Prepare the live demo script:**
   - Demo flow: Select an endpoint → show knowledge ingestion → show context retrieval → show scenario generation with reasoning → show feature file output → execute tests → show results.
   - Target: endpoint to running tests in under 5 minutes.

2. **Prepare the side-by-side comparison:**
   - For the same endpoint, show:
     - Spec-only generation: ~1-2 surface-level contract tests.
     - Multi-source generation: 5-7+ tests including business rules, validation, error handling.
   - Visualize in a table or slide.

3. **Write `docs/architecture.md`:**
   - System architecture diagram (can be Mermaid).
   - Component descriptions.
   - Data flow diagram.
   - Technology choices and rationale.

4. **Write `docs/setup_guide.md`:**
   - Prerequisites.
   - Step-by-step installation.
   - Configuration.
   - Running the first generation.

5. **Dry-run the demo.** Fix any issues. Time it.

---

### Day 20 (Fri): Final Demo & Stakeholder Presentation

**Tasks:**

1. **Final metrics collection.** Update the metrics dashboard with all results from the MVP period.

2. **Deliver the stakeholder demo:**
   - Live demo of the full workflow.
   - Side-by-side comparison showing depth of multi-source vs. spec-only.
   - Metrics report.
   - Architecture overview and Phase 2 roadmap.

3. **Collect structured feedback** from 3+ engineers using a survey covering:
   - Trust in generated business logic tests.
   - Usefulness of reasoning chains.
   - Suggestions for improvement.
   - Willingness to use in daily workflow.

4. **Document lessons learned** and prioritized backlog for Phase 2.

**Acceptance criteria:** Successful live demo. Metrics report delivered. Feedback collected. Phase 2 backlog created. MVP complete.

---

## 7. Success Criteria Summary

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| Generation Speed | 5–10x faster than manual | Time comparison |
| Syntactic Accuracy | >85% first-run pass rate | Karate execution results |
| Business Logic Coverage | ≥3x more branches than spec-only | Side-by-side scenario count |
| Scenario Completeness | ≥80% of human-written scenarios | Expert review |
| Knowledge Source Utilization | >60% of scenarios use 2+ sources | Reasoning chain analysis |
| Self-Correction Rate | >50% of test_issues auto-fixed | Retry loop metrics |
| Engineer Satisfaction | Positive from 3+ engineers | Post-demo survey |

---

## 8. Key Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| LLM Provider | Claude API (Anthropic) | Strong code understanding, structured output, excellent reasoning over business logic. Use Sonnet for generation, Haiku for analysis. |
| Agent Framework | LangGraph | Graph-based orchestration with built-in state management, human-in-the-loop interrupts, and conditional edges for retry loops. |
| Vector DB | ChromaDB | Lightweight, local-first, supports metadata filtering for multi-source retrieval. No infrastructure overhead for MVP. |
| Embeddings | all-MiniLM-L6-v2 | Fast, runs locally, good semantic similarity for code and docs. Avoids additional API costs. |
| Code Parsing | tree-sitter | Production-grade AST parser. Structural awareness for accurate method-level chunking. Same tool used by GitHub Copilot. |
| Interface | CLI (Typer + Rich) | Fastest to build. Engineers are comfortable in terminal. Web UI deferred to Phase 2. |

---

## 9. Risk Watchlist

| Risk | Trigger | Mitigation |
|------|---------|------------|
| Claude generates invalid Karate syntax | >20% of features fail syntax linting | Add more RAG examples, tighten prompt constraints, implement auto-retry with error context |
| Endpoint-to-code mapping failures | Source code chunks don't match endpoints | Fall back to naming convention heuristics, allow manual mapping config |
| Token budget overrun | Multi-source context exceeds token limits | Implement context compression (summarize code chunks), use `top_k` reduction, cache retrieval |
| Scope creep | Attempting DB adapter before core is solid | Strict priority: core loop must be demo-ready before any stretch goals |
| LLM API latency | >30s per feature generation | Batch scenarios, parallelize feature writing, cache repeated context retrievals |

---

## 10. Phase 2 Preview (Post-MVP)

Upon successful MVP demo, the following are prioritized for Phase 2 (Months 2–3):

1. **Database schema ingestion** — SQLAlchemy introspection adapter, JDBC verification test generation.
2. **BRD/User story ingestion** — Jira/Confluence connector, acceptance criteria → scenario mapping.
3. **Self-healing from CI/CD** — Monitor Karate test failures in CI, auto-generate fix PRs.
4. **Web UI** — Flask/React interface for broader team adoption beyond CLI users.
5. **LangSmith observability** — Trace agent reasoning, debug retrieval quality, evaluate generation accuracy at scale.
