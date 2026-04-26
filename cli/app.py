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

    console.print("[bold green]Full ingestion complete![/bold green]")
    stats()


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
# Week 2: Generation commands
# ──────────────────────────────────────────────

@app.command()
def generate(
    endpoint: str = typer.Argument(..., help="Endpoint tag, e.g. 'POST /orders'"),
    project: str = typer.Option("", help="Target project for context filtering"),
):
    """Generate Karate test features for an endpoint using AI."""
    settings = get_settings()

    if not settings.anthropic_api_key:
        console.print("[bold red]Error: ANTHROPIC_API_KEY is not set in .env[/bold red]")
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
        result = graph.invoke(initial_state)

    # Display results
    _display_generation_results(result, settings)


@app.command()
def generate_auto(
    endpoint: str = typer.Argument(..., help="Endpoint tag, e.g. 'POST /orders'"),
    project: str = typer.Option("", help="Target project for context filtering"),
):
    """Generate and auto-approve Karate test features (non-interactive)."""
    settings = get_settings()

    if not settings.anthropic_api_key:
        console.print("[bold red]Error: ANTHROPIC_API_KEY is not set in .env[/bold red]")
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
        result = graph.invoke(initial_state)

    feature_files = result.get("feature_files", [])
    if feature_files:
        _write_features_to_disk(feature_files, settings)
        console.print(f"[bold green]✅ Auto-approved and saved {len(feature_files)} feature files[/bold green]")
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
