import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/api/client';

export function useClients() {
  return useQuery({
    queryKey: ['clients'],
    queryFn: () => apiClient.getClients(),
    staleTime: 60000, // Clients change infrequently, stale after 1 min
  });
}
