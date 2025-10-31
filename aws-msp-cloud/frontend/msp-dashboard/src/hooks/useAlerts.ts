import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import type { AlertFilters } from '@/types/api';

export function useAlerts(filters?: AlertFilters) {
  return useQuery({
    queryKey: ['alerts', filters],
    queryFn: () => apiClient.getAlerts(filters),
    staleTime: 10000, // Consider data stale after 10 seconds
  });
}
