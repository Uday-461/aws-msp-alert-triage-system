export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  sources?: string[];
}

export interface Conversation {
  id: string;
  user_id: string;
  created_at: Date;
  messages: Message[];
}

export interface ChatRequest {
  message: string;
  customer_name?: string;
  customer_email?: string;
  conversation_id?: string;
  openai_api_key?: string;
  openrouter_api_key?: string;
}

export interface StreamToken {
  type: 'chunk';
  content: string;
}

export interface StreamMetadata {
  type: 'metadata';
  conversation_id: string;
}

export interface StreamComplete {
  type: 'complete';
  confidence: number;
  sources: Array<{
    id: string;
    title: string;
    category: string;
    similarity: number;
  }>;
}

export interface StreamError {
  type: 'error';
  message: string;
}

export type StreamEvent = StreamToken | StreamMetadata | StreamComplete | StreamError;
