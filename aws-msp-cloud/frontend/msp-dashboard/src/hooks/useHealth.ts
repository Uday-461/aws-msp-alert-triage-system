import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/api/client';

export function useServicesHealth(refetchInterval: number = 30000) {
  return useQuery({
    queryKey: ['health', 'services'],
    queryFn: () => apiClient.getServicesHealth(),
    refetchInterval,
    staleTime: refetchInterval - 1000,
  });
}

export function useMLModelsHealth(refetchInterval: number = 30000) {
  return useQuery({
    queryKey: ['health', 'ml-models'],
    queryFn: () => apiClient.getMLModelsHealth(),
    refetchInterval,
    staleTime: refetchInterval - 1000,
  });
}

export function useDatabaseHealth(refetchInterval: number = 60000) {
  return useQuery({
    queryKey: ['health', 'database'],
    queryFn: () => apiClient.getDatabaseHealth(),
    refetchInterval,
    staleTime: refetchInterval - 1000,
  });
}
