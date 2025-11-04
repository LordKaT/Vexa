import time
import uuid
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path

from lib.memory import ShortTermMemory, ConversationSummarizer

"""
    Orchestrator manages the memory lifecycle:
    1 - Check context window length and archive oldest chunks when full
    2 - Summarize archived chunks using LLM
    3 - Store summaries in ChromaDB for semantic recall
    4 - Query relevant memories based on user input
    5 - Inject recalled memories into system prompt
    6 - Deliver augmented context to LLM
"""
class Orchestrator:
    def __init__(self, app, *, chunk_size: int = 4, max_conversation: int | None = None) -> None:
        """
        Initialize orchestrator with memory system.
        
        :param app: The VexaApp instance (expects .conversation, .system_prompt).
        :param chunk_size: Number of messages to summarize together when archiving.
        :param max_conversation: Optional hard cap; falls back to app.max_conversation_length if None.
        """
        self.app = app
        self.chunk_size = chunk_size
        self.max_conversation = max_conversation or getattr(app, "max_conversation_length", 50)
        
        # Load memory configuration
        self._load_memory_config()
        
        # Initialize memory system if enabled
        if self.memory_enabled:
            try:
                self.mem = ShortTermMemory(
                    persist_directory=self.memory_config.get('persist_directory', '~/.vexa/memory/short_term'),
                    embedding_model=self.memory_config.get('embedding_model', 'sentence-transformers/all-MiniLM-L6-v2')
                )
                self.summarizer = ConversationSummarizer(app)
            except Exception as e:
                print(f"Warning: Could not initialize memory system: {e}")
                self.memory_enabled = False
                self.mem = None
                self.summarizer = None
        else:
            self.mem = None
            self.summarizer = None
    
    def _load_memory_config(self) -> None:
        """Load memory configuration from app settings."""
        import yaml
        
        try:
            config_path = Path(__file__).parent.parent / "config" / "settings.yaml"
            if config_path.exists():
                with open(config_path, 'r') as f:
                    settings = yaml.safe_load(f)
                    memory_settings = settings.get('memory', {})
                    self.memory_enabled = memory_settings.get('enabled', True)
                    self.memory_config = memory_settings.get('short_term', {})
                    self.recall_top_k = self.memory_config.get('recall_top_k', 5)
                    self.importance_threshold = self.memory_config.get('importance_threshold', 0.3)
                    self.chunk_size = self.memory_config.get('chunk_size', 4)
            else:
                self.memory_enabled = True
                self.memory_config = {}
                self.recall_top_k = 5
                self.importance_threshold = 0.3
        except Exception as e:
            print(f"Warning: Could not load memory config: {e}")
            self.memory_enabled = True
            self.memory_config = {}
            self.recall_top_k = 5
            self.importance_threshold = 0.3

    async def process_prompt(self, user_input: str) -> str:
        """
        Orchestration entry point:
          - Archive old messages if context window is full
          - Recall relevant memories from short-term storage
          - Compose augmented system prompt with memories
          - Send to LLM with full context
          - Update conversation history
        """
        # Archive if needed (before adding new messages)
        await self._archive_if_needed()

        # Recall relevant memories based on user input
        recalled = self._recall(user_input)
        
        # Compose system prompt with memory context
        system_with_memory = self._compose_system_with_memory(recalled)

        # Build message payload
        messages = [{"role": "system", "content": system_with_memory}]
        # Append all current messages except the system prompt at index 0
        if len(self.app.conversation) > 1:
            messages.extend(self.app.conversation[1:])
        # Add the new user input
        messages.append({"role": "user", "content": user_input})
        
        # Get response from LLM
        reply = await self.app._ask_ai_with_context(messages)

        # Update live conversation AFTER the call returns
        self.app.conversation.append({"role": "user", "content": user_input})
        self.app.conversation.append({"role": "assistant", "content": reply})

        return reply

    # ------------------------
    # Internal helpers
    # ------------------------

    async def _archive_if_needed(self) -> None:
        """
        If the conversation exceeds max length, archive the oldest chunk.
        
        Archives chunk_size messages at a time:
        1. Extract oldest N messages (excluding system prompt)
        2. Summarize using LLM
        3. Store in ChromaDB
        4. Remove from live conversation
        """
        if not self.memory_enabled or self.mem is None:
            # Fallback: simple truncation
            if len(self.app.conversation) > self.max_conversation:
                self.app.conversation = [self.app.conversation[0]] + self.app.conversation[-(self.max_conversation-1):]
            return
        
        convo = self.app.conversation
        if len(convo) <= self.max_conversation:
            return

        # Extract chunk to archive (oldest messages after system prompt)
        # Start at index 1 (skip system prompt at 0)
        start_idx = 1
        end_idx = min(start_idx + self.chunk_size, len(convo) - 1)  # Leave room for current exchange
        
        if start_idx >= end_idx:
            return
        
        chunk_to_archive = convo[start_idx:end_idx]
        
        # Summarize the chunk
        try:
            summary_result = await self.summarizer.summarize_messages(chunk_to_archive)
            summary_text = summary_result.get('summary', '')
            topic = summary_result.get('topic', '')
            
            if not summary_text:
                # Fallback if summarization fails
                summary_text = f"Archived {len(chunk_to_archive)} messages"
            
            # Store in ChromaDB
            self.mem.add_memory_chunk(
                summary=summary_text,
                original_messages=chunk_to_archive,
                topic=topic
            )
            
            # Remove archived messages from live conversation
            del convo[start_idx:end_idx]
            
        except Exception as e:
            print(f"Warning: Could not archive memory: {e}")
            # Fallback: just truncate
            if len(convo) > self.max_conversation:
                self.app.conversation = [convo[0]] + convo[-(self.max_conversation-1):]

    def _recall(self, latest_input: str) -> List[Dict[str, Any]]:
        """
        Recall relevant memories based on the latest user input.
        
        Uses semantic search to find contextually relevant past conversations.
        """
        if not self.memory_enabled or self.mem is None:
            return []
        
        try:
            memories = self.mem.query_relevant_memories(
                query_text=latest_input,
                top_k=self.recall_top_k,
                importance_threshold=self.importance_threshold
            )
            return memories
        except Exception as e:
            print(f"Warning: Could not recall memories: {e}")
            return []

    def _compose_system_with_memory(self, recalled: List[Dict[str, Any]]) -> str:
        """
        Compose system prompt with recalled memories injected as context.
        
        Format:
        [Base System Prompt]
        
        [Recalled Memories]
        - Memory 1
        - Memory 2
        ...
        [/Recalled Memories]
        
        Current time: [timestamp]
        """
        base = self.app.system_prompt
        
        if not recalled:
            return f"{base}\n\nCurrent time: {datetime.now()}"

        # Build memory context
        memory_lines = []
        for i, mem in enumerate(recalled, 1):
            summary = mem.get('summary', '')
            if summary:
                # Include relevance indicator (distance: lower = more relevant)
                distance = mem.get('distance', 1.0)
                relevance = "high" if distance < 0.3 else "medium" if distance < 0.6 else "low"
                memory_lines.append(f"{i}. [{relevance}] {summary}")
        
        if not memory_lines:
            return f"{base}\n\nCurrent time: {datetime.now()}"

        memory_context = "\n".join(memory_lines)
        
        return (
            f"{base}\n\n"
            "[Recalled from past conversations — reference as needed]\n"
            f"{memory_context}\n"
            "[/Recalled memories]\n\n"
            f"Current time: {datetime.now()}"
        )
