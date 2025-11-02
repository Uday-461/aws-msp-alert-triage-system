from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
from datetime import datetime

router = APIRouter(prefix="/api/chat", tags=["chatbot"])
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    user_id: str
    openai_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None


class CreateConversationRequest(BaseModel):
    user_id: str
    openai_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None


class ConversationResponse(BaseModel):
    id: str
    user_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    ticket_created: bool
    incident_detected: bool


@router.post("/message")
async def send_message(request: ChatRequest, req: Request):
    """Stream chatbot response using Server-Sent Events"""
    try:
        chatbot_service = req.app.state.chatbot_service

        # Create conversation if needed
        if not request.conversation_id:
            conversation_id = await chatbot_service.create_conversation(
                request.user_id,
                openai_key=request.openai_api_key,
                openrouter_key=request.openrouter_api_key
            )
        else:
            conversation_id = request.conversation_id

        # Save user message
        await chatbot_service.save_message(conversation_id, "user", request.message)

        # Stream response
        async def generate():
            full_response = ""
            try:
                # Send conversation ID first
                yield f"data: {{'type': 'conversation_id', 'conversation_id': '{conversation_id}'}}\n\n"

                # Stream chatbot response
                async for chunk in chatbot_service.stream_response(
                    request.message,
                    conversation_id,
                    user_openai_key=request.openai_api_key,
                    user_openrouter_key=request.openrouter_api_key
                ):
                    full_response += chunk
                    # Send each chunk as SSE
                    yield f"data: {{'type': 'token', 'content': {repr(chunk)}}}\n\n"

                # Save assistant message
                await chatbot_service.save_message(conversation_id, "assistant", full_response)

                # Send completion event
                yield f"data: {{'type': 'done'}}\n\n"

            except Exception as e:
                logger.error(f"Error in stream: {e}", exc_info=True)
                yield f"data: {{'type': 'error', 'error': {repr(str(e))}}}\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    except Exception as e:
        logger.error(f"Error in send_message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conversations", response_model=Dict[str, str])
async def create_conversation(request: CreateConversationRequest, req: Request):
    """Create a new conversation"""
    try:
        chatbot_service = req.app.state.chatbot_service

        conversation_id = await chatbot_service.create_conversation(
            request.user_id,
            openai_key=request.openai_api_key,
            openrouter_key=request.openrouter_api_key
        )

        return {"conversation_id": conversation_id}

    except Exception as e:
        logger.error(f"Error creating conversation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{user_id}")
async def get_user_conversations(user_id: str, req: Request):
    """Get all conversations for a user"""
    try:
        chatbot_service = req.app.state.chatbot_service

        conversations = await chatbot_service.get_conversations_by_user(user_id)

        return conversations

    except Exception as e:
        logger.error(f"Error getting conversations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: str, req: Request):
    """Get all messages in a conversation"""
    try:
        db_pool = req.app.state.db_pool

        async with db_pool.acquire() as conn:
            messages = await conn.fetch("""
                SELECT
                    id::text as message_id,
                    conversation_id::text,
                    role,
                    content,
                    created_at
                FROM customer.messages
                WHERE conversation_id = $1
                ORDER BY created_at ASC
            """, conversation_id)

        return [dict(m) for m in messages]

    except Exception as e:
        logger.error(f"Error getting messages: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conversations/{conversation_id}/end")
async def end_conversation(conversation_id: str, req: Request):
    """End a conversation"""
    try:
        chatbot_service = req.app.state.chatbot_service

        await chatbot_service.mark_conversation_ended(conversation_id)

        return {"status": "ended", "conversation_id": conversation_id}

    except Exception as e:
        logger.error(f"Error ending conversation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
