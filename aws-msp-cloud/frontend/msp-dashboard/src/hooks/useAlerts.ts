import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import type { AlertFilters } from '@/types/api';

export interface UseAlertsOptions {
  filters?: AlertFilters;
  autoRefresh?: boolean;
  refetchInterval?: number;
}

export function useAlerts(options?: UseAlertsOptions) {
  const { filters, autoRefresh = false, refetchInterval = 5000 } = options || {};

  return useQuery({
    queryKey: ['alerts', filters],
    queryFn: () => apiClient.getAlerts(filters),
    staleTime: 10000, // Consider data stale after 10 seconds
    refetchInterval: autoRefresh ? refetchInterval : false, // Auto-refresh when enabled
  });
}
