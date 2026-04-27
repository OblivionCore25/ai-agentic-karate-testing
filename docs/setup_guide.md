# Setup Guide

This guide walks you through setting up and running the Karate AI Agent.

## Prerequisites
- Python 3.11+
- Java 17 (Required to bypass `sun.misc.Unsafe` errors in Karate 1.4.1)
- Maven 3.8+
- Anthropic API Key

## 1. Installation

```bash
# Set up a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## 2. Configuration

Create a `.env` file in the root directory:

```env
ANTHROPIC_API_KEY=sk-ant-api03...
CLAUDE_MODEL_GENERATION=claude-3-5-sonnet-20241022
CLAUDE_MODEL_ANALYSIS=claude-3-haiku-20240307
CHROMA_PERSIST_DIR=./chroma_data
KARATE_PROJECT_PATH=./karate_project
LOG_LEVEL=INFO
```

## 3. Usage

### Step 1: Ingest Knowledge
Load the API specs, Java source code, and existing test patterns into the RAG vector database.

```bash
python3 -m cli.app ingest \
  --spec data/sample_specs/orders-api.yaml \
  --source data/sample_source/ \
  --tests data/sample_features/ \
  --karate-examples data/karate_syntax_examples/
```

### Step 2: Generate Tests
Generate test scenarios and feature files for a specific endpoint.

```bash
python3 -m cli.app generate "POST /orders"
```
Follow the interactive prompts to approve the generated tests.

### Step 3: Execute Tests
Run the generated tests. The framework will automatically start a standalone WireMock server to simulate the backend.

```bash
python3 -m cli.app execute --env dev
```

### Step 4: Run the Full Autonomous Loop
Execute the entire pipeline: Retrieve → Generate → Write → Execute → Analyze → Self-Correct.

```bash
python3 -m cli.app run-full "POST /orders"
```

### Step 5: View Metrics
Check the effectiveness of the pipeline over time.

```bash
python3 -m cli.app metrics
```
