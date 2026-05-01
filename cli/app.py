import typer
import json
import logging
import os
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from typing import Optional

from config.logging_config import setup_logging
from config.settings import get_settings
from rag.vector_store import VectorStore
from rag.retriever import ContextRetriever
from ingestion.openapi_adapter import OpenAPIAdapter
from ingestion.source_code_adapter import SourceCodeAdapter
from ingestion.existing_tests_adapter import ExistingTestsAdapter
from executor.runner import run_tests
from metrics.collector import MetricsCollector, GenerationRun, ExecutionRun
import time
from datetime import datetime
from collections import Counter

app = typer.Typer(help="AI Agentic System for Automation Testing with Karate Framework")
console = Console()


@app.callback()
def main():
    setup_logging()


@app.command()
def ingest_spec(path: str = typer.Argument(..., help="Path to OpenAPI spec file")):
    """Ingest an OpenAPI 3.0 spec into the knowledge base."""
    adapter = OpenAPIAdapter()
    chunks = adapter.ingest(path)
    store = VectorStore()
    store.add_documents("spec", chunks)
    console.print(f"[green]Successfully ingested {len(chunks)} API endpoints.[/green]")


@app.command()
def ingest_source(path: str = typer.Argument(..., help="Path to Java source code directory")):
    """Ingest Java source code into the knowledge base."""
    adapter = SourceCodeAdapter()
    chunks = adapter.ingest(path)
    store = VectorStore()
    store.add_documents("code", chunks)
    console.print(f"[green]Successfully ingested {len(chunks)} Java methods.[/green]")


@app.command()
def ingest_tests(path: str = typer.Argument(..., help="Path to existing .feature files")):
    """Ingest existing Karate tests into the knowledge base."""
    adapter = ExistingTestsAdapter()
    chunks = adapter.ingest(path)
    # Determine if reference or test based on path heuristics or default to test
    origin = "reference" if "karate_syntax_examples" in path else "test"
    store = VectorStore()
    store.add_documents(origin, chunks)
    console.print(f"[green]Successfully ingested {len(chunks)} {origin} scenarios.[/green]")


@app.command()
def ingest(
    spec: str = typer.Option(..., help="Path to OpenAPI spec"),
    source: str = typer.Option(..., help="Path to source code directory"),
    tests: str = typer.Option(..., help="Path to existing features"),
    karate_examples: str = typer.Option(..., help="Path to Karate syntax examples"),
    project: str = typer.Option("", help="Project identifier for metadata tagging"),
    domain: str = typer.Option("", help="Domain identifier for metadata tagging"),
    db: str = typer.Option("", help="PostgreSQL connection string for schema ingestion"),
):
    """Run full ingestion pipeline."""
    with console.status("[bold blue]Ingesting knowledge base...") as status:
        store = VectorStore()

        status.update("[bold blue]Ingesting OpenAPI spec...")
        spec_chunks = OpenAPIAdapter().ingest(spec)
        store.add_documents("spec", spec_chunks)

        status.update("[bold blue]Ingesting Java source code...")
        code_chunks = SourceCodeAdapter().ingest(source)
        store.add_documents("code", code_chunks)

        status.update("[bold blue]Ingesting existing tests...")
        test_adapter = ExistingTestsAdapter()
        test_chunks = test_adapter.ingest(tests, project=project, domain=domain)
        store.add_documents("test", test_chunks)

        status.update("[bold blue]Ingesting Karate syntax examples...")
        ref_chunks = ExistingTestsAdapter().ingest(karate_examples)
        store.add_documents("reference", ref_chunks)

        # Optional: Database schema ingestion
        db_conn = db or get_settings().db_connection_string
        if db_conn:
            status.update("[bold blue]Ingesting database schema...")
            from ingestion.db_schema_adapter import DatabaseSchemaAdapter
            settings = get_settings()
            table_filter = None
            if settings.db_table_filter:
                table_filter = [t.strip() for t in settings.db_table_filter.split(",")]
            adapter = DatabaseSchemaAdapter(
                connection_string=db_conn,
                schema=settings.db_schema,
                table_filter=table_filter,
            )
            try:
                schema_chunks = adapter.ingest()
                store.add_documents("schema", schema_chunks)
                console.print(f"[green]Ingested {len(schema_chunks)} table schemas.[/green]")
            except Exception as e:
                console.print(f"[yellow]⚠️  Schema ingestion failed: {e}[/yellow]")
            finally:
                adapter.close()

    console.print("[bold green]Full ingestion complete![/bold green]")
    stats()


