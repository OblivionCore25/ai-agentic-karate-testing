# Speaker Notes — AI-Orchestrated API Test Generation

> **Duration:** ~15–20 minutes  
> **Audience:** Engineering manager + team leads  
> **Goal:** Demonstrate the pipeline's value and secure LLM API access approval  

---

## Slide 1 — Title (30 sec)

> "Thanks for taking the time today. I want to walk you through something I've been building — an AI-powered pipeline that can generate comprehensive API test suites in minutes instead of days.
>
> The key idea is that this isn't just another code generator. It reads four different knowledge sources — your API spec, your Java source code, your existing test patterns, and even your database schema — and cross-references all of them to produce tests that are deeper and more thorough than what we'd typically write by hand.
>
> Let me show you what I mean."

**[Click → Next]**

---

## Slide 2 — The Cost of Manual API Testing (1.5 min)

> "Let's start with the problem we all live with every day.
>
> **First, it's time-intensive.** Writing comprehensive API tests for a single endpoint — including edge cases, validation, security scenarios — that typically takes two to three days of QA engineering time. And that's for *one* endpoint.
>
> **Second, we have blind spots.** When we write tests manually, we usually work from the API spec. But the spec doesn't tell you about the business rules buried in the Java service layer, or the database constraints like foreign key relationships and data type limits. Those blind spots are often where production defects come from.
>
> **Third, test drift.** As services evolve, our tests fall behind. We either slow down releases to update tests, or we skip testing and accept more risk in production.
>
> So the question is — what if we could solve all three of these at once?"

**[Click → Next]**

---

## Slide 3 — Before vs. After (2 min)

> "Here's what the difference looks like side by side.
>
> **Time per endpoint** goes from two to three days down to about fifteen minutes of generation plus review time.
>
> **Scenarios generated** — manually, we typically write five to eight tests covering the common paths. The AI agent generates twenty to twenty-five, including boundary conditions, security checks, and database constraint violations.
>
> **Knowledge sources** — this is the big one. Today we test against the API spec only. The agent also reads the Java source code to find business rules, existing tests to match our team's style, and the database schema to discover constraints.
>
> **Database constraint testing** — honestly, how often do we test for foreign key violations or numeric overflow? Rarely. The agent does this automatically because it reads the schema.
>
> **Database state verification** — the generated tests don't just check the API response. They also open a JDBC connection and verify the data was actually persisted correctly in the database. That's something we almost never do in our manual tests.
>
> And importantly — **human oversight stays**. Every generated test goes through human review before it's committed. The engineer approves, edits, or rejects."

**[Click → Next]**

---

## Slide 4 — How It Works (1.5 min)

> "Here's how the pipeline works at a high level.
>
> At the top, you can see the four knowledge sources the agent reads: the OpenAPI spec for endpoint definitions and schemas, the Java source code for business logic and validation rules, existing test files for team patterns and style conventions, and the PostgreSQL database for constraints, foreign keys, and data types.
>
> The AI agent — which is powered by a large language model — cross-references all four sources simultaneously. That's what makes it different from tools that just read the API spec.
>
> At the bottom, you see what it produces: categorized test scenarios, which become executable test files, which then go through human review before they're approved. Nothing goes into the codebase without a human signing off."

**[Click → Next]**

---

## Slide 5 — What Makes This Different (2 min)

> "So what makes this fundamentally different from existing test generation tools?
>
> **Database-aware testing.** The agent connects to your PostgreSQL database and introspects the schema — it discovers foreign key relationships, data type limits, enum constraints, check rules. Then it generates test scenarios for each of those.
>
> For example, in our proof of concept, the `total_amount` column is defined as `NUMERIC(12,2)` in the database. The agent saw that, calculated the maximum value the column can hold — nine billion, nine hundred ninety-nine million — and generated boundary tests at, above, and well above that limit. A manual tester would need to open the database, check the column definition, and do that math themselves. The agent did it automatically.
>
> **Post-API database verification.** After each API call, the generated test doesn't just check that the API returned a 200. It opens a JDBC connection to the database and verifies the row was actually inserted with the correct values — the right discount amount, the right status, the right line item totals. It even discovered a denormalized view called `order_summary` in the database and generated assertions against it, without being told the view existed.
>
> These are the kinds of tests that catch production defects before they reach users."

**[Click → Next]**

---

## Slide 6 — Proof of Concept Results (2 min)

> "Let me show you the concrete results from our proof of concept on the `POST /orders` endpoint.
>
> From a single command, the agent generated **twenty-three test scenarios** across **six categories** in about fifteen minutes.
>
> Looking at the breakdown: seven boundary tests — things like numeric overflow, the exact discount threshold at five hundred dollars and one cent, zero-price items. Six business rule tests covering the GOLD customer discount logic, tier defaults, multi-item totals. Five validation tests for missing required fields, empty arrays, invalid enum values. Two security tests for missing auth headers and expired tokens. And one error handling test for a foreign key violation — submitting a customer ID that doesn't exist in the database.
>
> Here's what's important: **a manual QA engineer would typically write five to eight of these.** And specifically, **five of these twenty-three scenarios** could only be discovered by reading the database schema. No amount of API spec reading would surface the numeric overflow test or the foreign key violation test. Those are the hidden defects this catches."

