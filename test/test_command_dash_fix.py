"""
Test that commands with dashes work correctly.
Tests the fix for /memory-stats, /memory-clear, /memory-search
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.command_parser import CommandParser


class MockApp:
    """Mock app for testing."""
    def __init__(self):
        self.messages = []
        self.orchestrator = None
    
    def update_description(self, text: str):
        self.messages.append(text)
        print(f"[APP OUTPUT] {text}")
    
    def handle_ai_prompt(self, text: str):
        self.messages.append(f"Sent to AI: {text}")
        print(f"[SENT TO AI] {text}")


def test_dash_commands():
    """Test that commands with dashes are properly converted."""
    print("=" * 60)
    print("Testing Dash-to-Underscore Command Conversion")
    print("=" * 60)
    
    app = MockApp()
    parser = CommandParser(app)
    
    test_cases = [
        ("/memory-stats", "cmd_memory_stats", True),
        ("/memory-clear", "cmd_memory_clear", True),
        ("/memory-search test", "cmd_memory_search", True),
        ("/help", "cmd_help", True),
        ("/not-a-real-command", None, False),  # Should go to AI
    ]
    
    for cmd, expected_handler, should_be_handled in test_cases:
        print(f"\nTesting: '{cmd}'")
        
        # Get handler name
        cmd_name = cmd.split()[0][1:].replace('-', '_')
        handler = getattr(parser, f"cmd_{cmd_name}", None)
        
        if should_be_handled:
            if handler:
                print(f"  ✓ Handler found: cmd_{cmd_name}")
            else:
                print(f"  ✗ FAIL: Handler not found for cmd_{cmd_name}")
                return False
        else:
            if handler is None:
                print(f"  ✓ No handler (will route to AI)")
            else:
                print(f"  ✗ FAIL: Unexpected handler found")
                return False
    
    # Test actual execution
    print("\n" + "=" * 60)
    print("Testing Actual Command Execution")
    print("=" * 60)
    
    # Clear messages
    app.messages = []
    
    # Test /memory-stats (will fail gracefully since no real orchestrator)
    print("\n1. Testing /memory-stats")
    parser.run("/memory-stats")
    if "Memory system is not enabled" in app.messages[-1]:
        print("  ✓ /memory-stats executed correctly")
    else:
        print(f"  ✗ Unexpected output: {app.messages[-1]}")
        return False
    
    # Test /memory-search without args (will also fail gracefully due to no orchestrator)
    print("\n2. Testing /memory-search (no orchestrator)")
    parser.run("/memory-search")
    if "Memory system is not enabled" in app.messages[-1]:
        print("  ✓ /memory-search executed correctly (no orchestrator)")
    else:
        print(f"  ✗ Unexpected output: {app.messages[-1]}")
        return False
    
    # Test /memory-clear without confirm (will also fail gracefully due to no orchestrator)
    print("\n3. Testing /memory-clear (no orchestrator)")
    parser.run("/memory-clear")
    if "Memory system is not enabled" in app.messages[-1]:
        print("  ✓ /memory-clear executed correctly (no orchestrator)")
    else:
        print(f"  ✗ Unexpected output: {app.messages[-1]}")
        return False
    
    # Test /help still works
    print("\n4. Testing /help (no dash)")
    parser.run("/help")
    if "Available commands" in app.messages[-1]:
        print("  ✓ /help executed correctly")
    else:
        print(f"  ✗ Unexpected output: {app.messages[-1]}")
        return False
    
    # Test non-command goes to AI
    print("\n5. Testing non-command routing to AI")
    parser.run("hello there")
    if "Sent to AI: hello there" in app.messages[-1]:
        print("  ✓ Non-command routed to AI correctly")
    else:
        print(f"  ✗ Unexpected output: {app.messages[-1]}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ All dash conversion tests passed!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    try:
        success = test_dash_commands()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