@app.command("ingest-schema")
def ingest_schema(
    connection: str = typer.Option("", help="PostgreSQL connection string (overrides .env)"),
    schema: str = typer.Option("public", help="Database schema to introspect"),
    tables: str = typer.Option("", help="Comma-separated table filter (empty = all)"),
):
    """Ingest PostgreSQL database schema into the knowledge base."""
    settings = get_settings()
    conn_str = connection or settings.db_connection_string

    if not conn_str:
        console.print(
            "[bold red]Error: No database connection string provided.[/bold red]\n"
            "[dim]Set DB_CONNECTION_STRING in .env or pass --connection[/dim]"
        )
        raise typer.Exit(code=1)

    table_filter = None
    if tables:
        table_filter = [t.strip() for t in tables.split(",")]
    elif settings.db_table_filter:
        table_filter = [t.strip() for t in settings.db_table_filter.split(",")]

    from ingestion.db_schema_adapter import DatabaseSchemaAdapter

    console.print(f"\n[bold cyan]🗄️  Introspecting database schema '{schema}'[/bold cyan]\n")

    adapter = DatabaseSchemaAdapter(
        connection_string=conn_str,
        schema=schema,
        table_filter=table_filter,
    )

    try:
        with console.status("[bold blue]Connecting and introspecting...") as status:
            chunks = adapter.ingest()

        if not chunks:
            console.print("[yellow]No tables found matching the filter.[/yellow]")
            return

        store = VectorStore()
        store.add_documents("schema", chunks)

        console.print(f"[bold green]✅ Ingested {len(chunks)} table schemas:[/bold green]")
        for chunk in chunks:
            table_name = chunk.metadata.get("table_name", "unknown")
            col_count = chunk.metadata.get("column_count", 0)
            has_fk = "🔗" if chunk.metadata.get("has_foreign_keys") else ""
            console.print(f"  - {table_name} ({col_count} columns) {has_fk}")

    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        raise typer.Exit(code=1)
    finally:
        adapter.close()



@app.command()
def stats():
    """Show ChromaDB collection stats."""
    store = VectorStore()
    collection_stats = store.get_stats()

    table = Table(title="Knowledge Base Statistics")
    table.add_column("Origin Type", style="cyan", no_wrap=True)
    table.add_column("Document Count", style="magenta")

    for origin, count in collection_stats.items():
        table.add_row(origin, str(count))

    console.print(table)


@app.command()
def retrieve(query: str = typer.Argument(..., help="Endpoint tag or natural language query")):
    """Semantic search and display context package."""
    retriever = ContextRetriever()
    with console.status(f"[bold blue]Retrieving context for '{query}'...") as status:
        package = retriever.retrieve(query)

    if package.is_empty():
        console.print("[yellow]No relevant context found.[/yellow]")
        return

    console.print(f"\n[bold green]Context Package for: {package.endpoint_tag or query}[/bold green]\n")

    def print_section(title, chunks, color):
        if not chunks:
            return
        console.print(f"[bold {color}]-- {title} ({len(chunks)}) --[/bold {color}]")
        for i, chunk in enumerate(chunks):
            preview = chunk.content[:150] + "..." if len(chunk.content) > 150 else chunk.content
            preview = preview.replace("\n", " ")
            console.print(f"[{i+1}] {chunk.source_file} (tag: {chunk.endpoint_tag})")
            console.print(f"    [dim]{preview}[/dim]")
        console.print()

    print_section("API Specification", package.spec_context, "cyan")
    print_section("Source Code", package.code_context, "blue")
    print_section("Existing Tests", package.test_context, "magenta")
    print_section("Reference Examples", package.reference_context, "yellow")


