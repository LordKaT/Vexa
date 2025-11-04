"""
Short-term memory backend using ChromaDB for semantic vector search.
Stores conversation chunks with metadata for recall and archival.
"""

import time
import uuid
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.utils import embedding_functions


class ShortTermMemory:
    """
    Persistent short-term memory using ChromaDB for semantic search.
    
    Stores summarized conversation chunks with metadata including:
    - Timestamp
    - Importance score
    - Topic tags
    - Message count
    - Sentiment
    """
    
    def __init__(
        self,
        persist_directory: str = "~/.vexa/memory/short_term",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        collection_name: str = "conversation_memory"
    ):
        """
        Initialize short-term memory with ChromaDB backend.
        
        Args:
            persist_directory: Path to store ChromaDB data
            embedding_model: Sentence-transformers model for embeddings
            collection_name: Name of the ChromaDB collection
        """
        # Expand user path and create directory
        self.persist_directory = Path(persist_directory).expanduser()
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path=str(self.persist_directory))
        
        # Set up embedding function
        self.embedder = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=embedding_model
        )
        
        # Get or create collection
        try:
            self.collection = self.client.get_collection(
                name=collection_name,
                embedding_function=self.embedder
            )
        except Exception:
            self.collection = self.client.create_collection(
                name=collection_name,
                embedding_function=self.embedder,
                metadata={"hnsw:space": "cosine"}  # Use cosine similarity
            )
    
    def add_memory_chunk(
        self,
        summary: str,
        original_messages: List[Dict[str, Any]],
        topic: str = "",
        importance: Optional[float] = None
    ) -> str:
        """
        Add a summarized conversation chunk to memory.
        
        Args:
            summary: The summarized text to store
            original_messages: Original messages that were summarized
            topic: Extracted topic/theme
            importance: Importance score (0.0-1.0), auto-calculated if None
            
        Returns:
            The UUID of the stored memory
        """
        memory_id = uuid.uuid4().hex
        timestamp = time.time()
        
        # Calculate importance if not provided
        if importance is None:
            importance = self.calculate_importance(original_messages)
        
        # Build metadata
        metadata = {
            "timestamp": timestamp,
            "importance": importance,
            "topic": topic,
            "message_count": len(original_messages),
            "conversation_range": f"{len(original_messages)} messages"
        }
        
        # Add to ChromaDB
        self.collection.add(
            documents=[summary],
            ids=[memory_id],
            metadatas=[metadata]
        )
        
        return memory_id
    
    def query_relevant_memories(
        self,
        query_text: str,
        top_k: int = 5,
        time_filter: Optional[Dict[str, float]] = None,
        importance_threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Query for semantically relevant memories.
        
        Args:
            query_text: Text to search for (typically latest user input)
            top_k: Number of results to return
            time_filter: Optional dict with 'after' and/or 'before' timestamps
            importance_threshold: Minimum importance score to include
            
        Returns:
            List of memory dictionaries with 'id', 'summary', 'metadata', 'distance'
        """
        # Build where clause for filtering
        where = {}
        if importance_threshold > 0:
            where["importance"] = {"$gte": importance_threshold}
        
        # Query ChromaDB
        results = self.collection.query(
            query_texts=[query_text],
            n_results=top_k,
            where=where if where else None
        )
        
        # Format results
        memories = []
        if results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                memory = {
                    'id': results['ids'][0][i],
                    'summary': doc,
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if results['distances'] else None
                }
                
                # Apply time filter if specified
                if time_filter:
                    mem_time = memory['metadata'].get('timestamp', 0)
                    if 'after' in time_filter and mem_time < time_filter['after']:
                        continue
                    if 'before' in time_filter and mem_time > time_filter['before']:
                        continue
                
                memories.append(memory)
        
        return memories
    
    def get_recent_memories(self, n: int = 10) -> List[Dict[str, Any]]:
        """
        Get the N most recent memories (by timestamp).
        
        Args:
            n: Number of recent memories to retrieve
            
        Returns:
            List of memory dictionaries sorted by timestamp (newest first)
        """
        # Get all memories (ChromaDB doesn't have native time-based sorting)
        results = self.collection.get()
        
        if not results['documents']:
            return []
        
        # Combine into memory objects
        memories = []
        for i in range(len(results['documents'])):
            memories.append({
                'id': results['ids'][i],
                'summary': results['documents'][i],
                'metadata': results['metadatas'][i]
            })
        
        # Sort by timestamp and return top N
        memories.sort(key=lambda x: x['metadata'].get('timestamp', 0), reverse=True)
        return memories[:n]
    
    def calculate_importance(self, messages: List[Dict[str, Any]]) -> float:
        """
        Calculate importance score for a set of messages.
        
        Multi-factor calculation based on:
        - Message length (longer = more substantial)
        - Message count
        - Character variety (more unique = more information-dense)
        
        Args:
            messages: List of message dictionaries with 'content' field
            
        Returns:
            Importance score between 0.0 and 1.0
        """
        if not messages:
            return 0.3
        
        score = 0.5  # baseline
        
        # Length factor (diminishing returns)
        total_length = sum(len(m.get('content', '')) for m in messages)
        avg_length = total_length / len(messages)
        score += min(avg_length / 1000, 0.2)
        
        # Message count factor (more back-and-forth = more substantial)
        message_bonus = min(len(messages) * 0.02, 0.15)
        score += message_bonus
        
        # Character variety (higher entropy = more information)
        if total_length > 0:
            combined_text = ' '.join(m.get('content', '') for m in messages)
            unique_chars = len(set(combined_text.lower()))
            variety_score = min(unique_chars / 50, 0.15)
            score += variety_score
        
        return min(score, 1.0)
    
    def cleanup_old_memories(self, days_threshold: int = 30) -> int:
        """
        Remove memories older than the specified threshold.
        
        Args:
            days_threshold: Delete memories older than this many days
            
        Returns:
            Number of memories deleted
        """
        cutoff_timestamp = time.time() - (days_threshold * 86400)
        
        # Get all memories
        results = self.collection.get()
        
        if not results['ids']:
            return 0
        
        # Find IDs to delete
        ids_to_delete = []
        for i, metadata in enumerate(results['metadatas']):
            if metadata.get('timestamp', 0) < cutoff_timestamp:
                ids_to_delete.append(results['ids'][i])
        
        # Delete if any found
        if ids_to_delete:
            self.collection.delete(ids=ids_to_delete)
        
        return len(ids_to_delete)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the memory collection.
        
        Returns:
            Dictionary with count, avg_importance, oldest, newest timestamps
        """
        results = self.collection.get()
        
        if not results['ids']:
            return {
                'count': 0,
                'avg_importance': 0.0,
                'oldest': None,
                'newest': None
            }
        
        timestamps = [m.get('timestamp', 0) for m in results['metadatas']]
        importances = [m.get('importance', 0.5) for m in results['metadatas']]
        
        return {
            'count': len(results['ids']),
            'avg_importance': sum(importances) / len(importances) if importances else 0.0,
            'oldest': min(timestamps) if timestamps else None,
            'newest': max(timestamps) if timestamps else None
        }
    
    def clear_all(self) -> int:
        """
        Clear all memories from the collection.
        
        Returns:
            Number of memories deleted
        """
        results = self.collection.get()
        count = len(results['ids'])
        
        if count > 0:
            self.collection.delete(ids=results['ids'])
        
        return count
    
    def search_memories(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search memories with a text query (for user-facing search).
        
        Args:
            query: Search query text
            limit: Maximum number of results
            
        Returns:
            List of matching memories with metadata
        """
        return self.query_relevant_memories(query, top_k=limit)
