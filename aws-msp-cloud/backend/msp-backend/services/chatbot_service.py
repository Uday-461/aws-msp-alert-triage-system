import os
import json
import logging
from typing import AsyncGenerator, List, Dict, Optional, Tuple
from datetime import datetime
import httpx
import asyncpg

logger = logging.getLogger(__name__)

class ChatbotService:
    """
    Customer-facing AI chatbot service with OpenRouter integration.
    Provides RAG-enhanced responses for IT support questions.
    """

    def __init__(self, db_pool, rag_service):
        """
        Initialize chatbot service.
        
        Args:
            db_pool: asyncpg connection pool
            rag_service: RAGService instance for knowledge retrieval
        """
        self.db_pool = db_pool
        self.rag_service = rag_service
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY")
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.model = "qwen/qwen-2.5-7b-instruct"
        self.max_context_messages = 10
        
    async def create_conversation(
        self,
        user_id: str,
        openai_key: Optional[str] = None,
        openrouter_key: Optional[str] = None
    ) -> str:
        """Create new conversation and return conversation_id"""
        async with self.db_pool.acquire() as conn:
            conversation_id = await conn.fetchval("""
                INSERT INTO customer.conversations
                (customer_id, openai_api_key, openrouter_api_key, started_at)
                VALUES ($1, $2, $3, NOW())
                RETURNING id
            """, user_id, openai_key, openrouter_key)

        logger.info(f"Created conversation {conversation_id} for user {user_id}")
        return str(conversation_id)
    
    async def save_message(
        self,
        conversation_id: str,
        role: str,
        content: str
    ) -> str:
        """Save message to database"""
        async with self.db_pool.acquire() as conn:
            message_id = await conn.fetchval("""
                INSERT INTO customer.messages
                (conversation_id, role, content, created_at)
                VALUES ($1, $2, $3, NOW())
                RETURNING id
            """, conversation_id, role, content)
        
        return str(message_id)
    
    async def get_conversation_history(
        self,
        conversation_id: str,
        limit: int = 10
    ) -> List[Dict]:
        """Get recent conversation history"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT role, content, created_at
                FROM customer.messages
                WHERE conversation_id = $1
                ORDER BY created_at DESC
                LIMIT $2
            """, conversation_id, limit)
        
        # Reverse to chronological order
        messages = [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
        return messages
    
    async def get_api_keys(self, conversation_id: str) -> Tuple[Optional[str], Optional[str]]:
        """Get user-provided API keys from conversation"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT openai_api_key, openrouter_api_key
                FROM customer.conversations
                WHERE id = $1
            """, conversation_id)
        
        if row:
            return row["openai_api_key"], row["openrouter_api_key"]
        return None, None
    
    def filter_dangerous_content(self, text: str) -> bool:
        """
        Check for dangerous commands or content.
        Returns True if content is safe, False if dangerous.
        """
        dangerous_patterns = [
            "DROP TABLE", "DELETE FROM", "rm -rf",
            "<script>", "eval(", "exec(",
            "; shutdown", "format c:",
            "__import__", "subprocess"
        ]
        
        text_lower = text.lower()
        for pattern in dangerous_patterns:
            if pattern.lower() in text_lower:
                logger.warning(f"Dangerous pattern detected: {pattern}")
                return False
        
        return True
    
    async def stream_response(
        self,
        user_message: str,
        conversation_id: str,
        user_openai_key: Optional[str] = None,
        user_openrouter_key: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream chatbot response using OpenRouter + RAG.
        
        Yields chunks of text as they arrive from OpenRouter API.
        """
        
        # Safety check
        if not self.filter_dangerous_content(user_message):
            yield "⚠️ I detected potentially dangerous content in your message. Please rephrase your question."
            return
        
        try:
            # Get API keys (user-provided overrides defaults)
            db_openai, db_openrouter = await self.get_api_keys(conversation_id)
            openai_key = user_openai_key or db_openai or self.rag_service.openai_api_key
            openrouter_key = user_openrouter_key or db_openrouter or self.openrouter_key
            
            if not openrouter_key:
                yield "❌ No OpenRouter API key configured. Please provide your API key in settings."
                return
            
            # 1. Retrieve relevant KB articles using RAG
            try:
                sources = await self.rag_service.search(
                    query=user_message,
                    top_k=3,
                    user_api_key=openai_key
                )
                
                # Build context from high-similarity sources
                context_parts = []
                for source in sources:
                    if source.get('similarity', 0) > 0.7:
                        context_parts.append(
                            f"**{source['title']}** (Category: {source.get('category', 'General')})\n"
                            f"{source.get('chunk_text', source.get('content', ''))}"
                        )
                
                context = "\n\n---\n\n".join(context_parts) if context_parts else ""
                
            except Exception as e:
                logger.error(f"RAG search failed: {e}")
                context = ""
            
            # 2. Get conversation history
            history = await self.get_conversation_history(conversation_id, self.max_context_messages)
            
            # 3. Build prompt with RAG context
            if context:
                system_prompt = f"""You are a helpful IT support assistant. Use the following knowledge base articles to answer the user's question accurately and helpfully:

{context}

Instructions:
- Provide clear, step-by-step instructions when relevant
- If the knowledge base has the answer, use it to provide an accurate response
- If the knowledge base doesn't cover the question, politely say you don't have that specific information and suggest creating a support ticket
- Be friendly and professional
- Format responses with markdown for readability
- Include links to relevant documentation when available"""
            else:
                system_prompt = """You are a helpful IT support assistant. Answer user questions to the best of your ability.

If you don't know the answer, politely say so and suggest creating a support ticket for personalized help."""
            
            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(history)
            messages.append({"role": "user", "content": user_message})
            
            # 4. Stream response from OpenRouter
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    "POST",
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {openrouter_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://aws-msp.example.com",
                        "X-Title": "AWS MSP Customer Support"
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": True,
                        "max_tokens": 1000,
                        "temperature": 0.7
                    }
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        logger.error(f"OpenRouter API error: {response.status_code} - {error_text}")
                        yield f"❌ API Error: {response.status_code}. Please check your API key."
                        return
                    
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            
                            if data == "[DONE]":
                                break
                            
                            try:
                                chunk = json.loads(data)
                                
                                if "choices" in chunk and len(chunk["choices"]) > 0:
                                    delta = chunk["choices"][0].get("delta", {})
                                    content = delta.get("content", "")
                                    
                                    if content:
                                        yield content
                                        
                            except json.JSONDecodeError:
                                continue
        
        except httpx.TimeoutException:
            logger.error("OpenRouter API timeout")
            yield "\n\n⏱️ Request timed out. Please try again."
        
        except Exception as e:
            logger.error(f"Stream response error: {e}", exc_info=True)
            yield f"\n\n❌ Error: {str(e)}"
    
    async def get_conversations_by_user(self, user_id: str, limit: int = 20) -> List[Dict]:
        """Get user's conversation history"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT
                    id,
                    started_at,
                    ended_at,
                    ticket_created,
                    incident_detected
                FROM customer.conversations
                WHERE customer_id = $1
                ORDER BY started_at DESC
                LIMIT $2
            """, user_id, limit)

        return [dict(r) for r in rows]
    
    async def mark_conversation_ended(self, conversation_id: str):
        """Mark conversation as ended"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE customer.conversations
                SET ended_at = NOW()
                WHERE id = $1
            """, conversation_id)