# ──────────────────────────────────────────────
# LLM provider helpers
# ──────────────────────────────────────────────

def _check_llm_api_key(settings) -> bool:
    """Check if the API key is configured for the active LLM provider."""
    if settings.llm_provider == "openai":
        return bool(settings.openai_api_key)
    else:  # anthropic
        return bool(settings.anthropic_api_key)


# ──────────────────────────────────────────────
# Week 2: Generation commands
# ──────────────────────────────────────────────

@app.command()
def generate(
    endpoint: str = typer.Argument(..., help="Endpoint tag, e.g. 'POST /orders'"),
    project: str = typer.Option("", help="Target project for context filtering"),
):
    """Generate Karate test features for an endpoint using AI."""
    settings = get_settings()

    if not _check_llm_api_key(settings):
        console.print("[bold red]Error: API key not set for the configured LLM provider.[/bold red]")
        console.print(f"[dim]Provider: {settings.llm_provider}. Set the appropriate API key in .env[/dim]")
        raise typer.Exit(code=1)

    from agents.graph import compile_graph

    console.print(f"\n[bold cyan]🚀 Generating tests for: {endpoint}[/bold cyan]\n")

    graph = compile_graph()
    initial_state = {
        "endpoint_tag": endpoint,
        "target_project": project,
        "retry_count": 0,
        "reasoning_chain": [],
    }

    with console.status("[bold blue]Running AI agent pipeline...") as status:
        status.update("[bold blue]Step 1/3: Retrieving context...")
        start_time = time.time()
        result = graph.invoke(initial_state)
        gen_time = time.time() - start_time

    # Record Generation Metrics
    if result.get("scenarios") and result.get("feature_files"):
        categories = dict(Counter([s.get("category", "unknown") for s in result.get("scenarios", [])]))
        ks_used = len([s for s in result.get("scenarios", []) if len(s.get("knowledge_sources", [])) >= 2])
        
        collector = MetricsCollector()
        collector.record_generation(GenerationRun(
            timestamp=datetime.now().isoformat(),
            endpoint_tag=endpoint,
            scenarios_generated=len(result["scenarios"]),
            features_written=len(result["feature_files"]),
            syntactic_errors=0,
            generation_time_seconds=gen_time,
            categories=categories,
            knowledge_sources_used=ks_used
        ))

    # Display results
    _display_generation_results(result, settings)


@app.command()
def generate_auto(
    endpoint: str = typer.Argument(..., help="Endpoint tag, e.g. 'POST /orders'"),
    project: str = typer.Option("", help="Target project for context filtering"),
):
    """Generate and auto-approve Karate test features (non-interactive)."""
    settings = get_settings()

    if not _check_llm_api_key(settings):
        console.print("[bold red]Error: API key not set for the configured LLM provider.[/bold red]")
        console.print(f"[dim]Provider: {settings.llm_provider}. Set the appropriate API key in .env[/dim]")
        raise typer.Exit(code=1)

    from agents.graph import compile_graph

    console.print(f"\n[bold cyan]🚀 Generating tests for: {endpoint} (auto-approve)[/bold cyan]\n")

    graph = compile_graph()
    initial_state = {
        "endpoint_tag": endpoint,
        "target_project": project,
        "retry_count": 0,
        "reasoning_chain": [],
    }

    with console.status("[bold blue]Running AI agent pipeline..."):
        start_time = time.time()
        result = graph.invoke(initial_state)
        gen_time = time.time() - start_time

    feature_files = result.get("feature_files", [])
    if feature_files:
        _write_features_to_disk(feature_files, settings)
        console.print(f"[bold green]✅ Auto-approved and saved {len(feature_files)} feature files[/bold green]")
        
        # Record Generation Metrics
        if result.get("scenarios"):
            categories = dict(Counter([s.get("category", "unknown") for s in result.get("scenarios", [])]))
            ks_used = len([s for s in result.get("scenarios", []) if len(s.get("knowledge_sources", [])) >= 2])
            
            collector = MetricsCollector()
            collector.record_generation(GenerationRun(
                timestamp=datetime.now().isoformat(),
                endpoint_tag=endpoint,
                scenarios_generated=len(result["scenarios"]),
                features_written=len(feature_files),
                syntactic_errors=0,
                generation_time_seconds=gen_time,
                categories=categories,
                knowledge_sources_used=ks_used
            ))
    else:
        console.print("[yellow]No feature files were generated.[/yellow]")

    _display_reasoning_chain(result)


