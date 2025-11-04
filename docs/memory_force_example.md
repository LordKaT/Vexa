# `/memory-force` Command - Detailed Example

## Overview

The `/memory-force` command allows you to manually trigger aggressive memory archival, keeping only the last 5 messages in the context window while archiving everything else to persistent memory.

## How It Works

```
Before /memory-force:
┌─────────────────────────────────────┐
│ Context Window (31 messages)        │
├─────────────────────────────────────┤
│ [0] System Prompt                   │
│ [1] User: What are Python practices?│
│ [2] AI: Follow PEP8...              │
│ [3] User: Tell me about async       │
│ [4] AI: async/await is...           │
│ ... (20 more messages)              │
│ [26] User: What about testing?      │
│ [27] AI: Use pytest...              │
│ [28] User: How do I mock?           │
│ [29] AI: Use unittest.mock...       │
│ [30] User: Show me an example       │
│ [31] AI: Here's how...              │
└─────────────────────────────────────┘

After /memory-force:
┌─────────────────────────────────────┐
│ Context Window (6 messages)         │
├─────────────────────────────────────┤
│ [0] System Prompt                   │
│ [27] AI: Use pytest...              │ ← Last 5
│ [28] User: How do I mock?           │   kept
│ [29] AI: Use unittest.mock...       │
│ [30] User: Show me an example       │
│ [31] AI: Here's how...              │
└─────────────────────────────────────┘

           ↓ Archived to ChromaDB

┌─────────────────────────────────────┐
│ Short-Term Memory (ChromaDB)        │
├─────────────────────────────────────┤
│ Summary: "Discussion about Python   │
│ best practices including PEP8,      │
│ async/await patterns, and testing   │
│ strategies..."                      │
│                                     │
│ Topic: Python programming           │
│ Importance: 0.78                    │
│ Messages: 26 (original indices 1-26)│
│ Timestamp: 2025-11-04 00:15         │
└─────────────────────────────────────┘
```

## Use Case Examples

### 1. Long Debugging Session

**Scenario:** You've been debugging for an hour with 80+ messages in context.

```
You: "I've been debugging this async issue for a while now..."
AI: "Let's review what we've tried so far..."

[Context is getting huge, costs are increasing]

You: /memory-force

✓ Archived 75 messages
  Summary: Extended debugging session for async/await issue...
  Topic: Python async debugging
  
Context window reduced:
  Before: 81 messages
  After: 6 messages (system + 5)

Total memories stored: 8

[Now you can continue with a fresh context]

You: "Based on everything we discussed, what should I try next?"
AI: [Recalls relevant memories from ChromaDB and provides answer]
```

### 2. Topic Switch Mid-Conversation

**Scenario:** You want to change topics but preserve the previous discussion.

```
You: "Thanks for helping with the database design!"
AI: "You're welcome! The normalized schema should work well."

You: /memory-force

✓ Archived 35 messages
  Summary: Database design discussion covering normalization...
  Topic: Database architecture
  
You: "Now let's talk about frontend optimization"
AI: "Sure! What specific aspects are you interested in?"

[Later, you can /memory-search "database design" to recall it]
```

### 3. Before Important Context

**Scenario:** You're about to paste a large code file and want to free up context.

```
You: "I'm about to share a big file, let me archive our chat first"

You: /memory-force

✓ Archived 42 messages
  Context window: 6 messages

You: [pastes 500-line code file]
AI: [Has plenty of context window space to analyze the code]
```

### 4. Cost Optimization

**Scenario:** Reduce token costs by keeping context small.

```
# After every major discussion point
You: "Great, let's move on"

You: /memory-force

✓ Archived 28 messages
  
# Continue with minimal context
# Relevant memories will be recalled automatically when needed
```

## Command Behavior

### Requirements

- **Minimum messages:** 7 total (system + 6 messages) to archive 1 message
- **Memory system:** Must be enabled in `config/settings.yaml`

### What Gets Archived

