import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface DemoStatus {
  is_running: boolean;
  start_time: string | null;
  elapsed_seconds: number | null;
  alerts_sent: number;
  rate_per_minute: number;
  estimated_alerts_processed: number;
}

export interface StartDemoRequest {
  rate_per_minute: number;
  duration_minutes?: number;
}

// Fetch demo status
async function fetchDemoStatus(): Promise<DemoStatus> {
  const response = await fetch(`${API_URL}/api/demo/status`);
  if (!response.ok) {
    throw new Error('Failed to fetch demo status');
  }
  return response.json();
}

// Start demo
async function startDemo(request: StartDemoRequest): Promise<void> {
  const response = await fetch(`${API_URL}/api/demo/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to start demo');
  }
}

// Pause demo
async function pauseDemo(): Promise<void> {
  const response = await fetch(`${API_URL}/api/demo/pause`, {
    method: 'POST',
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to pause demo');
  }
}

// Reset demo
async function resetDemo(): Promise<void> {
  const response = await fetch(`${API_URL}/api/demo/reset`, {
    method: 'POST',
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to reset demo');
  }
}

export function useDemo() {
  const queryClient = useQueryClient();

  // Poll demo status every 1 second when running, every 5 seconds when idle
  const { data: status, isLoading, error } = useQuery<DemoStatus>({
    queryKey: ['demoStatus'],
    queryFn: fetchDemoStatus,
    refetchInterval: (query) => {
      const data = query.state.data as DemoStatus | undefined;
      return data?.is_running ? 1000 : 5000; // Poll every 1s when running, 5s when idle
    },
  });

  // Start mutation
  const startMutation = useMutation({
    mutationFn: startDemo,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['demoStatus'] });
      queryClient.invalidateQueries({ queryKey: ['metrics'] });
    },
    onError: (error: any) => {
      // If already running, just refresh status to sync state
      if (error.message && error.message.includes('already active')) {
        console.log('Demo already running, refreshing status...');
        queryClient.invalidateQueries({ queryKey: ['demoStatus'] });
      }
    },
  });

  // Pause mutation
  const pauseMutation = useMutation({
    mutationFn: pauseDemo,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['demoStatus'] });
    },
  });

  // Reset mutation
  const resetMutation = useMutation({
    mutationFn: resetDemo,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['demoStatus'] });
      queryClient.invalidateQueries({ queryKey: ['metrics'] });
    },
  });

  return {
    status,
    isLoading,
    error,
    startDemo: startMutation.mutate,
    pauseDemo: pauseMutation.mutate,
    resetDemo: resetMutation.mutate,
    isStarting: startMutation.isPending,
    isPausing: pauseMutation.isPending,
    isResetting: resetMutation.isPending,
  };
}
