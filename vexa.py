
from rich.text import Text
from string import Template
from textual.app import App, ComposeResult
from textual.widgets import Label, Input, ListView, ListItem, RichLog
from textual.containers import Container, Vertical
from textual.reactive import reactive
from textual import events
import httpx
import asyncio
import yaml
from pathlib import Path


class TextAdventureApp(App):
    CSS = """
    Screen { layers: base overlay; }
    #main-container { layout: vertical; layer: base; }
    #log-container {
        width: 100%;
        height: 1fr; 
        layout: grid;
        grid-size: 1 1;
        layers: base overlay;
    }
    #description {
        layer: base;
        border: solid blue;
        width: 100%;
        height: 1fr;
        overflow-y: scroll;
        overflow-x: hidden;
    }
    #spinner {
        layer: overlay;
        width: auto;
        height: auto;
        dock: bottom;
        align-horizontal: left;
        padding-left: 0;
        color: yellow;
        background: transparent;
    }
    #chat-status {
        layer: overlay;
        width: auto;
        height: auto;
        dock: bottom;
        align-horizontal: left;
        offset-x: 1;
        color: yellow;
        background: transparent;
    }
    .hidden { display: none; }
    #input-container { width: 100%; height: 1; dock: bottom; }
    #input { width: 100%; height: 1; border: none; }
    #suggestions {
        layer: overlay;
        dock: bottom;
        margin-bottom: 1;

        max-height: 8;
        overflow-y: auto;
        border: round $accent;
        background: $panel;
        color: $text;
        padding: 0 1;
    }
    ListItem.--highlight { background: $accent; color: $text; }
    .hidden { display: none; }
    """

    commands = {
        "/help":     "List available commands.",
        "/quit":     "Exit the game.",
        "/clear":    "Clear the context window.",
        "/system":   "Set the system prompt (/system <prompt>).",
        "/echo":     "Write to the output buffer directly",
        "/name":     "Change your username",
        "/ainame":   "Change the AI name",
    }

    selected_index = reactive(0)

    system_prompt = ""

    ai_name = "Vexa"
    user_name = "Felicia"

    conversation = []

    _thinking = False

    def __init__(self):
        super().__init__()
        self.description_text = ""
        self._suggest_cmds: list[str] = []
        
        # Load configuration
        self._load_config()
        
        self.current_prompt_template = self.default_prompt_template
        self.system_prompt = self.default_prompt_template.safe_substitute(USER_NAME=self.user_name, AI_NAME=self.ai_name)

        self.conversation = [
            {"role": "system", "content": self.system_prompt}
        ]
        self.conversation = [
            {"role": "system", "content": self.system_prompt}
        ]
    
    def _load_config(self):
        """Load configuration from YAML file."""
        config_path = Path(__file__).parent / "config" / "default.yaml"
        
        # Default fallback values
        default_prompt = "User is $USER_NAME. You are $AI_NAME, a female AI created by $USER_NAME. You speak casually and try to be brief. You act slightly flirty with $USER_NAME. You are defensive of $USER_NAME. You are inquisitive but don't offer to help or assist."
        
        try:
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                
                # Load names
                self.ai_name = config.get('ai_name', 'Vexa')
                self.user_name = config.get('user_name', 'Felicia')
                
                # Load system prompt template
                prompt_text = config.get('system_prompt', default_prompt).strip()
                self.default_prompt_template = Template(prompt_text)
                
                # Load API configuration
                api_config = config.get('api', {})
                self.api_url = api_config.get('url', 'http://localhost:7777/v1/chat/completions')
                self.api_model = api_config.get('model', 'Vexa')
                self.api_timeout = api_config.get('timeout', 120.0)
                
                # Load conversation settings
                self.max_conversation_length = config.get('max_conversation_length', 100)
            else:
                # Use hardcoded defaults if config doesn't exist
                self.default_prompt_template = Template(default_prompt)
        except Exception as e:
            # Fall back to defaults on any error
            self.default_prompt_template = Template(default_prompt)
            print(f"Warning: Could not load config: {e}")

    def compose(self) -> ComposeResult:
        yield Vertical(
            Vertical(
                Container(
                    RichLog(id="description", wrap=True),
                    Label("", id="chat-status"),
                    Label("", id="spinner", classes="hidden"),
                    id="log-container"
                )
            ),
            Vertical(Input(placeholder="Enter your command...", id="input"), id="input-container"),
            id="main-container",
        )
        yield ListView(id="suggestions", classes="hidden")

    def on_mount(self) -> None:
        self.query_one("#input", Input).focus()
        self.update_status()
    
    def update_status(self) -> None:
        status_label = self.query_one("#chat-status", Label)
        status_label.update(f"[yellow]{self.user_name}[/yellow] [white]/[/white] [yellow]{self.ai_name}[/yellow]")

    # ---------- Suggestions ----------
    def on_input_changed(self, event: Input.Changed):
        text = event.value.strip().lower()
        suggestion_box = self.query_one("#suggestions", ListView)

        if text.startswith("/"):
            #term = text[1:]
            matches = [cmd for cmd in self.commands if text in cmd]
            suggestion_box.clear()
            self._suggest_cmds = []

            if matches:
                for cmd in matches:
                    suggestion_box.append(ListItem(Label(f"{cmd} — {self.commands[cmd]}")))
                self._suggest_cmds = matches[:]
                self.selected_index = 0
                self._update_highlight(suggestion_box)
                suggestion_box.remove_class("hidden")
            else:
                suggestion_box.add_class("hidden")
        else:
            suggestion_box.add_class("hidden")
            self._suggest_cmds = []

    def on_key(self, event: events.Key):
        suggestion_box = self.query_one("#suggestions", ListView)
        if suggestion_box.has_class("hidden"):
            return

        items = list(suggestion_box.children)
        if not items:
            return

        if event.key == "down":
            self.selected_index = (self.selected_index + 1) % len(items)
            self._update_highlight(suggestion_box)
        elif event.key == "up":
            self.selected_index = (self.selected_index - 1) % len(items)
            self._update_highlight(suggestion_box)
        elif event.key == "enter":
            if 0 <= self.selected_index < len(self._suggest_cmds):
                selected_cmd = self._suggest_cmds[self.selected_index]
                self._run_command(selected_cmd)
                input_widget = self.query_one("#input", Input)
                input_widget.value = ""
                suggestion_box.add_class("hidden")
                self._suggest_cmds = []

    def _update_highlight(self, suggestion_box: ListView):
        for i, item in enumerate(suggestion_box.children):
            if i == self.selected_index:
                item.add_class("--highlight")
                suggestion_box.scroll_to_widget(item, animate=False)
            else:
                item.remove_class("--highlight")

    # ---------- Submission ----------
    def on_input_submitted(self, event: Input.Submitted):
        command = event.value.strip()
        if not command:
            return
        self._run_command(command.strip())
        self.query_one("#input", Input).value = ""
        self.query_one("#suggestions", ListView).add_class("hidden")
        self._suggest_cmds = []
    
    async def _spinner(self):
        spinner_frames = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
        spinner_label = self.query_one("#spinner", Label)
        spinner_label.remove_class("hidden")

        i = 0
        while self._thinking:
            frame = spinner_frames[i % len(spinner_frames)]
            spinner_label.update(f"[yellow]{frame}[/yellow]")
            await asyncio.sleep(0.1)
            i += 1

        # cleanup when done
        spinner_label.update("")
        spinner_label.add_class("hidden")

    # ---------- Game logic ----------
    def _run_command(self, text: str):
        parts = text.strip().split(maxsplit=1)
        if not parts:
            return
        
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        match cmd:
            case "/help":
                lines = [f"  [bold cyan]{command}[/bold cyan] - {desc}" for command, desc in self.commands.items()]
                help_text = "\n".join(lines)
                self._update_description(f"Available commands:\n{help_text}")
            case "/quit":
                self.exit()
            case "/clear":
                self.conversation = [
                    {"role": "system", "content": self.system_prompt}
                ]
                self.query_one("#description", RichLog).clear()
                self._update_description("Conversation cleared.")
            case "/default":
                self.system_prompt = self.default_prompt_template.safe_substitute(USER_NAME=self.user_name, AI_NAME=self.ai_name)
            case "/system":
                if len(args) > 0:
                    self.current_prompt_template = Template(args.strip())
                    self.system_prompt = self.current_prompt_template.safe_substitute(USER_NAME=self.user_name, AI_NAME=self.ai_name)
                    self._update_description(f"[bold]System prompt set:[/bold] {self.current_prompt_template.template}")
                else:
                    self._update_description(f"[bold]System prompt:[/bold] {self.current_prompt_template.template}")
                    self._update_description(f"System prompt templates:\n  $USER_NAME - your user name ({self.user_name})\n  $AI_NAME - AI name ({self.ai_name})")
                    self._update_description(f"[bold]System prompt:[/bold] {self.system_prompt}")
            case "/echo":
                if len(args) > 0:
                    self._update_description(text.strip())
            case "/name":
                if len(args) > 0:
                    self.user_name = args.strip()
                    self.system_prompt = self.current_prompt_template.safe_substitute(USER_NAME=self.user_name, AI_NAME=self.ai_name)
                self._update_description(f"Your name is: [bold]{self.user_name}[/bold]")
                self.update_status()
            case "/ainame":
                if len(args) > 0:
                    self.ai_name = args.strip()
                    self.system_prompt = self.current_prompt_template.safe_substitute(USER_NAME=self.user_name, AI_NAME=self.ai_name)
                self._update_description(f"AI name is: [bold]{self.ai_name}[/bold]")
                self.update_status()
            case _:
                if len(text) <= 0:
                    return
                self._update_description(f"[bold]{self.user_name}:[/bold] {text.strip()}")
                self._thinking = True
                self.run_worker(self._spinner(), exclusive=False)
                try:
                    if hasattr(self, "_spinner_worker") and not self._spinner_worker.is_finished:
                        self._spinner_worker.cancel()
                except Exception:
                    pass
                self.run_worker(self._ask_ai(text.strip()))

    #def _update_description(self, new_text: str):
    #    self.query_one("#description", Label).update(new_text)
    def _update_description(self, text: str):
        desc = self.query_one("#description", RichLog)
        desc.write(Text.from_markup(f"{text}\n"))
        desc.scroll_end(animate=False)

    # ---------- AI hook ----------
    def _normalize_quotes(self, text: str) -> str:
        """Replace curly quotes, long dashes, and similar with plain ASCII."""
        replacements = {
            "“": '"', "”": '"', "„": '"', "‟": '"', "❝": '"', "❞": '"',
            "‘": "'", "’": "'", "‚": "'", "‛": "'", "❛": "'", "❜": "'",
            "—": "-",  # em dash
            "–": "-",  # en dash
            "―": "-",  # horizontal bar
            "…": "...",
            "′": "'", "″": '"',
        }
        for bad, good in replacements.items():
            text = text.replace(bad, good)
        return text

    async def _ask_ai(self, prompt: str):
        """Send the question to llama.cpp OpenAI-compatible API."""
        url = getattr(self, 'api_url', 'http://localhost:7777/v1/chat/completions')
        self.conversation.append({"role": "user", "content": prompt})

        payload = {
            "model": getattr(self, 'api_model', 'Vexa'),
            "messages": self.conversation
        }
        try:
            timeout = getattr(self, 'api_timeout', 120.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                reply = data["choices"][0]["message"]["content"]
                reply = self._normalize_quotes(reply)
                self.conversation.append({"role": "assistant", "content": reply})
                self._update_description(f"[bold]{self.ai_name}:[/bold] {reply}")
                max_len = getattr(self, 'max_conversation_length', 100)
                if len(self.conversation) > max_len:
                    self.conversation = [self.conversation[0]] + self.conversation[-(max_len-1):]
        except Exception as e:
            self._update_description(f"[Error contacting model]\n{e}")
        finally:
            self._thinking = False

if __name__ == "__main__":
    TextAdventureApp().run()