```python
# Given conversation:
conversation = [
    [0] system_prompt,      # KEPT
    [1] message_1,          # ARCHIVED
    [2] message_2,          # ARCHIVED
    ...
    [n-5] message_n_minus_5,# ARCHIVED
    [n-4] message_n_minus_4,# KEPT
    [n-3] message_n_minus_3,# KEPT
    [n-2] message_n_minus_2,# KEPT
    [n-1] message_n_minus_1,# KEPT
    [n]   message_n         # KEPT
]

# Archives: [1] through [n-5]
# Keeps: [0] + [n-4] through [n]
```

### Summarization

- Uses your configured LLM to create semantic summaries
- Extracts topic/theme automatically
- Calculates importance score
- Stores with timestamp for later recall

### Memory Recall

After archival, memories are automatically recalled when:
- You ask questions related to archived topics
- Semantic similarity detected between your input and archived content
- Relevance score is above threshold (configurable)

## Output Explanation

```
✓ Archived 10 messages                    ← How many removed from context
  Summary: Discussion about...            ← AI-generated summary
  Topic: Python programming               ← Extracted topic
  Memory ID: 2b51ecae...                  ← Unique identifier

Context window reduced:                   
  Before: 16 messages                     ← Original size
  After: 6 messages (system + 5)          ← New size

Total memories stored: 1                  ← Total in ChromaDB
```

## Error Cases

### Not Enough Messages

```
You: /memory-force

[yellow]Not enough messages to archive.[/yellow]
Current: 3 messages (need at least 6 to keep 5)
```

**Solution:** Continue conversation until you have at least 7 messages total.

### Memory System Disabled

```
You: /memory-force

[yellow]Memory system is not enabled[/yellow]
```

**Solution:** Enable memory in `config/settings.yaml`:
```yaml
memory:
  enabled: true
```

## Best Practices

### ✅ Good Uses

1. **Before pasting large content:** Free up context space
2. **After completing a subtask:** Archive and move to next topic
3. **Cost optimization:** Regular archival in long sessions
4. **Topic boundaries:** Clear mental separation between discussions

### ⚠️ Use With Caution

1. **During active debugging:** Wait until issue is resolved
2. **In middle of code review:** Finish reviewing first
3. **When referencing recent messages:** Keep them in context

### ❌ Don't Use

1. **Every message:** Too aggressive, defeats purpose of context
2. **Before getting answer:** Keep question/answer pairs together
3. **With < 10 messages:** Not worth the overhead

## Comparison with Automatic Archival

| Feature | Automatic | `/memory-force` |
|---------|-----------|-----------------|
| Trigger | Context window full (50+ msgs) | Manual command |
| Amount archived | 4 messages at a time | All except last 5 |
| Frequency | As needed | On demand |
| Use case | Normal operation | Aggressive cleanup |

## Example Session

```bash
# Start conversation
You: "What are Python decorators?"
AI: "Decorators are a way to modify functions..."

# Continue discussion (30 messages)
You: "Can you show me a practical example?"
AI: "Here's a caching decorator..."

# Check context size
You: /memory-stats
→ Context window: 31 messages

# Force archive before new topic
You: /memory-force
→ ✓ Archived 26 messages
→ Context: 6 messages

# New topic with fresh context
You: "Now let's discuss REST APIs"
AI: "Sure! REST APIs are..."

# Later, reference old topic
You: "Remember that decorator example?"
AI: [Recalls from memory] "Yes, we discussed caching decorators..."
```

## Technical Details

### Implementation

```python
# Archival process:
1. Extract messages [1] to [len-5]
2. Call LLM to summarize
3. Store summary in ChromaDB with embeddings
4. Delete messages from conversation array
5. Keep: [system_prompt] + [last_5_messages]
```

### Storage

- **Format:** ChromaDB vector database
- **Location:** `~/.vexa/memory/short_term/`
- **Size:** ~50KB per archived chunk
- **Retrieval:** Semantic search via cosine similarity

### Recall Mechanism

When you send a new message after `/memory-force`:
1. Your message is embedded (384-dim vector)
2. ChromaDB searches for similar memories
3. Top-K matches injected into system prompt
4. LLM sees both current context AND relevant memories

---

**Pro Tip:** Combine with `/memory-search` to verify what was archived:
```bash
You: /memory-force
You: /memory-search decorators
→ Found 1 matching memory about Python decorators
```
