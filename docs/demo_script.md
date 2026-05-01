# AI-Orchestrated Karate Test Generation — Demo Script

> **Audience:** Engineering manager + team  
> **Duration:** ~20 minutes  
> **Goal:** Demonstrate the pipeline's capabilities and justify LLM API access request  
> **Prerequisites:** Terminal open at project root, Docker running, IDE with project loaded

---

## 1. Opening — The Problem (2 min)

**Talking points:**
- "Manual API test writing is slow, repetitive, and misses edge cases"
- "API specs tell you *what* exists, but not the *business rules* hidden in source code and database constraints"
- "What if an AI agent could ingest your API spec, Java source code, AND database schema — then generate production-quality test suites that test things a human would miss?"

---

## 2. Architecture Overview (3 min)

Open [docs/architecture.md](file:///Users/fabiangonzalez/Documents/karate-automation-project/docs/architecture.md) or draw on whiteboard:

```
┌─────────────┐   ┌───────────────┐   ┌──────────────┐   ┌──────────────┐
│ OpenAPI Spec │   │ Java Source   │   │ Existing     │   │ PostgreSQL   │
│ (YAML)       │   │ Code (AST)   │   │ Karate Tests │   │ DB Schema    │
└──────┬──────┘   └──────┬────────┘   └──────┬───────┘   └──────┬───────┘
       │                 │                    │                   │
       ▼                 ▼                    ▼                   ▼
   ┌─────────────────────────────────────────────────────────────────┐
   │                    ChromaDB Vector Store                        │
   │  (api_specs | source_code | existing_tests | karate_ref | db_schemas)  │
   └──────────────────────────┬──────────────────────────────────────┘
                              │ RAG Retrieval
                              ▼
                    ┌─────────────────────┐
                    │    LLM Agent        │
                    │ (Claude / GPT / …)  │
                    └─────────┬───────────┘
                              │
               ┌──────────────┼──────────────┐
               ▼              ▼              ▼
        ┌────────────┐ ┌────────────┐ ┌────────────┐
        │ Scenarios  │ │ .feature   │ │ Execution  │
        │ (JSON)     │ │ Files      │ │ + Analysis │
        └────────────┘ └────────────┘ └────────────┘
```

**Key point:** "The system doesn't just look at the API spec. It reasons across *four* knowledge sources simultaneously."

---

## 3. Live Demo: Knowledge Ingestion (5 min)

### 3a. Show the input sources

```bash
# The API spec the agent reads
cat data/sample_specs/orders-api.yaml | head -40
```

```bash
# The Java business logic the agent analyzes
cat data/sample_source/OrderService.java
```

**Highlight:** "Notice the GOLD customer discount rule on line 18 — this is NOT in the API spec."

### 3b. Show the database schema

```bash
# Start the seeded PostgreSQL
docker compose up -d

# Show the schema
docker exec karate-orders-db psql -U karate -d orders_db -c "\dt+" -c "\dv"
```

```bash
# Show the constraints the agent discovers
docker exec karate-orders-db psql -U karate -d orders_db -c "\d orders"
```

**Highlight:** "The agent discovers FK constraints, CHECK constraints, ENUM types, NUMERIC precision limits — none of which appear in the API spec."

### 3c. Run the ingestion pipeline

```bash
# Ingest the database schema into the knowledge base
python3 -m cli.app ingest-schema
```

Expected output:
```
✅ Ingested 4 table schemas:
  - customers (6 columns)
  - order_items (6 columns) 🔗
  - orders (8 columns) 🔗
  - order_summary (9 columns)
```

```bash
# Show the full knowledge base stats
python3 -m cli.app stats
```

Expected output:
```
┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ Origin Type ┃ Document Count ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ spec        │ 5              │
│ code        │ 6              │
│ test        │ 46             │
│ reference   │ 2              │
│ schema      │ 4              │
└─────────────┴────────────────┘
```

**Talking point:** "63 knowledge chunks indexed across 5 source types. The agent retrieves the most relevant ones for each endpoint before generating tests."

---

## 4. Generated Test Showcase (7 min)

> **Note:** The test generation step requires LLM API access, which we're in the process of requesting.
> What follows are **real outputs** from an earlier run against Claude Sonnet 4.

### 4a. Overview — 23 scenarios generated

```bash
ls karate_project/src/test/java/karate/generated/post-orders-create-order-* | wc -l
```

**Talking point:** "From a single command — `generate "POST /orders"` — the agent produced 23 distinct test scenarios across 6 categories: business rules, validation, boundary, error handling, happy path, and security."

### 4b. Schema-driven tests (the "wow" moment)

**Open this file in IDE:**
`karate_project/src/test/java/karate/generated/post-orders-create-order-with-a-non-existent-customerid-returns-400-or-4.feature`

**Highlight lines 3-6:**
```gherkin
# Business Rule: orders.customer_id is a FK to customers.id.
# Submitting a customerId that does not exist in the customers table must be rejected
# by the API with a meaningful client error (400 or 404), not a 500 Internal Server Error.
# Source: postgresql://public/orders — customer_id FK → customers.id ON DELETE CASCADE
```

**Talking point:** "This test scenario was NOT in the API spec. The agent discovered the foreign key constraint by introspecting the database schema, then generated a test that sends a non-existent customer ID and verifies the API doesn't return a 500."

### 4c. NUMERIC boundary test

**Open:**
`karate_project/src/test/java/karate/generated/post-orders-create-order-with-very-large-totalamount-near-numeric-12-2-p.feature`

**Highlight the Examples table (lines 88-92):**
```gherkin
Examples:
  | price             | expectedStatus |
  | 9999999999.99     | 201            |
  | 99999999999.99    | 400            |
  | 999999999999.99   | 400            |
```

**Talking point:** "The agent read that `total_amount` is `NUMERIC(12,2)` from the database, calculated the maximum value (9,999,999,999.99), and generated boundary tests at, above, and well-above the limit. A human tester would need to check the DB schema manually to know this."

### 4d. JDBC database verification (the "deep verification" moment)

**Open:**
`karate_project/src/test/java/karate/generated/post-orders-create-order-with-gold-tier-and-multiple-items-totalling-abo.feature`

**Scroll to lines 63-130 (the JDBC section) and highlight:**

```gherkin
# --- JDBC Database Verification ---
* def stmtOrders = conn.prepareStatement("SELECT status, total_amount, discount_applied FROM orders WHERE id = ?")
* match rsOrders.getString('status') == 'PENDING'
* match rsOrders.getBigDecimal('total_amount').doubleValue() == 550.0
* match rsOrders.getBigDecimal('discount_applied').doubleValue() == 55.0
```

**Then show the view verification (lines 117-128):**

```gherkin
# Verify the order_summary view reflects the correct denormalized state
* match rsSummary.getString('customer_tier') == 'GOLD'
* match rsSummary.getBigDecimal('final_amount').doubleValue() == 495.0
* match rsSummary.getLong('item_count') == 2
```

**Talking point:** "After the API call, the generated test opens a JDBC connection to the database and verifies the row was persisted correctly — checking the orders table, the order_items table, AND a denormalized view. The agent discovered the `order_summary` view from the schema and decided to test it on its own."

### 4e. Negative test — JDBC confirms no write on error

**Back to the FK violation file, highlight lines 49-63:**

```gherkin
# JDBC Verification: Confirm no order record was inserted
* match rs.getInt('cnt') == 0
```

**Talking point:** "For error scenarios, the agent verifies the database was NOT modified — confirming that the API layer properly rejected the invalid request before it hit the DB."

---

## 5. Unit Test Suite & CI Readiness (2 min)

```bash
python3 -m pytest tests/ -v --tb=short 2>&1 | tail -5
```

Expected:
```
======================= 48 passed, 81 warnings in 8.24s ========================
```

**Talking point:** "48 unit tests covering the ingestion adapters, RAG pipeline, vector store, and agent logic — all passing, all ready for CI."

---

## 6. LLM Provider Flexibility (1 min)

**Open `.env` and show:**

```env
# Just change this line to switch providers:
LLM_PROVIDER=anthropic   # or "openai"
```

**Talking point:** "The system is provider-agnostic. Once we get API access, we just set the provider and key. If the corporate policy later mandates a different model, it's a one-line config change — zero code changes."

---

## 7. Closing — What We Need (2 min)

**Slide / talking points:**

1. **What we've built:** A multi-source RAG pipeline that generates schema-aware, JDBC-verified Karate test suites from API specs + source code + database schemas
2. **What it produces:** 23 test scenarios from a single endpoint, including FK violations, NUMERIC boundary tests, and database state verification — tests that manual QA would take days to write
3. **What we need:** API access to Claude or GPT to enable the generation step in our environment
4. **ROI:** Each generated test suite replaces ~2-3 days of manual QA effort per endpoint. For a service with 20 endpoints, that's 40-60 engineering days saved per release cycle

---

## Quick Reference — Commands for Live Portions

| Step | Command |
|------|---------|
| Start DB | `docker compose up -d` |
| Show schema | `docker exec karate-orders-db psql -U karate -d orders_db -c "\d orders"` |
| Ingest schema | `python3 -m cli.app ingest-schema` |
| Show stats | `python3 -m cli.app stats` |
| Run tests | `python3 -m pytest tests/ -v --tb=short` |
| Count features | `ls karate_project/src/test/java/karate/generated/post-orders-* \| wc -l` |

> **⚠️ Do NOT run `python3 -m cli.app generate` during the demo** — it requires LLM API access.
> Instead, walk through the pre-generated feature files in the IDE.
