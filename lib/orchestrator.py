import time
import uuid
from datetime import datetime
from typing import List, Dict, Any

# stub
class MemoryBackend:
    def __init__(self) -> None:
        self._store: List[Dict[str, Any]] = []

    def add(self, *, summary: str, topic: str = "", importance: float = 0.5) -> None:
        self._store.append({
            "id": uuid.uuid4().hex,
            "timestamp": time.time(),
            "summary": summary,
            "topic": topic,
            "importance": importance,
        })

        if len(self._store) > 1000:
            self._store.pop(0)

    def query(self, query_text: str, top_k: int = 3) -> List[Dict[str, Any]]:
        # Stub recall: return the most recent K entries only.
        return self._store[-top_k:]

"""
    1 - Take entire context window, check length archive Nth chjat entry into the DB
    2 - Recall memory based only on last user input
    3 - Append recalled memory into system prompt
    4 - Deliver payload to _ask_ai_with_context
"""
class Orchestrator:
    def __init__(self, app, *, archive_index: int = 1, max_conversation: int | None = None) -> None:
        """
        :param app: The VexaApp instance (expects .conversation, .system_prompt).
        :param archive_index: The 1-based index within the conversation to archive when oversized.
                              Default 1 archives the oldest non-system entry at index 1.
        :param max_conversation: Optional hard cap; falls back to app.max_conversation_length if None.
        """
        self.app = app
        self.mem = MemoryBackend()
        self.archive_index = max(1, archive_index)  # ensure we never archive the system prompt
        self.max_conversation = max_conversation or getattr(app, "max_conversation_length", 100)

    async def process_prompt(self, user_input: str) -> str:
        """
        Orchestration entry:
          - Archive Nth entry if the context is too long.
          - Recall memory based on the latest user_input.
          - Append recalled memory in the system prompt.
          - Build full payload and send to _ask_ai_with_context.
        """
        self._archive_if_needed()

        recalled = self._recall(user_input)
        system_with_memory = self._compose_system_with_memory(recalled)

        messages = [{"role": "system", "content": system_with_memory}]
        # append all current messages except the system prompt at index 0
        if len(self.app.conversation) > 1:
            messages.extend(self.app.conversation[1:])
        # add the new user input
        messages.append({"role": "user", "content": user_input})
        
        reply = await self.app._ask_ai_with_context(messages)

        # Update live conversation AFTER the call returns
        self.app.conversation.append({"role": "user", "content": user_input})
        self.app.conversation.append({"role": "assistant", "content": reply})

        return reply

    # ------------------------
    # Internal helpers
    # ------------------------

    def _archive_if_needed(self) -> None:
        """
        If the conversation exceeds the configured length, archive the Nth entry
        (default: the oldest non-system at index 1) into the memory DB and remove it
        from the live context window.
        """
        convo = self.app.conversation
        if len(convo) <= self.max_conversation:
            return

        idx = min(self.archive_index, len(convo) - 1)  # clamp to valid, avoid system at 0
        entry = convo[idx]

        # Create a compact summary; in a real system you'd LLM-summarize here.
        role = entry.get("role", "unknown")
        content = entry.get("content", "")
        summary = f"{role}: {content[:300]}"

        self.mem.add(summary=summary, topic="archived_context", importance=0.6)

        # Remove the archived entry from the live conversation
        del convo[idx]

    def _recall(self, latest_input: str) -> List[Dict[str, Any]]:
        """
        Recall memories for ONLY the latest input.
        (Stub backend returns the most recent K memories.)
        """
        return self.mem.query(latest_input, top_k=3)

    def _compose_system_with_memory(self, recalled: List[Dict[str, Any]]) -> str:
        """
        Append recalled memory inside the system prompt as background context.
        """
        base = self.app.system_prompt
        if not recalled:
            return base

        lines = "\n".join(f"- {m['summary']}" for m in recalled if m.get("summary"))
        if not lines:
            return base

        return (
            f"{base}\n\n"
            "[Recalled memories — background awareness only]\n"
            f"{lines}\n"
            "[/Recalled memories]\n"
            f"Current time: {datetime.now()}"
        )