@app.command()
def approve(
    all_files: bool = typer.Option(False, "--all", help="Approve all pending generated features"),
    filename: Optional[str] = typer.Argument(None, help="Specific feature file to approve"),
):
    """Approve generated feature files and store them in the knowledge base."""
    settings = get_settings()
    gen_dir = settings.generated_features_dir

    if not os.path.isdir(gen_dir):
        console.print(f"[yellow]No generated features directory found at {gen_dir}[/yellow]")
        return

    feature_files = [f for f in os.listdir(gen_dir) if f.endswith(".feature")]

    if not feature_files:
        console.print("[yellow]No feature files found to approve.[/yellow]")
        return

    if filename:
        if filename not in feature_files:
            console.print(f"[red]File '{filename}' not found in {gen_dir}[/red]")
            return
        feature_files = [filename]
    elif not all_files:
        console.print("[yellow]Use --all to approve all, or specify a filename.[/yellow]")
        console.print(f"Available files: {', '.join(feature_files)}")
        return

    # Store approved files in RAG for future learning
    store = VectorStore()
    adapter = ExistingTestsAdapter()

    for fname in feature_files:
        fpath = os.path.join(gen_dir, fname)
        chunks = adapter.ingest(fpath, project=settings.karate_project_path)
        if chunks:
            store.add_documents("test", chunks)
            console.print(f"[green]✅ Approved: {fname} (added to knowledge base)[/green]")
        else:
            console.print(f"[yellow]⚠️  Approved: {fname} (no scenarios extracted for KB)[/yellow]")


@app.command()
def reject(
    filename: str = typer.Argument(..., help="Feature file to reject"),
    reason: str = typer.Option("", help="Reason for rejection"),
):
    """Reject and remove a generated feature file."""
    settings = get_settings()
    gen_dir = settings.generated_features_dir
    fpath = os.path.join(gen_dir, filename)

    if not os.path.isfile(fpath):
        console.print(f"[red]File '{filename}' not found in {gen_dir}[/red]")
        return

    os.remove(fpath)
    msg = f"[red]❌ Rejected: {filename}[/red]"
    if reason:
        msg += f" (reason: {reason})"
    console.print(msg)


# ──────────────────────────────────────────────
# Week 3: Execution and Analysis commands
# ──────────────────────────────────────────────

