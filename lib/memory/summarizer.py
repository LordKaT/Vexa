"""
Conversation summarization for memory archival.
Uses the LLM to create semantic summaries of conversation chunks.
"""

import httpx
from typing import List, Dict, Any, Optional


class ConversationSummarizer:
    """
    Summarizes conversation chunks using the configured LLM.
    
    Extracts:
    - Concise summary of the exchange
    - Primary topic/theme
    - Key points
    """
    
    def __init__(self, app):
        """
        Initialize summarizer with reference to the app for API access.
        
        Args:
            app: VexaApp instance with API configuration
        """
        self.app = app
    
    async def summarize_messages(
        self,
        messages: List[Dict[str, Any]],
        context: str = ""
    ) -> Dict[str, Any]:
        """
        Summarize a chunk of conversation messages.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            context: Optional context about what preceded this chunk
            
        Returns:
            Dictionary with 'summary', 'topic', and 'key_points'
        """
        if not messages:
            return {
                'summary': '',
                'topic': '',
                'key_points': []
            }
        
        # Build a compact representation of the messages
        conversation_text = self._format_messages_for_summary(messages)
        
        # Create summarization prompt
        system_prompt = (
            "You are a memory archivist. Your job is to create concise, "
            "semantic summaries of conversations for later recall. "
            "Focus on key topics, facts, and the emotional tone. "
            "Be brief but capture the essence."
        )
        
        user_prompt = f"""Summarize this conversation exchange in 2-3 sentences:

{conversation_text}

Provide:
1. A brief summary (2-3 sentences)
2. The primary topic (few words)
3. Key points (comma-separated)

Format as:
SUMMARY: <summary>
TOPIC: <topic>
POINTS: <points>"""
        
        # Call the LLM
        try:
            summary_result = await self._call_llm(system_prompt, user_prompt)
            parsed = self._parse_summary_response(summary_result)
            return parsed
        except Exception as e:
            # Fallback to simple extraction if LLM fails
            return self._fallback_summary(messages)
    
    def _format_messages_for_summary(self, messages: List[Dict[str, Any]]) -> str:
        """Format messages into a readable text block."""
        lines = []
        for msg in messages:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            
            # Skip system messages
            if role == 'system':
                continue
            
            # Truncate very long messages
            if len(content) > 500:
                content = content[:497] + "..."
            
            lines.append(f"{role.upper()}: {content}")
        
        return '\n'.join(lines)
    
    async def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """
        Call the configured LLM for summarization.
        
        Args:
            system_prompt: System prompt for the summarization task
            user_prompt: User prompt with the conversation to summarize
            
        Returns:
            The LLM's response text
        """
        url = getattr(self.app, 'api_url', 'http://localhost:7777/v1/chat/completions')
        
        payload = {
            "model": getattr(self.app, 'api_model', 'Vexa'),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.3  # Lower temperature for more focused summaries
        }
        
        timeout = getattr(self.app, 'api_timeout', 120.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
    
    def _parse_summary_response(self, response: str) -> Dict[str, Any]:
        """
        Parse the structured LLM response into components.
        
        Args:
            response: The LLM's formatted response
            
        Returns:
            Dictionary with summary, topic, and key_points
        """
        summary = ""
        topic = ""
        points = []
        
        # Parse the structured response
        for line in response.split('\n'):
            line = line.strip()
            if line.startswith('SUMMARY:'):
                summary = line.replace('SUMMARY:', '').strip()
            elif line.startswith('TOPIC:'):
                topic = line.replace('TOPIC:', '').strip()
            elif line.startswith('POINTS:'):
                points_str = line.replace('POINTS:', '').strip()
                points = [p.strip() for p in points_str.split(',') if p.strip()]
        
        # If parsing failed, use the whole response as summary
        if not summary:
            summary = response.strip()
        
        return {
            'summary': summary,
            'topic': topic,
            'key_points': points
        }
    
    def _fallback_summary(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create a basic summary without LLM (fallback).
        
        Args:
            messages: List of messages to summarize
            
        Returns:
            Basic summary dictionary
        """
        # Count user and assistant messages
        user_msgs = [m for m in messages if m.get('role') == 'user']
        asst_msgs = [m for m in messages if m.get('role') == 'assistant']
        
        # Create basic summary
        summary = f"Exchange of {len(user_msgs)} user messages and {len(asst_msgs)} responses"
        
        # Try to extract topic from first user message
        topic = "general conversation"
        if user_msgs:
            first_msg = user_msgs[0].get('content', '')
            words = first_msg.split()[:10]  # First 10 words
            topic = ' '.join(words) + ('...' if len(words) > 10 else '')
        
        return {
            'summary': summary,
            'topic': topic,
            'key_points': []
        }
    
    def extract_topic(self, messages: List[Dict[str, Any]]) -> str:
        """
        Extract a topic/theme from messages (sync method for quick use).
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            Topic string
        """
        # Simple heuristic: use first meaningful user message
        for msg in messages:
            if msg.get('role') == 'user':
                content = msg.get('content', '').strip()
                if content:
                    # Take first sentence or first 50 chars
                    topic = content.split('.')[0][:50]
                    return topic if topic else "conversation"
        
        return "conversation"
