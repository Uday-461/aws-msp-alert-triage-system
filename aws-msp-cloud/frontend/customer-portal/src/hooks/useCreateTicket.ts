import { useState, useCallback } from 'react';

export interface CreateTicketRequest {
  customer_id: string;
  subject: string;
  description: string;
  priority: 'low' | 'medium' | 'high';
  conversation_id?: string;
}

export interface CreateTicketResponse {
  id: string;
  ticket_number: string;
  customer_id: string;
  subject: string;
  description: string;
  status: string;
  priority: string;
  created_at: string;
}

export const useCreateTicket = () => {
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createdTicket, setCreatedTicket] = useState<CreateTicketResponse | null>(null);

  const createTicket = useCallback(async (request: CreateTicketRequest) => {
    setIsCreating(true);
    setError(null);
    setCreatedTicket(null);

    try {
      const response = await fetch('/api/tickets', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      const ticket: CreateTicketResponse = await response.json();
      setCreatedTicket(ticket);
      return ticket;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to create ticket';
      setError(errorMessage);
      throw err;
    } finally {
      setIsCreating(false);
    }
  }, []);

  const reset = useCallback(() => {
    setError(null);
    setCreatedTicket(null);
  }, []);

  return {
    createTicket,
    isCreating,
    error,
    createdTicket,
    reset,
  };
};
