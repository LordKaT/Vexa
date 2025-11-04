# Memory System Quick Start

## Installation

```bash
cd /home/felicia/Projects/Vexa
source venv/bin/activate
pip install -r requirements.txt
```

## First Run

```bash
python vexa.py
```

The first time ChromaDB initializes, it will download the embedding model (~80MB). This happens once.

## Basic Usage

Just chat normally! The memory system works automatically in the background.

### When Context Window Fills (50 messages)
- Oldest messages are automatically summarized
- Summaries stored in `~/.vexa/memory/short_term/`
- Relevant memories recalled on each new message

### Memory Commands

```bash
# Check memory stats
/memory-stats

# Search your memories
/memory-search Python programming

# Preview what would be recalled
/memory-preview Python

# Force archive all but last 5 messages
/memory-force

# Clear all memories (careful!)
/memory-clear confirm
```

## Configuration

Edit `config/settings.yaml`:

```yaml
memory:
  enabled: true  # Toggle memory system
  
  short_term:
    recall_top_k: 5  # Memories to recall per query
    importance_threshold: 0.3  # Min score to store
```

## Testing

```bash
# Run test suite
python test/test_memory_system.py

# All tests should pass ✅
```

## Storage Location

Memories stored at: `~/.vexa/memory/short_term/`

**Backup:** Just copy this directory
**Reset:** Delete this directory and restart

## How to Know It's Working

1. Have a conversation with 50+ messages
2. Use `/memory-stats` to see stored memories
3. Reference something from early in the conversation
4. Vexa should recall it from memory!

Example:
```
You: "What are the Python best practices?"
Vexa: "Follow PEP8, use type hints..."

[...48 more messages...]

You: "What did we say about Python earlier?"
Vexa: "Earlier we discussed Python best practices including PEP8..."
```

## Troubleshooting

**Memory system not initializing?**
```bash
pip install --upgrade chromadb sentence-transformers
```

**Want to disable it?**
```yaml
# config/settings.yaml
memory:
  enabled: false
```

**Clean slate?**
```bash
rm -rf ~/.vexa/memory/short_term/
```

## Documentation

- **Full Plan:** `docs/memory_system_plan.md`
- **User Guide:** `docs/memory_system_usage.md`
- **Implementation:** `docs/IMPLEMENTATION_SUMMARY.md`

---

**Enjoy your AI with a memory! 🧠✨**
