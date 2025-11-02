import { useState, useCallback, useRef } from 'react';
import type { Message, ChatRequest, StreamEvent } from '../types';

// Generate or retrieve user ID
const getUserId = (): string => {
  const stored = localStorage.getItem('user_id');
  if (stored) return stored;

  const newId = crypto.randomUUID();
  localStorage.setItem('user_id', newId);
  return newId;
};

export const useChat = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const userId = useRef(getUserId());
  const abortControllerRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(async (
    content: string,
    openaiApiKey?: string,
    openrouterApiKey?: string
  ) => {
    if (!content.trim()) return;

    // Add user message immediately
    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: content.trim(),
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    setError(null);

    // Create assistant message placeholder
    const assistantMessageId = crypto.randomUUID();
    const assistantMessage: Message = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, assistantMessage]);

    try {
      // Create abort controller for this request
      abortControllerRef.current = new AbortController();

      const requestBody: ChatRequest = {
        message: content.trim(),
        customer_name: userId.current,
        conversation_id: conversationId || undefined,
        openai_api_key: openaiApiKey || undefined,
        openrouter_api_key: openrouterApiKey || undefined,
      };

      const response = await fetch('/api/chat/send/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      if (!response.body) {
        throw new Error('Response body is null');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();

        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data: StreamEvent = JSON.parse(line.slice(6));

              if (data.type === 'metadata') {
                // Store conversation ID from metadata event
                setConversationId(data.conversation_id);
              } else if (data.type === 'chunk') {
                // Append chunk to assistant message
                setMessages(prev =>
                  prev.map(msg =>
                    msg.id === assistantMessageId
                      ? { ...msg, content: msg.content + data.content }
                      : msg
                  )
                );
              } else if (data.type === 'complete') {
                // Response complete with sources
                setMessages(prev =>
                  prev.map(msg =>
                    msg.id === assistantMessageId
                      ? { ...msg, sources: data.sources.map(s => s.title) }
                      : msg
                  )
                );
                setIsLoading(false);
              } else if (data.type === 'error') {
                throw new Error(data.message);
              }
            } catch (parseError) {
              console.error('Failed to parse SSE data:', parseError);
            }
          }
        }
      }

      setIsLoading(false);
    } catch (err) {
      if (err instanceof Error) {
        if (err.name === 'AbortError') {
          console.log('Request aborted');
        } else {
          setError(err.message);
          // Remove empty assistant message on error
          setMessages(prev => prev.filter(msg => msg.id !== assistantMessageId));
        }
      }
      setIsLoading(false);
    }
  }, [conversationId]);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setConversationId(null);
    setError(null);
  }, []);

  const cancelRequest = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setIsLoading(false);
    }
  }, []);

  return {
    messages,
    isLoading,
    error,
    conversationId,
    userId: userId.current,
    sendMessage,
    clearMessages,
    cancelRequest,
  };
};
