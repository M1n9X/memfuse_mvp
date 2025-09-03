from __future__ import annotations

import argparse
import sys

from .config import Settings
from .rag import RAGService
from rich.console import Console
from rich.panel import Panel
from .context import RetrievedChunk
from .tokenizer import count_tokens


def main() -> None:
    parser = argparse.ArgumentParser(description="MemFuse CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    ingest = sub.add_parser("ingest", help="Ingest a text file")
    ingest.add_argument("source", help="Document source label")
    ingest.add_argument("path", help="Path to text file")

    chat = sub.add_parser("chat", help="Start a chat turn (RAG only)")
    chat.add_argument("session", help="Session id")
    chat.add_argument("query", help="User query or '-' for interactive mode")
    chat.add_argument("--verbose", action="store_true", help="Show detailed context operations")

    # Orchestrated task runner (Phase 3/4)
    task = sub.add_parser("task", help="Run orchestrated multi-agent task")
    task.add_argument("session", help="Session id")
    task.add_argument("goal", help="High-level user goal or '-' for interactive mode")
    task.add_argument("--verbose", action="store_true", help="Show planner and agent steps")

    debug = sub.add_parser("debug", help="Debug retrieval and context (no LLM call)")
    debug.add_argument("session", help="Session id")
    debug.add_argument("query", help="User query")

    health = sub.add_parser("health", help="Check environment and dependencies")
    health.add_argument("--strict", action="store_true", help="Exit non-zero if any check fails")
    health.add_argument("--check-embeddings", action="store_true", help="Perform a live embeddings API check")
    health.add_argument("--check-llm", action="store_true", help="Perform a live LLM chat API check")
    health.add_argument("--db-timeout", type=int, default=2, help="DB connect timeout seconds (default: 2)")

    args = parser.parse_args()

    settings = Settings.from_env()
    service = RAGService.from_settings(settings)
    # Lazy import to avoid circulars if user never runs task
    orchestrator = None

    if args.cmd == "ingest":
        try:
            with open(args.path, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError as e:
            print(f"Failed to read file: {e}", file=sys.stderr)
            sys.exit(1)
        n = service.ingest_document(args.source, content)
        print(f"Ingested {n} chunks from {args.path}")
    elif args.cmd == "chat":
        console = Console()
        # Interactive mode if query is '-'
        if args.query == "-":
            console.print("[bold green]MemFuse Chat[/bold green] - type /exit to quit", highlight=False)
            while True:
                try:
                    user_q = console.input("[bold cyan]You>[/bold cyan] ")
                except (KeyboardInterrupt, EOFError):
                    console.print("\n[dim]Bye[/dim]")
                    break
                if user_q.strip() in {"/exit", ":q", "/quit"}:
                    console.print("[dim]Bye[/dim]")
                    break
                # Build optional trace
                from .tracing import ContextTrace
                trace = ContextTrace() if args.verbose else None
                # Call non-streaming backend and print normally
                try:
                    answer = service.chat(args.session, user_q, trace=trace)
                except Exception as e:
                    console.print(f"[red]Chat failed:[/red] {e}")
                    continue
                # Verbose context operations
                if args.verbose and trace is not None:
                    # Clear previous screen to avoid mixed old/new outputs
                    try:
                        console.clear()
                    except Exception:
                        pass
                    console.rule("Context Operations")
                    # Show full assembled context blocks
                    from textwrap import shorten
                    # System prompt (from settings)
                    from .config import Settings as _S
                    sp = _S.from_env().system_prompt
                    console.print(Panel(sp, title="[bold blue]System Prompt[/bold blue]", border_style="blue"))
                    # User input
                    console.print(Panel(user_q, title="[bold cyan]User Query[/bold cyan]", border_style="cyan"))
                    # Retrieved (facts + chunks)
                    retrieved_content = trace.retrieved_block_content or "<none>"
                    rc_title = f"[bold green]Retrieved[/bold green] (facts={trace.retrieved_facts_count}, chunks={trace.retrieved_chunks_count})"
                    console.print(Panel(retrieved_content, title=rc_title, border_style="green"))
                    # History kept (show exactly what's kept, not meta)
                    if trace.history_rounds_after:
                        kept_lines = []
                        for role, content in trace.history_kept_messages[-6:]:
                            label = '[cyan]You[/cyan]' if role == 'user' else '[magenta]Assistant[/magenta]'
                            kept_lines.append(f"{label} {content}")
                        hist_title = f"[bold yellow]History[/bold yellow] (kept {trace.history_rounds_after} rounds)"
                        console.print(Panel("\n".join(kept_lines) if kept_lines else "<none>", title=hist_title, border_style="yellow"))
                    if trace.user_truncated:
                        console.print(f"[yellow]User input truncated:[/yellow] {trace.user_tokens_before} -> {trace.user_tokens_after}")
                    if trace.history_truncated:
                        console.print(f"[yellow]History truncated:[/yellow] {trace.history_tokens_before} -> {trace.history_tokens_after} tokens; kept rounds {trace.history_rounds_after}/{trace.history_rounds_before}")
                        # Show a compact summary of dropped content (first line only)
                        for rid, spk, cont in trace.dropped_messages[:3]:
                            preview = cont.split('\n',1)[0]
                            if len(preview) > 120:
                                preview = preview[:120] + '...'
                            console.print(f"[dim]Dropped {spk}#{rid}:[/dim] {preview}")
                    if trace.summary_added:
                        console.print("[green]Added compressed history summary[/green]")
                        console.print(trace.summary_text)
                    if trace.retrieved_facts_count or trace.retrieved_chunks_count:
                        if trace.retrieved_facts_count:
                            console.print(f"Retrieved facts: {trace.retrieved_facts_count}")
                            for src, score in trace.retrieved_facts_preview:
                                console.print(f"  [dim]{src}[/dim] score={score:.3f}")
                        if trace.retrieved_chunks_count:
                            console.print(f"Retrieved chunks: {trace.retrieved_chunks_count}")
                            for src, score in trace.retrieved_chunks_preview:
                                console.print(f"  [dim]{src}[/dim] score={score:.3f}")
                    console.print(f"Final messages: {trace.final_messages_count}, token~={trace.final_tokens_estimate}")
                    # Final Context panel
                    fc_lines = ["(System prompt is prepended separately; shown above)"]
                    for i, m in enumerate(trace.final_messages, 1):
                        role = m.get('role','')
                        content = m.get('content','')
                        fc_lines.append(f"[{i}] ({role}) {content}")
                    console.print(Panel("\n".join(fc_lines), title="[bold magenta]Final Context (raw, order to LLM)[/bold magenta]", border_style="magenta"))
                    console.rule()
                # Print full answer in a distinct panel
                console.print(Panel(answer, title="[bold magenta]Assistant[/bold magenta]", border_style="magenta", style="yellow"))
        else:
            try:
                answer = service.chat(args.session, args.query)
            except Exception as e:
                print(f"Chat failed: {e}", file=sys.stderr)
                sys.exit(2)
            console = Console()
            console.print(Panel(answer, title="[bold magenta]Assistant[/bold magenta]", border_style="magenta", style="yellow"))
    elif args.cmd == "task":
        from .orchestrator import Orchestrator
        if orchestrator is None:
            orchestrator = Orchestrator.from_settings(settings)
        console = Console()
        if args.goal == "-":
            console.print("[bold green]MemFuse Orchestrator[/bold green] - type /exit to quit", highlight=False)
            while True:
                try:
                    goal = console.input("[bold cyan]Goal>[/bold cyan] ")
                except (KeyboardInterrupt, EOFError):
                    console.print("\n[dim]Bye[/dim]")
                    break
                if goal.strip() in {"/exit", ":q", "/quit"}:
                    console.print("[dim]Bye[/dim]")
                    break
                try:
                    result = orchestrator.handle_request(args.session, goal, verbose=args.verbose)
                except Exception as e:
                    console.print(f"[red]Task failed:[/red] {e}")
                    continue
                console.print(Panel(result, title="[bold magenta]Result[/bold magenta]", border_style="magenta"))
        else:
            try:
                if orchestrator is None:
                    orchestrator = Orchestrator.from_settings(settings)
                result = orchestrator.handle_request(args.session, args.goal, verbose=args.verbose)
            except Exception as e:
                print(f"Task failed: {e}", file=sys.stderr)
                sys.exit(2)
            console = Console()
            console.print(Panel(result, title="[bold magenta]Result[/bold magenta]", border_style="magenta"))
    elif args.cmd == "debug":
        # Step 1: history
        history = service.db.fetch_conversation_history(session_id=args.session)
        # Step 2: retrieval via Jina + pgvector
        vec = service.embedder.embed([args.query])[0]
        rows = service.db.search_similar_chunks(vec, service.settings.rag_top_k)
        retrieved = [RetrievedChunk(content=r[0], source=r[1], score=r[2]) for r in rows]
        # Step 3: context building
        messages = service.context.build_final_context(args.query, history, retrieved)
        # Report
        print(f"history_messages={len(history)}")
        print(f"retrieved_chunks={len(retrieved)} (top {service.settings.rag_top_k})")
        for i, c in enumerate(retrieved[:3], 1):
            preview = (c.content[:120] + '...') if len(c.content) > 120 else c.content
            print(f"  {i}. source={c.source} score={c.score:.3f} preview={preview}")
        total_tokens = sum(count_tokens(m.get('content','')) + 4 for m in messages)
        print(f"context_messages={len(messages)} total_tokens~={total_tokens}")
    elif args.cmd == "health":
        console = Console()
        ok = True
        console.rule("Health Check")
        # Settings summary
        console.print(Panel(
            f"DB={settings.database_url}\nEMBED_MODEL={settings.embedding_model}\nOPENAI_MODEL={settings.openai_model}",
            title="Settings", border_style="blue"
        ))

        # DB check with timeout
        try:
            import psycopg
            dsn = settings.database_url
            conn = psycopg.connect(dsn, autocommit=True, connect_timeout=args.db_timeout)
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    (one,) = cur.fetchone()
                    cur.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema='public'")
                    (tcount,) = cur.fetchone()
                console.print("[green]DB:[/green] OK (tables=" + str(tcount) + ")")
            finally:
                conn.close()
        except Exception as e:
            ok = False
            console.print(f"[red]DB:[/red] FAIL - {e}")

        # Embeddings check (optional)
        if args.check_embeddings:
            try:
                vecs = service.embedder.embed(["ping"]) or []
                dim = len(vecs[0]) if vecs else 0
                if dim > 0:
                    console.print(f"[green]Embeddings:[/green] OK (dim={dim})")
                else:
                    ok = False
                    console.print("[red]Embeddings:[/red] FAIL - empty response")
            except Exception as e:
                ok = False
                console.print(f"[red]Embeddings:[/red] FAIL - {e}")

        # LLM check (optional)
        if args.check_llm:
            try:
                out = service.llm.chat(settings.system_prompt, [{"role":"user","content":"ping"}])
                if out:
                    console.print("[green]LLM:[/green] OK")
                else:
                    ok = False
                    console.print("[red]LLM:[/red] FAIL - empty response")
            except Exception as e:
                ok = False
                console.print(f"[red]LLM:[/red] FAIL - {e}")

        console.rule()
        if args.strict and not ok:
            sys.exit(3)
        else:
            console.print("[bold]Health check completed[/bold]")


if __name__ == "__main__":
    main()
