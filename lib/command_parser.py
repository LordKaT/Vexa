from lib.vexa_interface import VexaInterface
from string import Template

class CommandParser:
    commands = {
        "/help":     "List available commands.",
        "/quit":     "Exit the game.",
        "/clear":    "Clear the context window.",
        "/system":   "Set the system prompt (/system <prompt>).",
        "/echo":     "Write to the output buffer directly",
        "/name":     "Change your username",
        "/ainame":   "Change the AI name",
    }

    def __init__(self, app: VexaInterface = None) -> None:
        self.app = app

    def run(self, text: str = "") -> None:
        parts = text.strip().split(maxsplit = 1)

        if not parts:
            return
        
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        handler = getattr(self, f"cmd_{cmd[1:]}", None)

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
