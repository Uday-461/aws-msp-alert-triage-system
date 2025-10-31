import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import type { TimeRange } from '@/types/api';

export function useAlertVolume(timeRange: TimeRange = '24h', enabled: boolean = true) {
  return useQuery({
    queryKey: ['analytics', 'volume', timeRange],
    queryFn: () => apiClient.getAlertVolume(timeRange),
    enabled,
    staleTime: 60000, // 1 minute
    refetchInterval: 60000, // Refetch every minute
  });
}

export function useClassificationDistribution(timeRange: TimeRange = '24h', enabled: boolean = true) {
  return useQuery({
    queryKey: ['analytics', 'classification', timeRange],
    queryFn: () => apiClient.getClassificationDistribution(timeRange),
    enabled,
    staleTime: 60000,
    refetchInterval: 60000,
  });
}

export function useLatencyDistribution(timeRange: TimeRange = '24h', enabled: boolean = true) {
  return useQuery({
    queryKey: ['analytics', 'latency', timeRange],
    queryFn: () => apiClient.getLatencyDistribution(timeRange),
    enabled,
    staleTime: 60000,
    refetchInterval: 60000,
  });
}
