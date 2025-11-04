"""
Test script for /memory-preview command.

Verifies:
1. Shows recalled memories for a query
2. Displays relevance levels
3. Shows how memories would appear in system prompt
"""

import sys
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.command_parser import CommandParser
from lib.orchestrator import Orchestrator
from lib.memory import ShortTermMemory


class MockApp:
    """Mock app with orchestrator and some stored memories."""
    def __init__(self):
        self.messages = []
        self.conversation = [{"role": "system", "content": "You are a test assistant."}]
        self.system_prompt = "You are a test assistant."
        self.api_url = "http://localhost:7777/v1/chat/completions"
        self.api_model = "test"
        self.api_timeout = 120.0
        self.orchestrator = Orchestrator(self, max_conversation=50)
    
    def update_description(self, text: str):
        self.messages.append(text)
        print(f"{text}\n")


def test_memory_preview():
    """Test /memory-preview command."""
    print("=" * 60)
    print("Testing /memory-preview Command")
    print("=" * 60)
    
    app = MockApp()
    parser = CommandParser(app)
    
    # Add some test memories
    print("\n[Setup] Adding test memories...")
    
    memories = [
        {
            'summary': 'Discussion about Python best practices including PEP8, type hints, and documentation.',
            'messages': [
                {'role': 'user', 'content': 'What are Python best practices?'},
                {'role': 'assistant', 'content': 'Follow PEP8, use type hints, write docstrings.'}
            ],
            'topic': 'Python programming'
        },
        {
            'summary': 'User asked about JavaScript async/await and promises.',
            'messages': [
                {'role': 'user', 'content': 'How do I use async/await?'},
                {'role': 'assistant', 'content': 'Use async functions and await promises.'}
            ],
            'topic': 'JavaScript'
        }
    ]
    
    for mem_data in memories:
        app.orchestrator.mem.add_memory_chunk(
            summary=mem_data['summary'],
            original_messages=mem_data['messages'],
            topic=mem_data['topic']
        )
    
    print(f"  ✓ Added {len(memories)} test memories\n")
    
    # Test 1: Preview with no args (default query)
    print("[Test 1] Preview with default query...")
    parser.run("/memory-preview")
    
    if not app.messages:
        print("  ✗ FAIL: No output")
        return False
    
    last_output = app.messages[-1]
    
    # Check for required elements
    required_elements = [
        "Memory Preview",
        "Found",
        "relevant memories",
        "How this would appear in system prompt",
        "Recalled from past conversations"
    ]
    
    for element in required_elements:
        if element not in last_output:
            print(f"  ✗ FAIL: Missing '{element}' in output")
            return False
    
    print("  ✓ Default preview working")
    
    # Test 2: Preview with specific query
    print("\n[Test 2] Preview with specific query: 'Python'...")
    parser.run("/memory-preview Python programming")
    
    last_output = app.messages[-1]
    
    if "Python" not in last_output or "Memory Preview" not in last_output:
        print(f"  ✗ FAIL: Query not reflected in output")
        return False
    
    print("  ✓ Specific query preview working")
    
    # Test 3: Check relevance indicators
    print("\n[Test 3] Checking relevance indicators...")
    
    # Should have relevance levels (high/medium/low)
    has_relevance = any(level in last_output for level in ["[high]", "[medium]", "[low]"])
    
    if not has_relevance:
        print(f"  ✗ FAIL: No relevance indicators found")
        return False
    
    print("  ✓ Relevance indicators present")
    
    # Test 4: Check system prompt preview
    print("\n[Test 4] Checking system prompt preview...")
    
    if "Recalled from past conversations" not in last_output:
        print(f"  ✗ FAIL: System prompt preview not shown")
        return False
    
    print("✓ System prompt preview shown")
    
    # Test 5: No memories case
    print("\n[Test 5] Testing with query that has no matches...")
    
    # Clear memories
    app.orchestrator.mem.clear_all()
    parser.run("/memory-preview nonexistent topic xyz")
    
    last_output = app.messages[-1]
    
    if "No memories found" not in last_output:
        print(f"  ✗ FAIL: Should show 'No memories found'")
        return False
    
    print("  ✓ No matches case handled correctly")
    
    print("\n" + "=" * 60)
    print("✅ All /memory-preview tests passed!")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    try:
        success = test_memory_preview()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
