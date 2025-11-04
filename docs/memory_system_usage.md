# Vexa Memory System - User Guide

## Overview

Vexa now includes a persistent memory system that allows the AI to remember past conversations beyond the immediate context window. This eliminates the need for separate "chat sessions" and creates a more natural, continuous conversation experience.

## Architecture

### Three-Tier Memory System (Phase 1 Implemented)

```
┌─────────────────────────────────┐
│  L1: Context Window (Active)   │  ← Current conversation (50 messages)
│  - 100% fidelity                │
│  - Immediate access             │
└─────────────────────────────────┘
            ↓ Archive when full
┌─────────────────────────────────┐
│  L2: Short-Term Memory (ChromaDB) │  ← Persistent semantic memory
│  - 70-80% fidelity              │
│  - Vector similarity search     │
│  - Days to weeks retention      │
└─────────────────────────────────┘
```

## Features

### Automatic Memory Archival

When your conversation exceeds 50 messages, the oldest messages are automatically:
1. **Summarized** using the LLM
2. **Stored** in ChromaDB with semantic embeddings
3. **Removed** from the active context window

This keeps the context window manageable while preserving conversation history.

### Semantic Memory Recall

When you send a message, Vexa:
1. **Searches** past memories for relevant context
2. **Ranks** results by semantic similarity
3. **Injects** top-K memories into the system prompt
4. **References** them naturally in responses

### Importance Scoring

Each memory is automatically scored based on:
- **Message length** (longer = more substantial)
- **Exchange depth** (more back-and-forth = more important)
- **Information density** (unique content = higher value)

Low-importance exchanges (< 0.3) are not stored to save space.

## Configuration

Edit `config/settings.yaml` to customize memory behavior:

```yaml
memory:
  enabled: true  # Toggle memory system on/off
  
  short_term:
    persist_directory: "~/.vexa/memory/short_term"
    chunk_size: 4  # Messages summarized together
    max_entries: 1000  # Auto-prune beyond this
    retention_days: 30  # Delete memories older than this
    embedding_model: "sentence-transformers/all-MiniLM-L6-v2"
    recall_top_k: 5  # Number of memories to recall per query
    importance_threshold: 0.3  # Minimum importance to store
```

## Commands

### `/memory-stats`

Display memory system statistics:

```
Memory System Statistics
  Total memories: 42
  Average importance: 0.68
  Oldest memory: 2025-10-15 14:23
  Newest memory: 2025-11-03 22:15
```

### `/memory-search <query>`

Search your stored memories:

```
/memory-search Python programming

Found 3 matching memories:
1. [2025-11-01 10:30] (relevance: 0.85, importance: 0.72)
   Discussion about Python best practices including PEP8, type hints...

2. [2025-10-28 15:45] (relevance: 0.73, importance: 0.65)
   User asked about async/await in Python. Explained event loops...
```

### `/memory-clear confirm`

Delete all stored memories (use with caution):

```
/memory-clear
⚠️  This will delete all stored memories!
To confirm, use: /memory-clear confirm

/memory-clear confirm
✓ Cleared 42 memories from storage
```

### `/memory-force`

Force immediate archival of all messages except the last 5:

```
/memory-force

✓ Archived 25 messages
  Summary: Discussion covered Python best practices, async/await patterns...
  Topic: Python programming
  Memory ID: abc12345...

Context window reduced:
  Before: 31 messages
  After: 6 messages (system + 5)

Total memories stored: 3
```

**Use cases:**
- Quickly compress a long conversation
- Force memory creation before context gets too large
- Manually trigger archival without waiting for automatic threshold
- Reset context window while preserving history

### `/memory-preview [query]`

Preview what memories would be recalled for a query:

```
/memory-preview Python programming

Memory Preview for query: Python programming

Found 3 relevant memories:

1. [high] 2025-11-03 10:30 (distance: 0.285, importance: 0.78)
   Discussion about Python best practices including PEP8, type hints...

2. [medium] 2025-11-03 09:15 (distance: 0.520, importance: 0.65)
   User asked about async/await patterns in Python...

3. [low] 2025-11-03 08:00 (distance: 0.780, importance: 0.55)
   Brief mention of Python in context of web development...

How this would appear in system prompt:
============================================================
You are Vexa, a female AI created by Felicia...

[Recalled from past conversations — reference as needed]
1. [high] Discussion about Python best practices including PEP8...
2. [medium] User asked about async/await patterns in Python...
3. [low] Brief mention of Python in context of web development...
[/Recalled memories]

Current time: 2025-11-03 19:35:06
============================================================
```

