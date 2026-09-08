import argparse
from time import perf_counter

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from langgraph_okf.agent.context import Context
from langgraph_okf.agent.graph import build_legal_discovery_graph
from langgraph_okf.agent.reasoning import summarize_usage
from langgraph_okf.agent.state import LegalDiscoveryState, ModelUsage
from langgraph_okf.bundle import OKFBundle
from langgraph_okf.settings import settings

console = Console()


def print_run_metrics(usage: ModelUsage, elapsed_seconds: float, calls: list[ModelUsage] | None = None) -> None:
    table = Table(title="Run Metrics", show_header=False)
    table.add_row("Total elapsed", f"{elapsed_seconds:.2f}s")
    table.add_row("Model", usage["model"])
    table.add_row("LLM status", usage["status"])
    table.add_row("LLM elapsed", f"{usage['elapsed_seconds']:.2f}s")
    for key, label in (("input_tokens", "Input tokens"), ("output_tokens", "Output tokens"), ("total_tokens", "Total tokens")):
        value = usage[key]
        table.add_row(label, f"{value:,}" if value is not None else "Unavailable")
    cost = usage["cost_usd"]
    table.add_row("Cost (USD)", f"${cost:.8f}" if cost is not None else "Unavailable (not reported)")
    console.print(table)
    if calls:
        detail = Table(title="LLM Calls")
        for label in ("Phase", "Model", "Status", "Time", "Input", "Output", "Total", "Cost (USD)"):
            detail.add_column(label)
        for call in calls:
            detail.add_row(call.get("phase", "unknown"), call["model"], call["status"], f"{call['elapsed_seconds']:.2f}s",
                           *(str(call[key]) if call[key] is not None else "Unavailable" for key in ("input_tokens", "output_tokens", "total_tokens")),
                           f"${call['cost_usd']:.8f}" if call["cost_usd"] is not None else "Unavailable")
        console.print(detail)


def cmd_query(query_text: str) -> None:
    """
    Execute a legal query through the OKF LangGraph consumer agent.
    """
    console.print(Panel(f"[bold cyan]Legal Inquiry:[/bold cyan] {query_text}", title="LangGraph OKF Consumer"))

    started = perf_counter()
    graph = build_legal_discovery_graph()
    context = Context.from_settings(settings)
    state: LegalDiscoveryState = {"query": query_text}

    with console.status("[bold green]Traversing OKF Knowledge Graph via Progressive Disclosure...[/bold green]"):
        result = graph.invoke(state, context=context, config=context.invocation_config)
    elapsed_seconds = perf_counter() - started

    traversal_log = result.get("traversal_log", [])
    inspected = result.get("inspected_concepts", {})
    computations = result.get("computation_results", [])
    advisories = result.get("trust_advisories", [])
    final_response = result.get("final_response", "")

    # Display Traversal Steps
    table = Table(title="OKF Progressive Disclosure & Traversal Audit Trail", show_header=True, header_style="bold magenta")
    table.add_column("Step", style="dim", width=6)
    table.add_column("Action & Provenance")
    for idx, step in enumerate(traversal_log, 1):
        table.add_row(str(idx), step)
    console.print(table)
    console.print()

    # Display Inspected Concepts with Trust Tiers
    c_table = Table(title="Inspected Concepts & Trust Verification", show_header=True, header_style="bold blue")
    c_table.add_column("Concept ID", style="cyan")
    c_table.add_column("Type", style="green")
    c_table.add_column("Trust Tier", style="yellow")
    c_table.add_column("Status", style="magenta")
    c_table.add_column("Outbound Links", style="dim")

    for cid, detail in inspected.items():
        links_str = ", ".join(link["target"] for link in detail.get("links", []))
        c_table.add_row(
            cid,
            detail.get("type", "Concept"),
            detail.get("trust_tier", "unverified"),
            detail.get("status", "stable"),
            links_str[:40] + ("..." if len(links_str) > 40 else ""),
        )
    console.print(c_table)
    console.print()

    # Display Attested Computations if any
    if computations:
        comp_table = Table(title="Local Calculation Results (attestation not verified)", show_header=True, header_style="bold green")
        comp_table.add_column("Computation", style="cyan")
        comp_table.add_column("Result", style="white")
        for comp in computations:
            cid = comp.get("computation_id", "attested_computation")
            expl = comp.get("explanation", str(comp))
            comp_table.add_row(cid, expl)
        console.print(comp_table)
        console.print()

    # Display Trust Advisories if any
    if advisories:
        adv_panel = Panel(
            "\n".join(f"• {a}" for a in dict.fromkeys(advisories)),
            title="[bold yellow]⚠️ Trust Advisories & Lifecycle Warnings[/bold yellow]",
            border_style="yellow",
        )
        console.print(adv_panel)
        console.print()

    # Final Legal Opinion
    console.print(Panel(Markdown(final_response), title="[bold green]Grounded Evidence & Synthesis[/bold green]", border_style="green"))
    print_run_metrics(summarize_usage(result.get("model_calls", [])), elapsed_seconds, result.get("model_calls"))


