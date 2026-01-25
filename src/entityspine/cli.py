"""
EntitySpine CLI - Command Line Interface

A powerful CLI for entity resolution, knowledge graph exploration,
and SEC filing analysis.

Usage:
    entityspine resolve AAPL
    entityspine search "Apple"
    entityspine graph network AAPL --depth 2
    entityspine filings list 0000320193
    entityspine serve --port 8000

Installation:
    pip install entityspine[cli]  # Includes typer and rich
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Annotated, Optional

# Check for CLI dependencies
try:
    import typer
    from rich import print as rprint
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.tree import Tree

    HAS_CLI_DEPS = True
except ImportError:
    HAS_CLI_DEPS = False


def check_cli_deps():
    """Check if CLI dependencies are installed."""
    if not HAS_CLI_DEPS:
        print("CLI dependencies not installed. Run: pip install entityspine[cli]")
        sys.exit(1)


# =============================================================================
# CLI App Setup
# =============================================================================

if HAS_CLI_DEPS:
    app = typer.Typer(
        name="entityspine",
        help="EntitySpine - Entity Resolution & Knowledge Graph CLI",
        no_args_is_help=True,
        rich_markup_mode="rich",
    )
    console = Console()

    # Sub-apps
    resolve_app = typer.Typer(help="Entity resolution commands")
    graph_app = typer.Typer(help="Knowledge graph commands")
    filings_app = typer.Typer(help="SEC filings commands")
    db_app = typer.Typer(help="Database management commands")

    app.add_typer(graph_app, name="graph")
    app.add_typer(filings_app, name="filings")
    app.add_typer(db_app, name="db")


# =============================================================================
# Helper Functions
# =============================================================================


def get_resolver(db_path: str | None = None, tier: int = 1):
    """Get configured EntityResolver instance."""
    from entityspine.domain.enums import ResolutionTier
    from entityspine.services.resolver import EntityResolver, ResolverConfig

    tier_enum = ResolutionTier(tier)
    config = ResolverConfig(
        db_path=db_path,
        tier=tier_enum,
        auto_load_sec=True,
    )
    return EntityResolver(config=config)


def format_entity_table(entity, result=None) -> Table:
    """Format entity as a rich table."""
    table = Table(title=f"Entity: {entity.primary_name}", show_header=False)
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Entity ID", entity.entity_id)
    table.add_row("Primary Name", entity.primary_name)
    table.add_row("Type", entity.entity_type.value if hasattr(entity.entity_type, 'value') else str(entity.entity_type))
    table.add_row("Status", entity.status.value if hasattr(entity.status, 'value') else str(entity.status))
    
    if entity.jurisdiction:
        table.add_row("Jurisdiction", entity.jurisdiction)
    if entity.sic_code:
        table.add_row("SIC Code", entity.sic_code)
    if entity.source_system:
        table.add_row("Source", entity.source_system)
    if entity.source_id:
        table.add_row("Source ID (CIK)", entity.source_id)
    if entity.aliases:
        table.add_row("Aliases", ", ".join(entity.aliases[:5]))

    if result:
        table.add_row("─" * 20, "─" * 40)
        table.add_row("Confidence", f"{result.confidence:.2%}")
        table.add_row("Match Reason", str(result.match_reason.value) if result.match_reason else "N/A")
        table.add_row("Tier", str(result.tier.value) if result.tier else "N/A")

    return table


def format_json_output(data: dict) -> str:
    """Format data as JSON."""
    return json.dumps(data, indent=2, default=str)


# =============================================================================
# Resolve Commands
# =============================================================================

if HAS_CLI_DEPS:
    @app.command("resolve")
    def resolve_identifier(
        query: Annotated[str, typer.Argument(help="Identifier to resolve (ticker, CIK, name, ISIN, etc.)")],
        as_of: Annotated[Optional[str], typer.Option("--as-of", help="Point-in-time date (YYYY-MM-DD)")] = None,
        mic: Annotated[Optional[str], typer.Option("--mic", help="Market Identifier Code for ticker disambiguation")] = None,
        db_path: Annotated[Optional[str], typer.Option("--db", help="Database path")] = None,
        tier: Annotated[int, typer.Option("--tier", help="Resolution tier (0-3)")] = 1,
        output: Annotated[str, typer.Option("--output", "-o", help="Output format: table, json")] = "table",
    ):
        """
        Resolve any identifier to an entity.
        
        Supports: tickers (AAPL), CIKs (0000320193), names ("Apple Inc"),
        ISINs (US0378331005), CUSIPs (037833100), LEIs
        
        Examples:
            entityspine resolve AAPL
            entityspine resolve 0000320193
            entityspine resolve "Apple Inc" --as-of 2020-01-01
        """
        resolver = get_resolver(db_path, tier)
        
        as_of_date = None
        if as_of:
            as_of_date = date.fromisoformat(as_of)
        
        with console.status(f"Resolving '{query}'..."):
            result = resolver.resolve(query, as_of=as_of_date, mic=mic)
        
        if result.status.value == "found" and result.entity:
            if output == "json":
                data = {
                    "status": result.status.value,
                    "entity_id": result.entity.entity_id,
                    "primary_name": result.entity.primary_name,
                    "type": result.entity.entity_type.value,
                    "source_id": result.entity.source_id,
                    "confidence": result.confidence,
                    "match_reason": result.match_reason.value if result.match_reason else None,
                    "tier": result.tier.value if result.tier else None,
                }
                rprint(format_json_output(data))
            else:
                table = format_entity_table(result.entity, result)
                console.print(table)
        else:
            if output == "json":
                rprint(format_json_output({"status": "not_found", "query": query}))
            else:
                console.print(f"[red]Not found:[/red] No entity matches '{query}'")
                if result.warnings:
                    for warning in result.warnings:
                        console.print(f"  [yellow]Warning:[/yellow] {warning}")


    @app.command("search")
    def search_entities(
        query: Annotated[str, typer.Argument(help="Search query")],
        limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results")] = 10,
        entity_type: Annotated[Optional[str], typer.Option("--type", "-t", help="Filter by entity type")] = None,
        db_path: Annotated[Optional[str], typer.Option("--db", help="Database path")] = None,
        tier: Annotated[int, typer.Option("--tier", help="Resolution tier")] = 1,
        output: Annotated[str, typer.Option("--output", "-o", help="Output format")] = "table",
    ):
        """
        Search for entities by name.
        
        Examples:
            entityspine search "technology"
            entityspine search "Apple" --limit 5
            entityspine search "bank" --type organization
        """
        resolver = get_resolver(db_path, tier)
        
        with console.status(f"Searching for '{query}'..."):
            results = resolver.search(query, limit=limit)
        
        if not results:
            console.print(f"[yellow]No results found for '{query}'[/yellow]")
            return
        
        if output == "json":
            data = [
                {
                    "entity_id": r.entity.entity_id,
                    "primary_name": r.entity.primary_name,
                    "type": r.entity.entity_type.value,
                    "source_id": r.entity.source_id,
                    "confidence": r.confidence,
                }
                for r in results
            ]
            rprint(format_json_output(data))
        else:
            table = Table(title=f"Search Results: '{query}'")
            table.add_column("Name", style="cyan")
            table.add_column("Type")
            table.add_column("CIK/Source ID")
            table.add_column("Score", justify="right")
            
            for r in results:
                table.add_row(
                    r.entity.primary_name,
                    r.entity.entity_type.value,
                    r.entity.source_id or "N/A",
                    f"{r.confidence:.2%}",
                )
            
            console.print(table)
            console.print(f"\n[dim]Found {len(results)} results[/dim]")


    @app.command("batch")
    def batch_resolve(
        identifiers: Annotated[list[str], typer.Argument(help="Identifiers to resolve")],
        db_path: Annotated[Optional[str], typer.Option("--db", help="Database path")] = None,
        tier: Annotated[int, typer.Option("--tier", help="Resolution tier")] = 1,
        output: Annotated[str, typer.Option("--output", "-o", help="Output format")] = "table",
    ):
        """
        Resolve multiple identifiers in batch.
        
        Examples:
            entityspine batch AAPL MSFT GOOGL
            entityspine batch 0000320193 0000789019 --output json
        """
        resolver = get_resolver(db_path, tier)
        
        with console.status(f"Resolving {len(identifiers)} identifiers..."):
            results = [resolver.resolve(q) for q in identifiers]
        
        if output == "json":
            data = [
                {
                    "query": identifiers[i],
                    "status": r.status.value,
                    "entity_id": r.entity.entity_id if r.entity else None,
                    "primary_name": r.entity.primary_name if r.entity else None,
                    "confidence": r.confidence,
                }
                for i, r in enumerate(results)
            ]
            rprint(format_json_output(data))
        else:
            table = Table(title="Batch Resolution Results")
            table.add_column("Query", style="cyan")
            table.add_column("Status")
            table.add_column("Name")
            table.add_column("CIK")
            table.add_column("Score", justify="right")
            
            for i, r in enumerate(results):
                status_style = "green" if r.status.value == "found" else "red"
                table.add_row(
                    identifiers[i],
                    f"[{status_style}]{r.status.value}[/{status_style}]",
                    r.entity.primary_name if r.entity else "N/A",
                    r.entity.source_id if r.entity else "N/A",
                    f"{r.confidence:.2%}",
                )
            
            console.print(table)


# =============================================================================
# Graph Commands
# =============================================================================

if HAS_CLI_DEPS:
    @graph_app.command("network")
    def graph_network(
        entity: Annotated[str, typer.Argument(help="Entity identifier (ticker, CIK, or ID)")],
        depth: Annotated[int, typer.Option("--depth", "-d", help="Traversal depth")] = 2,
        db_path: Annotated[Optional[str], typer.Option("--db", help="Database path")] = None,
        tier: Annotated[int, typer.Option("--tier", help="Resolution tier")] = 2,
        output: Annotated[str, typer.Option("--output", "-o", help="Output format")] = "tree",
    ):
        """
        Get entity network/relationships.
        
        Examples:
            entityspine graph network AAPL
            entityspine graph network 0000320193 --depth 3
        """
        if tier < 2:
            console.print("[yellow]Warning: Graph features work best with Tier 2+[/yellow]")
        
        resolver = get_resolver(db_path, tier)
        
        # First resolve the entity
        result = resolver.resolve(entity)
        if not result.entity:
            console.print(f"[red]Entity not found: {entity}[/red]")
            return
        
        # Try to get graph service
        try:
            from entityspine.services.graph_service import GraphService
            graph = GraphService(resolver.store)
            network = graph.get_entity_network(result.entity.entity_id, max_depth=depth)
            
            if output == "json":
                data = {
                    "center": result.entity.primary_name,
                    "nodes": len(network.nodes),
                    "edges": len(network.edges),
                    "entities": [
                        {"id": eid, "name": e.primary_name, "depth": network.depth_map.get(eid, 0)}
                        for eid, e in network.nodes.items()
                    ],
                }
                rprint(format_json_output(data))
            else:
                tree = Tree(f"[bold cyan]{result.entity.primary_name}[/bold cyan]")
                
                for d in range(1, depth + 1):
                    entities_at_depth = network.entities_at_depth(d)
                    if entities_at_depth:
                        depth_branch = tree.add(f"[dim]Depth {d}[/dim]")
                        for e in entities_at_depth[:10]:  # Limit display
                            depth_branch.add(f"{e.primary_name}")
                        if len(entities_at_depth) > 10:
                            depth_branch.add(f"[dim]... and {len(entities_at_depth) - 10} more[/dim]")
                
                console.print(Panel(tree, title="Entity Network"))
                console.print(f"\nTotal: {network.node_count} nodes, {network.edge_count} edges")
                
        except ImportError:
            console.print("[yellow]Graph service requires Tier 2+ features[/yellow]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


    @graph_app.command("subsidiaries")
    def graph_subsidiaries(
        entity: Annotated[str, typer.Argument(help="Parent entity identifier")],
        db_path: Annotated[Optional[str], typer.Option("--db", help="Database path")] = None,
        tier: Annotated[int, typer.Option("--tier", help="Resolution tier")] = 2,
        output: Annotated[str, typer.Option("--output", "-o", help="Output format")] = "tree",
    ):
        """
        Get entity subsidiaries.
        
        Examples:
            entityspine graph subsidiaries AAPL
        """
        resolver = get_resolver(db_path, tier)
        result = resolver.resolve(entity)
        
        if not result.entity:
            console.print(f"[red]Entity not found: {entity}[/red]")
            return
        
        try:
            from entityspine.services.graph_service import GraphService
            graph = GraphService(resolver.store)
            subsidiaries = graph.get_subsidiaries(result.entity.entity_id)
            
            if output == "json":
                data = [{"name": s.entity.primary_name, "type": str(s.relationship_type)} for s in subsidiaries]
                rprint(format_json_output(data))
            else:
                tree = Tree(f"[bold cyan]{result.entity.primary_name}[/bold cyan]")
                for sub in subsidiaries:
                    tree.add(f"{sub.entity.primary_name}")
                console.print(Panel(tree, title="Subsidiaries"))
                
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


    @graph_app.command("officers")
    def graph_officers(
        entity: Annotated[str, typer.Argument(help="Company identifier")],
        current_only: Annotated[bool, typer.Option("--current", help="Only current officers")] = True,
        db_path: Annotated[Optional[str], typer.Option("--db", help="Database path")] = None,
        tier: Annotated[int, typer.Option("--tier", help="Resolution tier")] = 2,
        output: Annotated[str, typer.Option("--output", "-o", help="Output format")] = "table",
    ):
        """
        Get company officers and directors.
        
        Examples:
            entityspine graph officers AAPL
            entityspine graph officers MSFT --current
        """
        resolver = get_resolver(db_path, tier)
        result = resolver.resolve(entity)
        
        if not result.entity:
            console.print(f"[red]Entity not found: {entity}[/red]")
            return
        
        try:
            from entityspine.services.graph_service import GraphService
            graph = GraphService(resolver.store)
            officers = graph.get_officers(result.entity.entity_id, current_only=current_only)
            
            if not officers:
                console.print("[yellow]No officers found (data may not be loaded)[/yellow]")
                return
            
            if output == "json":
                data = [
                    {
                        "name": o.person.primary_name,
                        "title": o.title,
                        "role_type": o.role_type.value,
                        "current": o.is_current,
                    }
                    for o in officers
                ]
                rprint(format_json_output(data))
            else:
                table = Table(title=f"Officers: {result.entity.primary_name}")
                table.add_column("Name", style="cyan")
                table.add_column("Title")
                table.add_column("Role")
                table.add_column("Current")
                
                for o in officers:
                    table.add_row(
                        o.person.primary_name,
                        o.title or "N/A",
                        o.role_type.value,
                        "✓" if o.is_current else "✗",
                    )
                
                console.print(table)
                
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


# =============================================================================
# Filings Commands
# =============================================================================

if HAS_CLI_DEPS:
    @filings_app.command("list")
    def filings_list(
        cik: Annotated[str, typer.Argument(help="Company CIK")],
        form_type: Annotated[Optional[str], typer.Option("--form", "-f", help="Filter by form type (10-K, 10-Q, 8-K)")] = None,
        limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results")] = 10,
        output: Annotated[str, typer.Option("--output", "-o", help="Output format")] = "table",
    ):
        """
        List SEC filings for a company.
        
        Examples:
            entityspine filings list 0000320193
            entityspine filings list 0000320193 --form 10-K
        """
        console.print(f"[yellow]Filing listing requires database with filing data loaded[/yellow]")
        console.print(f"Searching for CIK: {cik}, Form: {form_type or 'all'}")


    @filings_app.command("parse")
    def filings_parse(
        accession: Annotated[str, typer.Argument(help="Filing accession number")],
        sections: Annotated[bool, typer.Option("--sections", help="Extract sections")] = False,
        exhibits: Annotated[bool, typer.Option("--exhibits", help="Extract exhibits")] = False,
        output: Annotated[str, typer.Option("--output", "-o", help="Output format")] = "summary",
    ):
        """
        Parse and analyze an SEC filing.
        
        Examples:
            entityspine filings parse 0000320193-24-000081
            entityspine filings parse 0000320193-24-000081 --sections
        """
        console.print(f"[yellow]Filing parsing requires py-sec-edgar integration[/yellow]")
        console.print(f"Would parse: {accession}")


# =============================================================================
# Database Commands
# =============================================================================

if HAS_CLI_DEPS:
    @db_app.command("init")
    def db_init(
        path: Annotated[str, typer.Argument(help="Database path")] = "entityspine.db",
        tier: Annotated[int, typer.Option("--tier", help="Database tier (1=SQLite, 2=DuckDB, 3=PostgreSQL)")] = 1,
    ):
        """
        Initialize a new EntitySpine database.
        
        Examples:
            entityspine db init
            entityspine db init --tier 2 entities.duckdb
        """
        with console.status(f"Initializing Tier {tier} database at {path}..."):
            resolver = get_resolver(path, tier)
            # Force initialization
            resolver._ensure_initialized()
        
        console.print(f"[green]✓[/green] Database initialized: {path}")


    @db_app.command("load-sec")
    def db_load_sec(
        path: Annotated[str, typer.Argument(help="Database path")] = "entityspine.db",
    ):
        """
        Load SEC company_tickers.json data.
        
        Examples:
            entityspine db load-sec
        """
        with console.status("Loading SEC company tickers..."):
            resolver = get_resolver(path, tier=1)
            resolver._ensure_initialized()
            
            # Check if data loaded
            count = 0
            if hasattr(resolver.store, 'count_entities'):
                count = resolver.store.count_entities()
        
        console.print(f"[green]✓[/green] Loaded {count:,} entities from SEC data")


    @db_app.command("stats")
    def db_stats(
        path: Annotated[str, typer.Argument(help="Database path")] = "entityspine.db",
    ):
        """
        Show database statistics.
        
        Examples:
            entityspine db stats
        """
        resolver = get_resolver(path, tier=1)
        resolver._ensure_initialized()
        
        table = Table(title="Database Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right")
        
        count = 0
        if hasattr(resolver.store, 'count_entities'):
            count = resolver.store.count_entities()
        
        table.add_row("Entities", f"{count:,}")
        table.add_row("Database Path", str(path))
        table.add_row("Tier", str(resolver.config.tier.value))
        
        console.print(table)


# =============================================================================
# Server Command
# =============================================================================

if HAS_CLI_DEPS:
    @app.command("serve")
    def serve(
        host: Annotated[str, typer.Option("--host", "-h", help="Host to bind")] = "127.0.0.1",
        port: Annotated[int, typer.Option("--port", "-p", help="Port to bind")] = 8000,
        db_path: Annotated[Optional[str], typer.Option("--db", help="Database path")] = None,
        tier: Annotated[int, typer.Option("--tier", help="Resolution tier")] = 1,
        reload: Annotated[bool, typer.Option("--reload", help="Enable auto-reload")] = False,
    ):
        """
        Start the EntitySpine API server.
        
        Examples:
            entityspine serve
            entityspine serve --port 8080 --tier 2
        """
        try:
            import uvicorn
        except ImportError:
            console.print("[red]uvicorn not installed. Run: pip install entityspine[api][/red]")
            raise typer.Exit(1)
        
        console.print(f"[cyan]Starting EntitySpine API server...[/cyan]")
        console.print(f"  Host: {host}")
        console.print(f"  Port: {port}")
        console.print(f"  Tier: {tier}")
        console.print(f"  Docs: http://{host}:{port}/docs")
        console.print()
        
        uvicorn.run(
            "entityspine.api.app:app",
            host=host,
            port=port,
            reload=reload,
        )


    @app.command("version")
    def version():
        """Show EntitySpine version."""
        try:
            from entityspine import __version__
            console.print(f"EntitySpine version: [cyan]{__version__}[/cyan]")
        except ImportError:
            console.print("EntitySpine version: [cyan]0.3.3[/cyan]")


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """Main entry point for CLI."""
    check_cli_deps()
    app()


if __name__ == "__main__":
    main()
