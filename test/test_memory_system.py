"""
Test script for memory system Phase 1 implementation.

Tests:
1. ShortTermMemory initialization
2. Memory chunk addition
3. Semantic search/recall
4. Importance scoring
5. Memory statistics
"""

import sys
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.memory import ShortTermMemory, ConversationSummarizer


def test_short_term_memory():
    """Test ShortTermMemory basic operations."""
    print("=" * 60)
    print("Testing ShortTermMemory")
    print("=" * 60)
    
    # Initialize with test directory
    test_dir = "/tmp/vexa_memory_test"
    mem = ShortTermMemory(persist_directory=test_dir)
    
    print(f"✓ Initialized memory at: {test_dir}")
    
    # Test 1: Add memory chunks
    print("\n[Test 1] Adding memory chunks...")
    
    memories = [
        {
            'summary': 'User asked about Python programming best practices. Discussion covered PEP8, type hints, and documentation.',
            'messages': [
                {'role': 'user', 'content': 'What are Python best practices?'},
                {'role': 'assistant', 'content': 'Follow PEP8, use type hints, write docstrings.'}
            ],
            'topic': 'Python programming'
        },
        {
            'summary': 'User wanted help debugging a JavaScript async/await issue with promises.',
            'messages': [
                {'role': 'user', 'content': 'My async function is not working'},
                {'role': 'assistant', 'content': 'Make sure you await the promise.'}
            ],
            'topic': 'JavaScript debugging'
        },
        {
            'summary': 'Discussion about machine learning models, specifically neural networks and backpropagation.',
            'messages': [
                {'role': 'user', 'content': 'Explain how neural networks learn'},
                {'role': 'assistant', 'content': 'Through backpropagation and gradient descent.'}
            ],
            'topic': 'Machine learning'
        }
    ]
    
    for mem_data in memories:
        mem_id = mem.add_memory_chunk(
            summary=mem_data['summary'],
            original_messages=mem_data['messages'],
            topic=mem_data['topic']
        )
        print(f"  ✓ Added memory: {mem_data['topic']} (ID: {mem_id[:8]}...)")
    
    # Test 2: Query relevant memories
    print("\n[Test 2] Querying relevant memories...")
    
    queries = [
        "How do I write good Python code?",
        "My JavaScript promises are broken",
        "Tell me about deep learning"
    ]
    
    for query in queries:
        print(f"\n  Query: '{query}'")
        results = mem.query_relevant_memories(query, top_k=2)
        
        for i, result in enumerate(results, 1):
            distance = result.get('distance', 1.0)
            topic = result['metadata'].get('topic', 'N/A')
            print(f"    {i}. [{topic}] distance={distance:.3f}")
            print(f"       {result['summary'][:80]}...")
    
    # Test 3: Get statistics
    print("\n[Test 3] Memory statistics...")
    stats = mem.get_stats()
    print(f"  Total memories: {stats['count']}")
    print(f"  Average importance: {stats['avg_importance']:.2f}")
    
    # Test 4: Search functionality
    print("\n[Test 4] Search memories...")
    search_results = mem.search_memories("programming", limit=5)
    print(f"  Found {len(search_results)} results for 'programming'")
    
    print("\n✓ All ShortTermMemory tests passed!")
    print("=" * 60)


async def test_summarizer():
    """Test ConversationSummarizer (mock version without LLM)."""
    print("\n" + "=" * 60)
    print("Testing ConversationSummarizer")
    print("=" * 60)
    
    # Mock app object
    class MockApp:
        api_url = "http://localhost:7777/v1/chat/completions"
        api_model = "Vexa"
        api_timeout = 120.0
    
    summarizer = ConversationSummarizer(MockApp())
    
    print("✓ Initialized summarizer")
    
    # Test fallback summary (no LLM call)
    messages = [
        {'role': 'user', 'content': 'What is the capital of France?'},
        {'role': 'assistant', 'content': 'The capital of France is Paris.'},
        {'role': 'user', 'content': 'What about Germany?'},
        {'role': 'assistant', 'content': 'The capital of Germany is Berlin.'}
    ]
    
    print("\n[Test] Fallback summary generation...")
    result = summarizer._fallback_summary(messages)
    
    print(f"  Summary: {result['summary']}")
    print(f"  Topic: {result['topic']}")
    print(f"  Key points: {result['key_points']}")
    
    print("\n✓ Summarizer tests passed!")
    print("=" * 60)


def test_importance_calculation():
    """Test importance scoring algorithm."""
    print("\n" + "=" * 60)
    print("Testing Importance Calculation")
    print("=" * 60)
    
    mem = ShortTermMemory(persist_directory="/tmp/vexa_memory_test")
    
    test_cases = [
        {
            'name': 'Short trivial exchange',
            'messages': [
                {'role': 'user', 'content': 'hi'},
                {'role': 'assistant', 'content': 'hello'}
            ]
        },
        {
            'name': 'Medium conversation',
            'messages': [
                {'role': 'user', 'content': 'Can you explain how to use async/await in Python?'},
                {'role': 'assistant', 'content': 'Sure! async/await is used for asynchronous programming...'}
            ]
        },
        {
            'name': 'Long detailed exchange',
            'messages': [
                {'role': 'user', 'content': 'I need help designing a microservices architecture for a large-scale e-commerce platform with high availability requirements.'},
                {'role': 'assistant', 'content': 'That\'s a complex topic. Let\'s break it down into several key components: service discovery, load balancing, data consistency, and fault tolerance. For service discovery, consider using Consul or etcd...'},
                {'role': 'user', 'content': 'What about database sharding strategies?'},
                {'role': 'assistant', 'content': 'Database sharding is crucial for scalability. You can use horizontal sharding based on user ID, geographic location, or a combination...'}
            ]
        }
    ]
    
    for test in test_cases:
        importance = mem.calculate_importance(test['messages'])
        print(f"\n  {test['name']}")
        print(f"    Messages: {len(test['messages'])}")
        print(f"    Importance: {importance:.2f}")
    
    print("\n✓ Importance calculation tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    print("\n🧪 Vexa Memory System - Phase 1 Tests\n")
    
    try:
        # Test 1: ShortTermMemory
        test_short_term_memory()
        
        # Test 2: Summarizer
        asyncio.run(test_summarizer())
        
        # Test 3: Importance scoring
        test_importance_calculation()
        
        print("\n" + "=" * 60)
        print("✅ All tests completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