**[Click → Next]**

---

## Slide 7 — Human-in-the-Loop (1.5 min)

> "I want to be clear about governance here, because I know this matters.
>
> **The AI never pushes code.** It's a three-step process:
>
> **Step one** — the AI generates draft test files and runs them locally to verify the syntax is correct. If there are syntax errors, it self-corrects and retries.
>
> **Step two** — the QA engineer reviews every generated scenario in their IDE. They can edit test data, adjust assertions, remove irrelevant tests, or add new ones.
>
> **Step three** — the engineer explicitly approves the tests. Only then are they committed to the repo.
>
> And here's the key insight: **every approved test goes back into the knowledge base.** So the agent learns your team's patterns over time. The more tests you approve, the better the future generations match your style and standards. It's a continuous improvement loop."

**[Click → Next]**

---

## Slide 8 — Engineering Readiness (1 min)

> "From an engineering perspective, the platform is fully built and tested.
>
> We have forty-eight unit tests passing, covering the ingestion pipeline, the vector store, the agent logic, and the adapters. Docker infrastructure is provisioned for the PostgreSQL instance. Full documentation including architecture guides and setup instructions.
>
> On the architecture side, two things worth calling out: **it's provider-agnostic** — we can use Claude from Anthropic or GPT from OpenAI, switched with a single config line. And **it's self-correcting** — if a generated test has a syntax error, the agent automatically detects it, fixes it, and re-runs. No human intervention needed for syntax issues."

**[Click → Next]**

---

## Slide 9 — Projected Impact / ROI (1.5 min)

> "Let me put this in terms of projected impact.
>
> **Eighty percent reduction** in test writing time. **Three times more scenarios** per endpoint than manual testing. And **five or more hidden edge cases** discovered per endpoint that would be missed otherwise.
>
> Looking at the numbers: for a single endpoint, we go from two to three days down to fifteen minutes plus review time. For a typical service with twenty endpoints, that's **forty to sixty engineering days of manual work** reduced to **four to six days** — a savings of thirty-six to fifty-four engineering days per release cycle.
>
> And the coverage improvement isn't just about quantity. The database constraint testing and state verification mean we're catching classes of defects — numeric overflow, referential integrity violations, incorrect persistence — that we currently don't test for at all."

**[Click → Next]**

---

## Slide 10 — What We Need / The Ask (1 min)

> "So here's where we are and what we need.
>
> **Everything is built.** The pipeline, the database ingestion, the test generation, the self-correction loop, the human review workflow — it's all working. We've validated it with a proof of concept that generated twenty-three test scenarios with five database-driven edge cases.
>
> **The one thing we need is LLM API access** — either Anthropic Claude or OpenAI GPT. It's just API keys. No infrastructure changes, no new servers, no new deployments. One line in a config file.
>
> My proposal for next steps:
>
> **One** — request LLM API access through our standard approval process.
> **Two** — pilot on one service — the Orders API is ready to go.
> **Three** — measure the actual time savings against our current manual process, and expand based on those results.
>
> That's it. Happy to take any questions."

---

## Anticipated Questions & Answers

### "What LLM models does it use and what's the cost?"
> "It supports both Anthropic Claude and OpenAI GPT. For our proof of concept, each endpoint generation costs roughly two to five dollars in API calls — generating twenty-three test scenarios. That's the cost of about fifteen minutes of engineer time."

### "What if the LLM generates wrong or hallucinated tests?"
> "Two safeguards. First, the agent self-validates by running every generated test locally — if the syntax is invalid, it auto-corrects. Second, every test goes through human review. The engineer approves, edits, or rejects. Nothing reaches the codebase without human sign-off."

### "Does this replace QA engineers?"
> "No — it augments them. The agent handles the repetitive part of test writing so engineers can focus on exploratory testing, test strategy, and reviewing the AI's output for correctness. Think of it as a very thorough first draft."

### "How does it handle sensitive data or IP concerns?"
> "The API spec, source code, and schema metadata are sent to the LLM for generation. If that's a concern, we could explore using a self-hosted model in the future. The architecture is provider-agnostic, so switching is a config change."

### "Can it work with other databases besides PostgreSQL?"
> "Yes. The schema introspection uses SQLAlchemy, which supports PostgreSQL, MySQL, Oracle, and SQLite. We'd just change the connection string."

### "What happens when the API changes?"
> "You re-run the ingestion and generation for the changed endpoints. The agent re-reads the updated spec, source code, and schema, and generates new tests. Unchanged endpoints aren't affected."
