import { useState, useEffect, useCallback } from 'react';
import type { Ticket } from '../types';

// Get customer ID from localStorage (same as useChat)
const getCustomerId = (): string => {
  const stored = localStorage.getItem('user_id');
  if (stored) return stored;

  const newId = crypto.randomUUID();
  localStorage.setItem('user_id', newId);
  return newId;
};

export const useCustomerTickets = () => {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const customerId = getCustomerId();

  const fetchTickets = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/tickets?customer_id=${customerId}&limit=50`);

      if (!response.ok) {
        throw new Error(`Failed to fetch tickets: ${response.status}`);
      }

      const data = await response.json();

      // Sort tickets by created_at (newest first)
      const sortedTickets = (data.tickets || []).sort(
        (a: Ticket, b: Ticket) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );

      setTickets(sortedTickets);
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('An unknown error occurred');
      }
      setTickets([]);
    } finally {
      setIsLoading(false);
    }
  }, [customerId]);

  useEffect(() => {
    fetchTickets();
  }, [fetchTickets]);

  const refreshTickets = useCallback(() => {
    fetchTickets();
  }, [fetchTickets]);

  return {
    tickets,
    isLoading,
    error,
    customerId,
    refreshTickets,
  };
};
