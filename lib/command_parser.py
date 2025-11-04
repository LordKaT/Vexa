from lib.vexa_interface import VexaInterface
from string import Template

class CommandParser:
    commands = {
        "/help":          "List available commands.",
        "/quit":          "Exit the game.",
        "/clear":         "Clear the context window.",
        "/system":        "Set the system prompt (/system <prompt>).",
        "/echo":          "Write to the output buffer directly",
        "/name":          "Change your username",
        "/ainame":        "Change the AI name",
        "/memory-stats":  "Show memory system statistics",
        "/memory-clear":  "Clear all stored memories (requires confirmation)",
        "/memory-search": "Search memories (/memory-search <query>)",
        "/memory-force":  "Force archive all but last 5 messages to memory",
        "/memory-preview":"Preview recalled memories for a query",
    }

    def __init__(self, app: VexaInterface = None) -> None:
        self.app = app

    def run(self, text: str = "") -> None:
        parts = text.strip().split(maxsplit = 1)

        if not parts:
            return
        
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        # Convert dashes to underscores for handler lookup
        # e.g., /memory-stats -> cmd_memory_stats
        handler_name = cmd[1:].replace('-', '_')
        handler = getattr(self, f"cmd_{handler_name}", None)

        if handler:
            handler(args)
        else:
            self.app.handle_ai_prompt(text.strip())
    
    def cmd_help(self, args: str = "") -> None:
        lines = [f"  [bold cyan]{c}[/bold cyan] - {d}" for c, d in self.commands.items()]
        self.app.update_description("Available commands:\n" + "\n".join(lines))
    
    def cmd_quit(self, args: str = "") -> None:
        self.app.exit_app()
    
    def cmd_clear(self, args: str = "") -> None:
        self.app.clear_conversation()
    
    def cmd_system(self, args: str) -> None:
        if args:
            self.app.current_prompt_template = Template(args.strip())
            self.app.system_prompt = self.app.current_prompt_template.safe_substitute(
                USER_NAME=self.app.user_name,
                AI_NAME=self.app.ai_name,
                USER_DESCRIPTION=self.app.user_description,
            )
            self.app.update_description(f"[bold]System prompt set:[/bold] {args.strip()}")
        else:
            self.app.update_description(f"[bold]System prompt:[/bold] {self.app.system_prompt}")

    def cmd_echo(self, args: str) -> None:
        if args:
            self.app.update_description(args)

    def cmd_name(self, args: str) -> None:
        if args:
            self.app.user_name = args.strip()
            self.app.update_status()
        self.app.update_description(f"Your name is: [bold]{self.app.user_name}[/bold]")

    def cmd_ainame(self, args: str) -> None:
        if args:
            self.app.ai_name = args.strip()
            self.app.update_status()
        self.app.update_description(f"AI name is: [bold]{self.app.ai_name}[/bold]")
    
    def cmd_memory_stats(self, args: str) -> None:
        """Display memory system statistics."""
        if not hasattr(self.app, 'orchestrator') or self.app.orchestrator is None or self.app.orchestrator.mem is None:
            self.app.update_description("[yellow]Memory system is not enabled[/yellow]")
            return
        
        try:
            stats = self.app.orchestrator.mem.get_stats()
            
            from datetime import datetime
            oldest = datetime.fromtimestamp(stats['oldest']).strftime('%Y-%m-%d %H:%M') if stats['oldest'] else 'N/A'
            newest = datetime.fromtimestamp(stats['newest']).strftime('%Y-%m-%d %H:%M') if stats['newest'] else 'N/A'
            
            output = [
                "[bold cyan]Memory System Statistics[/bold cyan]",
                f"  Total memories: [yellow]{stats['count']}[/yellow]",
                f"  Average importance: [yellow]{stats['avg_importance']:.2f}[/yellow]",
                f"  Oldest memory: [yellow]{oldest}[/yellow]",
                f"  Newest memory: [yellow]{newest}[/yellow]",
            ]
            self.app.update_description('\n'.join(output))
        except Exception as e:
            self.app.update_description(f"[red]Error getting memory stats: {e}[/red]")
    
    def cmd_memory_clear(self, args: str) -> None:
        """Clear all stored memories (with confirmation)."""
        if not hasattr(self.app, 'orchestrator') or self.app.orchestrator is None or self.app.orchestrator.mem is None:
            self.app.update_description("[yellow]Memory system is not enabled[/yellow]")
            return
        
        # Simple confirmation via argument
        if args.strip().lower() != 'confirm':
            self.app.update_description(
                "[yellow]This will delete all stored memories![/yellow]\n"
                "To confirm, use: [bold]/memory-clear confirm[/bold]"
            )
            return
        
        try:
            count = self.app.orchestrator.mem.clear_all()
            self.app.update_description(f"[green]Cleared {count} memories from storage[/green]")
        except Exception as e:
            self.app.update_description(f"[red]Error clearing memories: {e}[/red]")
    
    def cmd_memory_search(self, args: str) -> None:
        """Search stored memories."""
        if not hasattr(self.app, 'orchestrator') or self.app.orchestrator is None or self.app.orchestrator.mem is None:
            self.app.update_description("[yellow]Memory system is not enabled[/yellow]")
            return
        
        if not args.strip():
            self.app.update_description("[yellow]Usage:[/yellow] /memory-search <query>")
            return
        
        try:
            results = self.app.orchestrator.mem.search_memories(args.strip(), limit=5)
            
            if not results:
                self.app.update_description("[yellow]No matching memories found[/yellow]")
                return
            
            from datetime import datetime
            output = [f"[bold cyan]Found {len(results)} matching memories:[/bold cyan]"]
            
            for i, mem in enumerate(results, 1):
                summary = mem.get('summary', 'N/A')
                metadata = mem.get('metadata', {})
                timestamp = datetime.fromtimestamp(metadata.get('timestamp', 0)).strftime('%Y-%m-%d %H:%M')
                importance = metadata.get('importance', 0.0)
                distance = mem.get('distance', 1.0)
                
                output.append(f"\n[bold]{i}.[/bold] [dim]{timestamp}[/dim] (relevance: {1-distance:.2f}, importance: {importance:.2f})")
                output.append(f"   {summary}")
            
            self.app.update_description('\n'.join(output))
        except Exception as e:
            self.app.update_description(f"[red]Error searching memories: {e}[/red]")
    
    def cmd_memory_force(self, args: str) -> None:
        """Force archive all messages except the last 5 to memory."""
        if not hasattr(self.app, 'orchestrator') or self.app.orchestrator is None or self.app.orchestrator.mem is None:
            self.app.update_description("[yellow]Memory system is not enabled[/yellow]")
            return
        
        # Get current conversation
        convo = self.app.conversation
        
        # Need at least system prompt + 6 messages to archive anything
        if len(convo) <= 6:  # system + 5 messages
            self.app.update_description(
                "[yellow]Not enough messages to archive.[/yellow]\n"
                f"Current: {len(convo)-1} messages (need at least 6 to keep 5)"
            )
            return
        
        # Calculate what to archive (everything except system prompt and last 5)
        archive_start = 1
        archive_end = len(convo) - 5
        
        if archive_start >= archive_end:
            self.app.update_description("[yellow]No messages to archive[/yellow]")
            return
        
        messages_to_archive = convo[archive_start:archive_end]
        num_to_archive = len(messages_to_archive)
        
        self.app.update_description(
            f"[cyan]Archiving {num_to_archive} messages to memory...[/cyan]"
        )
        
        # Run as async worker within Textual's event loop
        self.app.run_worker(self._do_memory_force(messages_to_archive, convo, archive_end, num_to_archive))
    
    async def _do_memory_force(self, messages_to_archive, convo, archive_end, num_to_archive):
        """Async worker for memory force archival."""
        try:
            # Use orchestrator's summarizer to create summary
            summary_result = await self.app.orchestrator.summarizer.summarize_messages(messages_to_archive)
            
            summary_text = summary_result.get('summary', '')
            topic = summary_result.get('topic', '')
            
            if not summary_text:
                # Fallback summary
                summary_text = f"Archived {num_to_archive} messages"
            
            # Store in ChromaDB
            memory_id = self.app.orchestrator.mem.add_memory_chunk(
                summary=summary_text,
                original_messages=messages_to_archive,
                topic=topic
            )
            
            # Remove archived messages from conversation
            # Keep: [system_prompt] + [last 5 messages]
            self.app.conversation = [convo[0]] + convo[archive_end:]
            
            # Get statistics
            stats = self.app.orchestrator.mem.get_stats()
            
            self.app.update_description(
                f"[green]✓ Archived {num_to_archive} messages[/green]\n"
                f"  Summary: {summary_text[:100]}{'...' if len(summary_text) > 100 else ''}\n"
                f"  Topic: {topic if topic else 'N/A'}\n"
                f"  Memory ID: {memory_id[:8]}...\n"
                f"\n[cyan]Context window reduced:[/cyan]\n"
                f"  Before: {len(convo)} messages\n"
                f"  After: {len(self.app.conversation)} messages (system + 5)\n"
                f"\n[cyan]Total memories stored:[/cyan] {stats['count']}"
            )
            
        except Exception as e:
            self.app.update_description(f"[red]Error forcing memory archive: {e}[/red]")
            import traceback
            traceback.print_exc()
    
    def cmd_memory_preview(self, args: str) -> None:
        """Preview what memories would be recalled for a query."""
        if not hasattr(self.app, 'orchestrator') or self.app.orchestrator is None or self.app.orchestrator.mem is None:
            self.app.update_description("[yellow]Memory system is not enabled[/yellow]")
            return
        
        # Default to empty query if no args (shows most recent)
        query = args.strip() if args.strip() else "recent conversation"
        
        try:
            # Recall memories using orchestrator's method
            recalled = self.app.orchestrator._recall(query)
            
            if not recalled:
                self.app.update_description(
                    f"[yellow]No memories found for query:[/yellow] {query}\n"
                    "Try /memory-stats to see if any memories are stored."
                )
                return
            
            # Show what would be injected
            output = [
                f"[bold cyan]Memory Preview for query:[/bold cyan] {query}",
                f"\n[cyan]Found {len(recalled)} relevant memories:[/cyan]\n"
            ]
            
            from datetime import datetime
            for i, mem in enumerate(recalled, 1):
                summary = mem.get('summary', 'N/A')
                metadata = mem.get('metadata', {})
                timestamp = datetime.fromtimestamp(metadata.get('timestamp', 0)).strftime('%Y-%m-%d %H:%M')
                importance = metadata.get('importance', 0.0)
                distance = mem.get('distance', 1.0)
                
                # Determine relevance level (same as orchestrator)
                relevance = "high" if distance < 0.3 else "medium" if distance < 0.6 else "low"
                relevance_color = "green" if distance < 0.3 else "yellow" if distance < 0.6 else "red"
                
                output.append(
                    f"[bold]{i}.[/bold] [{relevance_color}][{relevance}][/{relevance_color}] "
                    f"[dim]{timestamp}[/dim] (distance: {distance:.3f}, importance: {importance:.2f})"
                )
                output.append(f"   {summary}\n")
            
            # Show how it would be composed in system prompt
            output.append("\n[bold cyan]How this would appear in system prompt:[/bold cyan]\n")
            output.append("[dim]" + "="*60 + "[/dim]")
            output.append(f"[dim]{self.app.system_prompt[:100]}...[/dim]")
            output.append("")
            output.append("[cyan]\\[Recalled from past conversations — reference as needed][/cyan]")
            
            for i, mem in enumerate(recalled, 1):
                distance = mem.get('distance', 1.0)
                relevance = "high" if distance < 0.3 else "medium" if distance < 0.6 else "low"
                summary = mem.get('summary', '')
                output.append(f"{i}. [{relevance}] {summary}")
            
            output.append("[cyan]\\[/Recalled memories][/cyan]")
            output.append("")
            output.append(f"[dim]Current time: {datetime.now()}[/dim]")
            output.append("[dim]" + "="*60 + "[/dim]")
            
            self.app.update_description('\n'.join(output))
            
        except Exception as e:
            self.app.update_description(f"[red]Error previewing memories: {e}[/red]")
            import traceback
            traceback.print_exc()