@app.command()
def execute(
    feature: Optional[str] = typer.Option(None, help="Specific feature file or path to execute"),
    env: str = typer.Option("dev", help="Karate environment (e.g. dev, staging)"),
):
    """Execute generated Karate tests and show results."""
    console.print(f"\n[bold cyan]🏃 Executing Karate Tests (env: {env})[/bold cyan]\n")
    
    with console.status("[bold blue]Running tests via Maven...") as status:
        start_time = time.time()
        result = run_tests(feature_path=feature, env=env)
        exec_time = time.time() - start_time
        
    report = result.report
    
    # Record Execution Metrics
    collector = MetricsCollector()
    collector.record_execution(ExecutionRun(
        timestamp=datetime.now().isoformat(),
        total_tests=report.total,
        passed=report.passed,
        failed=report.failed,
        failure_classifications={},  # Just execution, no analysis here
        self_corrections_attempted=0,
        self_corrections_succeeded=0,
        execution_time_seconds=exec_time
    ))
    
    # Display summary
    if result.exit_code == 0 and report.failed == 0:
        console.print(f"[bold green]✅ Execution Complete: All {report.total} tests passed![/bold green]")
    else:
        console.print(f"[bold red]❌ Execution Complete: {report.failed} failed out of {report.total} tests.[/bold red]")
        
    console.print(f"[dim]Duration: {report.duration_ms / 1000:.2f}s[/dim]\n")
    
    # Detailed results table
    if report.scenario_results:
        table = Table(title="Test Results")
        table.add_column("Feature", style="cyan")
        table.add_column("Scenario", style="magenta", max_width=40)
        table.add_column("Status", justify="center")
        table.add_column("Duration", justify="right", style="dim")
        
        for r in report.scenario_results:
            status_emoji = "[green]PASS[/green]" if r.passed else "[red]FAIL[/red]"
            dur_str = f"{r.duration_ms:.0f}ms"
            
            table.add_row(r.feature_file, r.scenario_name, status_emoji, dur_str)
            
            if not r.passed and r.failure_message:
                # Add a row for the error message
                error_msg = r.failure_message.split('\\n')[0][:100] + "..." if len(r.failure_message) > 100 else r.failure_message
                table.add_row("", f"[dim red]└─ Error: {error_msg}[/dim red]", "", "")
                
        console.print(table)
        console.print("\n[dim]See target/karate-reports/karate-summary.html for full details.[/dim]")


@app.command("run-full")
def run_full(
    endpoint: str = typer.Argument(..., help="Endpoint tag, e.g. 'POST /orders'"),
    project: str = typer.Option("", help="Target project for context filtering"),
    env: str = typer.Option("dev", help="Karate environment for execution"),
):
    """Run the full agent loop: retrieve, generate, write, execute, analyze, and self-correct."""
    settings = get_settings()

    if not _check_llm_api_key(settings):
        console.print("[bold red]Error: API key not set for the configured LLM provider.[/bold red]")
        console.print(f"[dim]Provider: {settings.llm_provider}. Set the appropriate API key in .env[/dim]")
        raise typer.Exit(code=1)

    from agents.graph import compile_graph
    
    console.print(f"\n[bold cyan]🚀 Starting Full Agent Loop for: {endpoint}[/bold cyan]\n")
    
    graph = compile_graph()
    initial_state = {
        "endpoint_tag": endpoint,
        "target_project": project,
        "retry_count": 0,
        "reasoning_chain": [],
    }

    # Temporarily set env for the execution node
    os.environ["KARATE_ENV"] = env
    
    # Since the graph might run multiple times in a loop, we just use a generic spinner
    with console.status("[bold blue]Agent is working... (this may take a few minutes)") as status:
        start_time = time.time()
        result = graph.invoke(initial_state)
        total_time = time.time() - start_time

    # Clean up temp env
    if "KARATE_ENV" in os.environ:
        del os.environ["KARATE_ENV"]

    # Record Generation Metrics
    if result.get("scenarios") and result.get("feature_files"):
        categories = dict(Counter([s.get("category", "unknown") for s in result.get("scenarios", [])]))
        ks_used = len([s for s in result.get("scenarios", []) if len(s.get("knowledge_sources", [])) >= 2])
        
        collector = MetricsCollector()
        collector.record_generation(GenerationRun(
            timestamp=datetime.now().isoformat(),
            endpoint_tag=endpoint,
            scenarios_generated=len(result["scenarios"]),
            features_written=len(result["feature_files"]),
            syntactic_errors=0,
            generation_time_seconds=total_time,
            categories=categories,
            knowledge_sources_used=ks_used
        ))

    # Show generated features
    _display_generation_results(result, settings)
    
    # Show execution results
    execution_results = result.get("execution_results", [])
    if execution_results:
        console.print("\n[bold cyan]📊 Final Execution Results[/bold cyan]")
        passed = sum(1 for r in execution_results if r.get("passed"))
        failed = len(execution_results) - passed
        
        if failed == 0:
            console.print(f"[bold green]✅ All {passed} generated tests passed on the final run![/bold green]")
        else:
            console.print(f"[bold red]❌ {failed} tests failed on the final run ({passed} passed).[/bold red]")
            
        analysis = result.get("analysis", {})
        counts = {}
        if analysis and analysis.get("analyses"):
            console.print("\n[bold yellow]🔍 Failure Analysis Breakdown[/bold yellow]")
            
            counts = dict(Counter(a.get("classification") for a in analysis.get("analyses", [])))
            for classification, count in counts.items():
                console.print(f"  - {classification}: {count}")

        # Record Execution Metrics
        collector.record_execution(ExecutionRun(
            timestamp=datetime.now().isoformat(),
            total_tests=passed + failed,
            passed=passed,
            failed=failed,
            failure_classifications=counts,
            self_corrections_attempted=result.get("retry_count", 0),
            self_corrections_succeeded=1 if result.get("retry_count", 0) > 0 and failed == 0 else 0,
            execution_time_seconds=total_time
        ))