def cmd_inspect(concept_id: str) -> None:
    """
    Inspect a specific concept document in the OKF bundle.
    """
    bundle = OKFBundle(settings.bundle_path)
    concept = bundle.get_concept(concept_id)

    meta_table = Table(title=f"Concept: {concept.title} (`{concept.concept_id}`)", show_header=False)
    meta_table.add_row("Type", f"[green]{concept.type}[/green]")
    meta_table.add_row("Description", concept.description)
    meta_table.add_row("Trust Tier", f"[yellow]{concept.trust_tier.value}[/yellow]")
    meta_table.add_row("Status", concept.frontmatter.status)
    meta_table.add_row("Tags", ", ".join(concept.frontmatter.tags))
    meta_table.add_row("File Path", str(concept.file_path))

    console.print(meta_table)

    if concept.links:
        link_table = Table(title="Outbound Relational Links", show_header=True)
        link_table.add_column("Anchor Text")
        link_table.add_column("Target")
        link_table.add_column("Resolved Concept ID")
        for link in concept.links:
            link_table.add_row(link.text, link.target, link.resolved_concept_id or "[dim]unresolved[/dim]")
        console.print(link_table)

    console.print(Panel(Markdown(concept.body), title="Document Body"))


def cmd_list() -> None:
    """
    List all concepts in the OKF bundle with metadata.
    """
    bundle = OKFBundle(settings.bundle_path)
    cids = bundle.list_all_concept_ids()

    table = Table(title=f"OKF Bundle Catalog ({settings.bundle_path})", show_header=True, header_style="bold blue")
    table.add_column("Concept ID", style="cyan")
    table.add_column("Title")
    table.add_column("Type", style="green")
    table.add_column("Trust Tier", style="yellow")

    for cid in cids:
        c = bundle.get_concept(cid)
        table.add_row(cid, c.title, c.type, c.trust_tier.value)

    console.print(table)


def main() -> None:
    parser = argparse.ArgumentParser(description="LangGraph OKF Consumer for Legal Knowledge Discovery")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # query command
    query_parser = subparsers.add_parser("query", help="Query the legal bundle using LangGraph OKF agent")
    query_parser.add_argument("text", type=str, help="Legal question or scenario")

    # inspect command
    inspect_parser = subparsers.add_parser("inspect", help="Inspect a specific concept document")
    inspect_parser.add_argument("concept_id", type=str, help="Concept ID to inspect")

    # list command
    subparsers.add_parser("list", help="List all concepts in the OKF bundle")

    args = parser.parse_args()

    if args.command == "query":
        cmd_query(args.text)
    elif args.command == "inspect":
        cmd_inspect(args.concept_id)
    elif args.command == "list":
        cmd_list()
    else:
        # Default behavior: run demonstration query
        cmd_query("What is the liability cap under the contract, what exceptions apply, and how does a data breach affect it with $100,000 in fees?")


if __name__ == "__main__":
    main()
