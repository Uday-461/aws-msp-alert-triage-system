// Severity levels
export type Severity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

// Alert statuses
export type AlertStatus = 'AUTO_SUPPRESS' | 'ESCALATE' | 'REVIEW' | 'pending';

// Metrics API response
export interface MetricsResponse {
  total_alerts: number;
  suppressed_alerts: number;
  escalated_alerts: number;
  review_alerts: number;
  suppression_rate: number;
  escalation_rate: number;
  avg_ml_latency_ms: number | null;
  avg_ml_confidence: number | null;
  alerts_processed_24h: number;
  time_saved_hours: number;
  cost_saved_usd: number;
  roi_annual_usd: number;
  roi_weekly_hours: number;
  category_distribution: Record<string, unknown>;
  calculated_at: string;
  time_range_hours: number;
}

// Alert interface
export interface Alert {
  id: string;
  alert_id: string;
  client_id: string | null;
  client_name: string | null;
  asset_id: string | null;
  asset_name: string | null;
  message: string;
  severity: Severity;
  source: string | null;
  created_at: string;
  status: AlertStatus;
  ml_classification: string | null;
  ml_confidence: number | null;
  ml_action: string | null;
}

// Alert list response
export interface AlertListResponse {
  alerts: Alert[];
  total_count: number;
  page: number;
  page_size: number;
}

// Alert filters
export interface AlertFilters {
  status?: AlertStatus;
  severity?: Severity;
  client_id?: string;
  search?: string;
  page?: number;
  page_size?: number;
}

// Client interface
export interface Client {
  id: string;
  name: string;
  tier: string;
  total_alerts_24h: number;
  suppressed_alerts_24h: number;
  escalated_alerts_24h: number;
  critical_alerts_24h: number;
  active_assets: number;
}

// Client list response
export interface ClientListResponse {
  clients: Client[];
  total_count: number;
}

// WebSocket message types
export type WebSocketMessageType = 'connection_established' | 'alert_update' | 'pong';

export interface WebSocketMessage {
  type: WebSocketMessageType;
  message?: string;
  channel?: string;
  data?: unknown;
}

// Health API types
export type ServiceStatus = 'healthy' | 'degraded' | 'unhealthy' | 'unknown';
export type ServiceType = 'core' | 'infrastructure';

export interface ServiceHealth {
  name: string;
  type: ServiceType;
  status: ServiceStatus;
  port: number | null;
  endpoint: string | null;
  response_time_ms: number | null;
  error: string | null;
}

export interface ServicesHealthResponse {
  services: ServiceHealth[];
  total: number;
  healthy: number;
  degraded: number;
  unhealthy: number;
  checked_at: string;
}

export interface MLModelStats {
  tier: number;
  model_name: string;
  total_processed: number;
  avg_latency_ms: number | null;
  min_latency_ms: number | null;
  max_latency_ms: number | null;
  accuracy_pct: number | null;
  last_processed: string | null;
}

export interface MLModelsHealthResponse {
  models: MLModelStats[];
  total_classifications: number;
  avg_pipeline_latency_ms: number | null;
  checked_at: string;
}

export interface TableStats {
  schema_name: string;
  table_name: string;
  row_count: number;
  last_modified: string | null;
}

export interface DatabaseHealthResponse {
  schemas: Record<string, number>;
  tables: TableStats[];
  total_records: number;
  checked_at: string;
}

// Analytics API types
export type TimeRange = '1h' | '6h' | '24h' | '3d';

export interface TimeSeriesPoint {
  timestamp: string;
  total: number;
  suppressed: number;
  escalated: number;
  suppression_rate: number;
}

export interface VolumeResponse {
  data: TimeSeriesPoint[];
  time_range: string;
  total_points: number;
}

export interface ClassificationBreakdown {
  classification: string;
  count: number;
  percentage: number;
  color: string;
}

export interface ClassificationDistributionResponse {
  data: ClassificationBreakdown[];
  total: number;
  time_range: string;
}

export interface LatencyBucket {
  range: string;
  min_ms: number;
  max_ms: number;
  count: number;
  percentage: number;
}

export interface LatencyDistributionResponse {
  data: LatencyBucket[];
  total: number;
  avg_latency_ms: number;
  time_range: string;
}