@app.command()
def metrics():
    """Display generation and execution metrics."""
    console.print("\n[bold cyan]📈 Karate AI Agent Metrics[/bold cyan]")
    console.print("[dim]Note: Full persistent metrics storage is planned for Phase 2.[/dim]")
    
    settings = get_settings()
    gen_dir = settings.generated_features_dir
    
    features = []
    if os.path.isdir(gen_dir):
        features = [f for f in os.listdir(gen_dir) if f.endswith(".feature")]
        
    store = VectorStore()
    stats = store.get_stats()
    approved_tests = stats.get("test", 0)
    
    table = Table(title="Current Workspace Stats")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta", justify="right")
    
    table.add_row("Generated Features", str(len(features)))
    table.add_row("Approved Scenarios in KB", str(approved_tests))
    table.add_row("API Spec Endpoints in KB", str(stats.get("spec", 0)))
    table.add_row("Code Methods in KB", str(stats.get("code", 0)))
    
    console.print(table)

    # Historical trends from Collector
    collector = MetricsCollector()
    records = collector.get_all_records()
    gen_records = [r for r in records if r["type"] == "generation"]
    exec_records = [r for r in records if r["type"] == "execution"]
    
    if gen_records or exec_records:
        console.print("\n[bold cyan]📊 Historical Trends[/bold cyan]")
        trend_table = Table(title="Pipeline Effectiveness")
        trend_table.add_column("Metric", style="cyan")
        trend_table.add_column("Value", style="magenta", justify="right")
        
        if gen_records:
            avg_gen_time = sum(r["generation_time_seconds"] for r in gen_records) / len(gen_records)
            trend_table.add_row("Total Generation Runs", str(len(gen_records)))
            trend_table.add_row("Avg Generation Time", f"{avg_gen_time:.1f}s")
            
            total_scenarios = sum(r["scenarios_generated"] for r in gen_records)
            if total_scenarios > 0:
                ks_used = sum(r.get("knowledge_sources_used", 0) for r in gen_records)
                trend_table.add_row("Knowledge Source Utilization (>2)", f"{(ks_used/total_scenarios)*100:.1f}%")
                
        if exec_records:
            total_execs = len(exec_records)
            total_tests = sum(r["total_tests"] for r in exec_records)
            total_passed = sum(r["passed"] for r in exec_records)
            
            trend_table.add_row("Total Execution Runs", str(total_execs))
            if total_tests > 0:
                trend_table.add_row("Overall Pass Rate", f"{(total_passed/total_tests)*100:.1f}%")
                
            total_corrections = sum(r.get("self_corrections_attempted", 0) for r in exec_records)
            successful_corrections = sum(r.get("self_corrections_succeeded", 0) for r in exec_records)
            if total_corrections > 0:
                trend_table.add_row("Self-Correction Rate", f"{(successful_corrections/total_corrections)*100:.1f}%")
                
        console.print(trend_table)


