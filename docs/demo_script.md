# Live Demo Script & Side-by-Side Comparison

**Target Time:** Under 5 minutes.

## The Pitch
"Today we are demonstrating the AI Agentic Karate Framework. Traditional LLM code generation relies strictly on OpenAPI specs, resulting in shallow contract tests. Our solution ingests OpenAPI specs, actual Java source code, and existing Karate testing patterns to generate deep, business-logic-aware test suites that auto-correct themselves upon failure."

## Demo Flow

### 1. The Context (30s)
*Show `OrderService.java` on screen.*
"Notice this business rule: GOLD tier customers receive a 10% discount on orders over $500. A standard OpenAPI spec knows nothing about this rule. Let's see how our agent handles it."

### 2. Knowledge Base Stats (15s)
```bash
python3 -m cli.app stats
```
"Our agent has pre-ingested the OpenAPI spec, the backend Java code, and Karate syntax examples into a ChromaDB vector store."

### 3. Test Generation (60s)
```bash
python3 -m cli.app generate "POST /orders"
```
"Watch as the LangGraph agent retrieves the multi-source context and reasons through it. Notice the reasoning chains—it explicitly mentions finding the `total > 500` rule in `OrderService.java`."

*(Auto-approve the generated feature files)*

### 4. Execution & WireMock (30s)
```bash
python3 -m cli.app execute --env dev
```
"The agent automatically spins up a standalone WireMock server seeded with data-driven stubs, triggers Maven using Java 17, and parses the Karate JSON reports."

### 5. Failure Analysis (if applicable) & Results (30s)
"The agent uses Claude Haiku to analyze the results. Notice the rich CLI table showing Pass/Fail states and execution durations."

### 6. Metrics Dashboard (15s)
```bash
python3 -m cli.app metrics
```
"We persist metrics across runs. You can see our knowledge source utilization is high, proving the LLM is synthesizing data across spec and code."

---

## Side-by-Side Comparison

Prepare a slide with this data:

| Metric | Spec-Only Generation (Baseline) | Multi-Source AI Agent (Ours) |
|--------|--------------------------------|------------------------------|
| **Total Scenarios** | 2 | 23 |
| **Happy Path** | 201 Created | 201 Standard, 201 GOLD Discount, 201 GOLD threshold |
| **Validation Paths**| 400 Bad Request | Empty items array, negative quantity, zero price, missing fields |
| **Data Strategy** | Static JSON bodies | CSV Data-driven `Scenario Outline` |
| **Code Awareness** | None | Understands Java enums, custom exceptions, and branching logic |
| **Self-Healing** | None | LangGraph auto-retry loop for syntax errors |
