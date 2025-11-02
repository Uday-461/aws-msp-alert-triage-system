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
  user_id: string;
  conversation_id?: string;
  openai_api_key?: string;
  openrouter_api_key?: string;
}

export interface StreamToken {
  type: 'token';
  content: string;
}

export interface StreamComplete {
  type: 'done';
  conversation_id: string;
  message_id: string;
}

export interface StreamError {
  type: 'error';
  message: string;
}

export type StreamEvent = StreamToken | StreamComplete | StreamError;