# ──────────────────────────────────────────────
# Display helpers
# ──────────────────────────────────────────────

def _display_generation_results(result: dict, settings):
    """Display generated scenarios and features with Rich formatting."""
    scenarios = result.get("scenarios", [])
    feature_files = result.get("feature_files", [])
    error = result.get("error")

    if error:
        console.print(f"\n[bold red]Error: {error}[/bold red]")
        return

    # Scenarios table
    if scenarios:
        table = Table(title="Generated Test Scenarios")
        table.add_column("#", style="dim", width=3)
        table.add_column("Scenario", style="cyan", max_width=40)
        table.add_column("Category", style="magenta")
        table.add_column("Confidence", style="green")
        table.add_column("Sources", style="dim", max_width=30)

        for i, s in enumerate(scenarios):
            sources = ", ".join(s.get("knowledge_sources", [])[:2])
            if len(s.get("knowledge_sources", [])) > 2:
                sources += "..."
            table.add_row(
                str(i + 1),
                s["name"],
                s["category"],
                s["confidence"],
                sources,
            )
        console.print(table)
        console.print()

    # Feature files
    if feature_files:
        console.print(f"[bold green]Generated {len(feature_files)} feature files:[/bold green]\n")
        for feat in feature_files:
            console.print(Panel(
                Syntax(feat["content"], "gherkin", theme="monokai", line_numbers=True),
                title=f"📄 {feat['filename']}",
                subtitle=f"Scenario: {feat['scenario_name']}",
                border_style="cyan",
            ))

            if feat.get("companion_data_files"):
                for df in feat["companion_data_files"]:
                    console.print(Panel(
                        df["content"],
                        title=f"📊 {df['filename']}",
                        border_style="yellow",
                    ))
            console.print()

        # Write to disk
        _write_features_to_disk(feature_files, settings)
        console.print(
            f"\n[bold green]Files written to: {settings.generated_features_dir}/[/bold green]"
        )
        console.print(
            "[dim]Review in your IDE, then run: "
            "[bold]python3 -m cli.app approve --all[/bold] "
            "to add to knowledge base[/dim]"
        )
    else:
        console.print("[yellow]No feature files were generated.[/yellow]")

    # Reasoning chain
    _display_reasoning_chain(result)


def _display_reasoning_chain(result: dict):
    """Display the agent's reasoning chain."""
    chain = result.get("reasoning_chain", [])
    if chain:
        console.print("\n[bold]🧠 Reasoning Chain:[/bold]")
        for step in chain:
            console.print(f"  → {step}")
        console.print()


def _write_features_to_disk(feature_files: list, settings):
    """Write generated feature files (and companion data files) to disk."""
    gen_dir = settings.generated_features_dir
    os.makedirs(gen_dir, exist_ok=True)

    testdata_dir = os.path.join(gen_dir, "testdata")

    for feat in feature_files:
        # Write .feature file
        fpath = os.path.join(gen_dir, feat["filename"])
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(feat["content"])

        # Write companion data files
        for df in feat.get("companion_data_files", []):
            os.makedirs(testdata_dir, exist_ok=True)
            df_path = os.path.join(testdata_dir, df["filename"])
            with open(df_path, "w", encoding="utf-8") as f:
                f.write(df["content"])


if __name__ == "__main__":
    app()
