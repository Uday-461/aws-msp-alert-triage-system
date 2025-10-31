import type {
  MetricsResponse,
  AlertListResponse,
  ClientListResponse,
  AlertFilters,
  ServicesHealthResponse,
  MLModelsHealthResponse,
  DatabaseHealthResponse,
  VolumeResponse,
  ClassificationDistributionResponse,
  LatencyDistributionResponse,
  TimeRange
} from '@/types/api';

const API_URL = import.meta.env.VITE_API_URL;

class APIError extends Error {
  constructor(
    message: string,
    public status: number,
    public statusText: string
  ) {
    super(message);
    this.name = 'APIError';
  }
}

class APIClient {
  private async request<T>(endpoint: string): Promise<T> {
    try {
      const response = await fetch(`${API_URL}${endpoint}`);

      if (!response.ok) {
        throw new APIError(
          `API request failed: ${response.statusText}`,
          response.status,
          response.statusText
        );
      }

      const data = await response.json();
      return data as T;
    } catch (error) {
      if (error instanceof APIError) {
        throw error;
      }
      throw new APIError(
        `Network error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        0,
        'Network Error'
      );
    }
  }

  async getMetrics(hours: number = 24): Promise<MetricsResponse> {
    return this.request<MetricsResponse>(`/api/metrics?hours=${hours}`);
  }

  async getAlerts(filters?: AlertFilters): Promise<AlertListResponse> {
    const params = new URLSearchParams();

    if (filters?.status) params.append('status', filters.status);
    if (filters?.severity) params.append('severity', filters.severity);
    if (filters?.client_id) params.append('client_id', filters.client_id);
    if (filters?.search) params.append('search', filters.search);
    if (filters?.page) params.append('page', filters.page.toString());
    if (filters?.page_size) params.append('page_size', filters.page_size.toString());

    const queryString = params.toString();
    const endpoint = `/api/alerts${queryString ? `?${queryString}` : ''}`;

    return this.request<AlertListResponse>(endpoint);
  }

  async getClients(): Promise<ClientListResponse> {
    return this.request<ClientListResponse>('/api/clients');
  }

  async getServicesHealth(): Promise<ServicesHealthResponse> {
    return this.request<ServicesHealthResponse>('/api/health/services');
  }

  async getMLModelsHealth(): Promise<MLModelsHealthResponse> {
    return this.request<MLModelsHealthResponse>('/api/health/ml-models');
  }

  async getDatabaseHealth(): Promise<DatabaseHealthResponse> {
    return this.request<DatabaseHealthResponse>('/api/health/database');
  }

  async getAlertVolume(timeRange: TimeRange = '24h'): Promise<VolumeResponse> {
    return this.request<VolumeResponse>(`/api/analytics/volume?time_range=${timeRange}`);
  }

  async getClassificationDistribution(timeRange: TimeRange = '24h'): Promise<ClassificationDistributionResponse> {
    return this.request<ClassificationDistributionResponse>(`/api/analytics/classification-distribution?time_range=${timeRange}`);
  }

  async getLatencyDistribution(timeRange: TimeRange = '24h'): Promise<LatencyDistributionResponse> {
    return this.request<LatencyDistributionResponse>(`/api/analytics/latency-distribution?time_range=${timeRange}`);
  }
}

export const apiClient = new APIClient();
