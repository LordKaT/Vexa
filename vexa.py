from lib.command_parser import CommandParser

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
import sys
from pathlib import Path

class VexaApp(App):
    CSS = ""
    system_prompt = ""
    ai_name = "Vexa"
    user_name = "Felicia"
    user_description = ""

    conversation = []

    selected_index = reactive(0)
    _thinking = False

    def __init__(self, profile: str = "vexa") -> None:
        super().__init__()
        self.description_text = ""
        self._suggest_cmds: list[str] = []
        self.profile = profile
        
        self._load_css()
        self._load_config()
        
        self.current_prompt_template = self.default_prompt_template
        self.system_prompt = self.default_prompt_template.safe_substitute(
            USER_NAME=self.user_name, 
            AI_NAME=self.ai_name,
            USER_DESCRIPTION=self.user_description
        )

        self.conversation = [
            {"role": "system", "content": self.system_prompt}
        ]

        self.command_parser = CommandParser(self)
    
    def _load_css(self):
        css_path = Path(__file__).parent / "config" / "textual.css"
        
        try:
            if css_path.exists():
                with open(css_path, 'r') as f:
                    self.CSS = f.read()
            else:
                print(f"Warning: CSS file not found at {css_path}")
        except Exception as e:
            print(f"Warning: Could not load CSS: {e}")
    
    def _load_config(self):
        config_dir = Path(__file__).parent / "config"
        
        # Default fallback values
        default_prompt = "User is $USER_NAME. You are $AI_NAME, a female AI created by $USER_NAME. You speak casually and try to be brief. You act slightly flirty with $USER_NAME. You are defensive of $USER_NAME. You are inquisitive but don't offer to help or assist."
        
        try:
            # Load user configuration
            user_config_path = config_dir / "user.yaml"
            if user_config_path.exists():
                with open(user_config_path, 'r') as f:
                    user_config = yaml.safe_load(f)
                    self.user_name = user_config.get('user_name', 'Felicia')
                    self.user_description = user_config.get('user_description', '').strip()
            else:
                self.user_name = 'Felicia'
                self.user_description = ''
            
            # Load settings configuration
            settings_config_path = config_dir / "settings.yaml"
            if settings_config_path.exists():
                with open(settings_config_path, 'r') as f:
                    settings_config = yaml.safe_load(f)
                    
                    # Load API configuration
                    api_config = settings_config.get('api', {})
                    self.api_url = api_config.get('url', 'http://localhost:7777/v1/chat/completions')
                    self.api_model = api_config.get('model', 'Vexa')
                    self.api_timeout = api_config.get('timeout', 120.0)
                    
                    # Load conversation settings
                    self.max_conversation_length = settings_config.get('max_conversation_length', 100)
            else:
                self.api_url = 'http://localhost:7777/v1/chat/completions'
                self.api_model = 'Vexa'
                self.api_timeout = 120.0
                self.max_conversation_length = 100
            
            # Load AI profile configuration
            profile_path = config_dir / "profiles" / f"{self.profile}.yaml"
            if profile_path.exists():
                with open(profile_path, 'r') as f:
                    profile_config = yaml.safe_load(f)
                    self.ai_name = profile_config.get('ai_name', 'Vexa')
                    
                    # Load system prompt template
                    prompt_text = profile_config.get('system_prompt', default_prompt).strip()
                    self.default_prompt_template = Template(prompt_text)
            else:
                self.ai_name = 'Vexa'
                self.default_prompt_template = Template(default_prompt)
                print(f"Warning: Profile '{self.profile}' not found, using defaults")
                
        except Exception as e:
            # Fall back to defaults on any error
            self.user_name = 'Felicia'
            self.user_description = ''
            self.ai_name = 'Vexa'
            self.api_url = 'http://localhost:7777/v1/chat/completions'
            self.api_model = 'Vexa'
            self.api_timeout = 120.0
            self.max_conversation_length = 100
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
        self.update_statusbar()

    # Suggestions box
    def on_input_changed(self, event: Input.Changed):
        text = event.value.strip().lower()
        suggestion_box = self.query_one("#suggestions", ListView)

        if text.startswith("/"):
            matches = [cmd for cmd in self.command_parser.commands if text in cmd]
            suggestion_box.clear()
            self._suggest_cmds = []

            if matches:
                for cmd in matches:
                    suggestion_box.append(ListItem(Label(f"{cmd} — {self.command_parser.commands[cmd]}")))
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
                self.command_parser.run(selected_cmd)
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

    # Submission
    def on_input_submitted(self, event: Input.Submitted):
        command = event.value.strip()
        if not command:
            return
        self.command_parser.run(command.strip())
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

    # Interface contract
    def update_description(self, text: str = "") -> None:
        desc = self.query_one("#description", RichLog)
        desc.write(Text.from_markup(f"{text}\n"))
        desc.scroll_end(animate=False)
    
    def update_statusbar(self, text: str = "") -> None:
        status_label = self.query_one("#chat-status", Label)
        status_label.update(f"[yellow]{self.user_name}[/yellow] [white]/[/white] [yellow]{self.ai_name}[/yellow]")
    
    def clear_conversation(self) -> None:
        self.conversation = [
            {"role": "system", "content": self.system_prompt}
        ]
        desc = self.query_one("#description", RichLog)
        desc.clear()
        desc.write(Text.from_markup(f"[Conversation cleared]\n"))

    def exit_app(self) -> None:
        sys.exit()
    
    def handle_ai_prompt(self, prompt: str = "") -> None:
        self._thinking = True
        self.run_worker(self._spinner(), exclusive=False)
        self.run_worker(self._ask_ai(prompt))

    # AI hooks
    def _normalize_quotes(self, text: str) -> str:
        """
            Replace curly quotes, long dashes, and similar with plain ASCII.

            No, seriously, I hate that models are trained to use these things.
        """
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
        url = getattr(self, 'api_url', 'http://localhost:7777/v1/chat/completions')
        self.conversation.append({"role": "user", "content": prompt})

        self.update_description(f"[bold]{self.app.user_name}:[/bold] {prompt.strip()}")

        payload = {
            "model": getattr(self, 'api_model', 'Vexa'),
            "messages": self.conversation
        }
        try:
            timeout = getattr(self, 'api_timeout', 5000.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                reply = data["choices"][0]["message"]["content"]
                reply = self._normalize_quotes(reply)
                self.conversation.append({"role": "assistant", "content": reply})
                self.update_description(f"[bold]{self.ai_name}:[/bold] {reply}")
                max_len = getattr(self, 'max_conversation_length', 100)
                if len(self.conversation) > max_len:
                    self.conversation = [self.conversation[0]] + self.conversation[-(max_len-1):]
        except Exception as e:
            self.update_description(f"[Error contacting model]\n{e}")
        finally:
            self._thinking = False

if __name__ == "__main__":
    profile = sys.argv[1] if len(sys.argv) > 1 else "vexa"
    VexaApp(profile=profile).run()