**Use cases:**
- Check what memories would be recalled before asking a question
- Verify memories were properly archived after `/memory-force`
- Debug memory recall behavior
- See exactly how memories are injected into system prompt

**Note:** Without arguments, uses "recent conversation" as the default query.

## Storage Location

Memories are stored locally at:
- **Default:** `~/.vexa/memory/short_term/`
- **Size:** ~500KB per 1000 memories
- **Format:** ChromaDB vector database

To back up or transfer memories, copy the entire directory.

## How It Works

### Example Conversation Flow

1. **You:** "What are Python best practices?"
   - Context window: 10 messages
   - No archival needed yet

2. **Vexa:** "Follow PEP8, use type hints..."
   - Response added to context window

3. ...*48 more messages*...

4. **Context window full (50 messages)**
   - Oldest 4 messages archived
   - Summarized: "Discussion about Python best practices..."
   - Stored in ChromaDB with importance score

5. **You:** "Remind me what we said about Python?"
   - Semantic search finds archived memory
   - Recalled memory: "Discussion about Python best practices..."
   - Injected into system prompt
   - **Vexa:** "Earlier we discussed PEP8, type hints..."

## Performance

- **Embedding model:** all-MiniLM-L6-v2 (384 dimensions)
- **Search time:** < 100ms for top-5 results
- **Summarization:** ~2-3 seconds per chunk (depends on LLM speed)
- **Memory usage:** ~10MB for 10,000 conversation turns

## Privacy

- ✓ All data stored **locally** (no cloud sync)
- ✓ Standard file permissions apply
- ✓ Can be disabled with `memory.enabled: false`
- ✓ Can be wiped with `/memory-clear confirm`

## Troubleshooting

### Memory system not initializing

**Error:** `Could not initialize memory system`

**Solution:**
1. Check that dependencies are installed: `pip install chromadb sentence-transformers`
2. Verify write permissions for `~/.vexa/memory/short_term/`
3. Check disk space availability

### Memories not being recalled

**Issue:** Vexa doesn't reference past conversations

**Solutions:**
1. Check importance threshold in settings (lower = more memories stored)
2. Increase `recall_top_k` (more memories injected per query)
3. Use `/memory-search` to verify memories exist
4. Ensure embeddings are being generated (check console for errors)

### ChromaDB errors

**Error:** `chromadb.errors.*`

**Solutions:**
1. Delete `~/.vexa/memory/short_term/` and restart (fresh start)
2. Update chromadb: `pip install --upgrade chromadb`
3. Check Python version (3.9+ required)

## Future Enhancements (Phase 2)

Coming in Phase 2:
- **Long-term memory** (SQLite) for compressed historical summaries
- **Automatic compression** of old short-term memories
- **Topic clustering** for better organization
- **Time-decay weighting** (recent memories prioritized)
- **Export/import** tools for memory transfer

## Technical Details

### Memory Chunk Structure

```python
{
    "id": "uuid",
    "document": "Summarized conversation text",
    "embedding": [384-dimensional vector],
    "metadata": {
        "timestamp": 1730673245.123,
        "importance": 0.75,
        "topic": "Python programming",
        "message_count": 4,
        "conversation_range": "4 messages"
    }
}
```

### Importance Calculation

```python
score = 0.5  # baseline
score += min(avg_message_length / 1000, 0.2)  # length factor
score += min(message_count * 0.02, 0.15)      # depth factor
score += min(unique_chars / 50, 0.15)         # variety factor
return min(score, 1.0)
```

### Semantic Search

Uses **cosine similarity** on sentence-transformer embeddings:
- Distance < 0.3: High relevance
- Distance 0.3-0.6: Medium relevance
- Distance > 0.6: Low relevance

## Credits

Memory system design inspired by:
- Human memory hierarchy (L1/L2/L3 cache analogy)
- Vector databases for semantic search
- LLM-powered summarization techniques

---

**Questions?** Check the [implementation plan](memory_system_plan.md) for architectural details.
