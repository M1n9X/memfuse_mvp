from __future__ import annotations

import argparse
import sys

from .config import Settings
from .rag import RAGService
from rich.console import Console
from rich.markdown import Markdown
from .context import RetrievedChunk
from .tokenizer import count_tokens


def main() -> None:
    parser = argparse.ArgumentParser(description="MemFuse CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    ingest = sub.add_parser("ingest", help="Ingest a text file")
    ingest.add_argument("source", help="Document source label")
    ingest.add_argument("path", help="Path to text file")

    chat = sub.add_parser("chat", help="Start a chat turn")
    chat.add_argument("session", help="Session id")
    chat.add_argument("query", help="User query or '-' for interactive mode")
    chat.add_argument("--verbose", action="store_true", help="Show detailed context operations")

    debug = sub.add_parser("debug", help="Debug retrieval and context (no LLM call)")
    debug.add_argument("session", help="Session id")
    debug.add_argument("query", help="User query")

    args = parser.parse_args()

    settings = Settings.from_env()
    service = RAGService.from_settings(settings)

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
                # Call non-streaming backend for now; print as streaming chunks
                try:
                    answer = service.chat(args.session, user_q, trace=trace)
                except Exception as e:
                    console.print(f"[red]Chat failed:[/red] {e}")
                    continue
                # Verbose context operations
                if args.verbose and trace is not None:
                    console.rule("Context Operations")
                    # Show full assembled context blocks
                    from textwrap import shorten
                    # System prompt (from settings)
                    from .config import Settings as _S
                    sp = _S.from_env().system_prompt
                    console.print("[bold]System Prompt[/bold]\n" + sp)
                    # User input
                    console.print("\n[bold]User Query[/bold]\n" + user_q)
                    # Retrieved
                    if trace.retrieved_block_content:
                        console.print("\n[bold]Retrieved Chunks[/bold]\n" + trace.retrieved_block_content)
                    # History kept
                    if trace.history_rounds_after:
                        console.print(f"\n[bold]History (kept {trace.history_rounds_after} rounds)[/bold]")
                        # Print last few kept messages from final_messages
                        kept = [m for m in trace.final_messages if m.get('role') in {'user','ai'}]
                        for m in kept[-6:]:
                            who = 'You' if m['role']=='user' else 'Chatbot'
                            preview = m.get('content','')
                            console.print(f"[dim]{who}>[/dim] {preview}")
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
                    if trace.retrieved_count:
                        console.print(f"Retrieved top-{trace.retrieved_count} chunks:")
                        for src, score in trace.retrieved_preview:
                            console.print(f"  [dim]{src}[/dim] score={score:.3f}")
                    console.print(f"Final messages: {trace.final_messages_count}, token~={trace.final_tokens_estimate}")
                    console.rule()
                # Fake streaming: chunk the answer for UX
                console.print("[bold magenta]Chatbot>[/bold magenta] ", end="")
                for part in answer.split():
                    console.print(part + " ", end="", style="yellow")
                    console.file.flush()
                console.print("\n")
        else:
            try:
                answer = service.chat(args.session, args.query)
            except Exception as e:
                print(f"Chat failed: {e}", file=sys.stderr)
                sys.exit(2)
            console = Console()
            console.print("[bold magenta]Chatbot>[/bold magenta] " + answer)
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


if __name__ == "__main__":
    main()
