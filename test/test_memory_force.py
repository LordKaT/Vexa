"""
Test script for /memory-force command.

Verifies:
1. Archives all messages except last 5
2. Keeps system prompt
3. Updates context window correctly
4. Stores memory in ChromaDB
"""

import sys
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.command_parser import CommandParser
from lib.orchestrator import Orchestrator
from lib.memory import ShortTermMemory, ConversationSummarizer


class MockApp:
    """Mock app with full orchestrator support."""
    def __init__(self):
        self.messages = []
        self.conversation = []
        self.system_prompt = "You are a test assistant."
        self.api_url = "http://localhost:7777/v1/chat/completions"
        self.api_model = "test"
        self.api_timeout = 120.0
        self._workers = []
        
        # Initialize conversation with system prompt + messages
        self.conversation.append({"role": "system", "content": self.system_prompt})
        
        # Add 15 messages (will keep last 5, archive 10)
        for i in range(15):
            role = "user" if i % 2 == 0 else "assistant"
            self.conversation.append({
                "role": role,
                "content": f"Test message {i+1}"
            })
        
        # Initialize orchestrator with memory system
        self.orchestrator = Orchestrator(self, max_conversation=50)
    
    def update_description(self, text: str):
        self.messages.append(text)
        print(f"{text}")
    
    def run_worker(self, coroutine):
        """Mock run_worker that executes async coroutine synchronously."""
        self._workers.append(asyncio.run(coroutine))


def test_memory_force():
    """Test /memory-force command."""
    print("=" * 60)
    print("Testing /memory-force Command")
    print("=" * 60)
    
    app = MockApp()
    parser = CommandParser(app)
    
    # Check initial state
    initial_count = len(app.conversation)
    print(f"\n[Initial State]")
    print(f"  Total messages: {initial_count}")
    print(f"  System prompt: 1")
    print(f"  Conversation messages: {initial_count - 1}")
    
    # Test 1: Not enough messages
    print("\n[Test 1] Testing with insufficient messages...")
    small_app = MockApp()
    small_app.conversation = [
        {"role": "system", "content": "test"},
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"}
    ]
    small_app.orchestrator = Orchestrator(small_app)
    small_parser = CommandParser(small_app)
    
    small_parser.run("/memory-force")
    if "Not enough messages" in small_app.messages[-1]:
        print("  ✓ Correctly rejected insufficient messages")
    else:
        print(f"  ✗ FAIL: {small_app.messages[-1]}")
        return False
    
    # Test 2: Force archive with enough messages
    print("\n[Test 2] Testing force archive...")
    print(f"  Before: {len(app.conversation)} messages")
    
    parser.run("/memory-force")
    
    print(f"  After: {len(app.conversation)} messages")
    
    # Verify results
    expected_after = 6  # system + 5 messages
    if len(app.conversation) != expected_after:
        print(f"  ✗ FAIL: Expected {expected_after} messages, got {len(app.conversation)}")
        return False
    
    print(f"  ✓ Context window reduced to {len(app.conversation)} messages")
    
    # Verify system prompt is still there
    if app.conversation[0]["role"] != "system":
        print(f"  ✗ FAIL: System prompt missing")
        return False
    
    print("  ✓ System prompt preserved")
    
    # Verify we kept the last 5 conversation messages
    # Original last 5 were messages 11-15
    last_msg = app.conversation[-1]["content"]
    if "Test message 15" not in last_msg:
        print(f"  ✗ FAIL: Last message not preserved. Got: {last_msg}")
        return False
    
    print("  ✓ Last 5 messages preserved")
    
    # Check that memory was stored
    stats = app.orchestrator.mem.get_stats()
    if stats['count'] == 0:
        print(f"  ✗ FAIL: No memories stored")
        return False
    
    print(f"  ✓ Memory stored (total: {stats['count']})")
    
    # Test 3: Verify archived messages are searchable
    print("\n[Test 3] Testing memory recall...")
    
    # Search for something from the archived messages
    results = app.orchestrator.mem.search_memories("Test message", limit=3)
    
    if not results:
        print("  ✗ FAIL: No search results")
        return False
    
    print(f"  ✓ Found {len(results)} memories")
    print(f"    First result: {results[0]['summary'][:50]}...")
    
    # Test 4: Verify the command output is informative
    print("\n[Test 4] Testing command output...")
    
    last_output = app.messages[-1]
    required_elements = [
        "Archived",
        "messages",
        "Summary:",
        "Context window reduced:",
        "Before:",
        "After:"
    ]
    
    for element in required_elements:
        if element not in last_output:
            print(f"  ✗ FAIL: Missing '{element}' in output")
            return False
    
    print("  ✓ Output contains all required information")
    
    print("\n" + "=" * 60)
    print("✅ All /memory-force tests passed!")
    print("=" * 60)
    
    # Print sample output
    print("\n[Sample Output]")
    print(last_output)
    
    return True


if __name__ == "__main__":
    try:
        success = test_memory_force()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
