import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/api/client';

export function useMetrics(hours: number = 24, refetchInterval: number = 30000) {
  return useQuery({
    queryKey: ['metrics', hours],
    queryFn: () => apiClient.getMetrics(hours),
    refetchInterval, // Dynamic refetch interval
    staleTime: Math.min(refetchInterval - 1000, 20000), // Consider data stale slightly before refetch
  });
}
