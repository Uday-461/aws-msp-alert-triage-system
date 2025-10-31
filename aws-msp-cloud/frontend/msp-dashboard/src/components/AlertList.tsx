import { useState } from 'react';
import { useAlerts } from '@/hooks/useAlerts';
import { formatDistanceToNow } from 'date-fns';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { AlertFilters } from './AlertFilters';
import type { AlertFilters as AlertFiltersType } from '@/types/api';

export function AlertList() {
  const [filters, setFilters] = useState<AlertFiltersType>({ page: 1, page_size: 50 });
  const { data, isLoading, error } = useAlerts(filters);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'AUTO_SUPPRESS':
        return 'bg-green-500/20 text-green-400 border-green-500/50';
      case 'ESCALATE':
        return 'bg-red-500/20 text-red-400 border-red-500/50';
      case 'REVIEW':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/50';
      default:
        return 'bg-gray-500/20 text-gray-400 border-gray-500/50';
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'CRITICAL':
        return 'bg-red-500/20 text-red-400 border-red-500/50';
      case 'HIGH':
        return 'bg-orange-500/20 text-orange-400 border-orange-500/50';
      case 'MEDIUM':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/50';
      default:
        return 'bg-blue-500/20 text-blue-400 border-blue-500/50';
    }
  };

  const handlePageChange = (newPage: number) => {
    setFilters({ ...filters, page: newPage });
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Alert Management</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-20 bg-muted/50 animate-pulse rounded"></div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Alert Management</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-destructive">Error loading alerts: {error.message}</p>
        </CardContent>
      </Card>
    );
  }

  if (!data) return null;

  const totalPages = Math.ceil(data.total_count / (filters.page_size || 50));

  return (
    <div className="space-y-4">
      <AlertFilters onFiltersChange={(newFilters) => setFilters({ ...filters, ...newFilters, page: 1 })} />

      <Card>
        <CardHeader>
          <CardTitle>
            Alert Management ({data.total_count} total)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {/* CRITICAL: Every alert MUST have key={alert.id} */}
            {data.alerts.map((alert) => (
              <div
                key={alert.id}
                className="border border-border rounded-lg p-4 hover:bg-muted/50 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <Badge variant="outline" className={getStatusColor(alert.status)}>
                        {alert.status}
                      </Badge>
                      <Badge variant="outline" className={getSeverityColor(alert.severity)}>
                        {alert.severity}
                      </Badge>
                      <span className="text-sm text-muted-foreground">{alert.alert_id}</span>
                    </div>
                    <p className="text-sm font-medium mb-1">{alert.message}</p>
                    <div className="flex items-center gap-4 text-xs text-muted-foreground">
                      {alert.client_name && <span>Client: {alert.client_name}</span>}
                      {alert.asset_name && <span>Asset: {alert.asset_name}</span>}
                      <span>
                        {formatDistanceToNow(new Date(alert.created_at), { addSuffix: true })}
                      </span>
                    </div>
                  </div>
                  {alert.ml_confidence && (
                    <div className="text-right">
                      <div className="text-xs text-muted-foreground">ML Confidence</div>
                      <div className="text-sm font-medium">
                        {(alert.ml_confidence * 100).toFixed(1)}%
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-6">
              <Button
                variant="outline"
                size="sm"
                onClick={() => handlePageChange((filters.page || 1) - 1)}
                disabled={(filters.page || 1) <= 1}
              >
                Previous
              </Button>
              <span className="text-sm text-muted-foreground">
                Page {filters.page || 1} of {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handlePageChange((filters.page || 1) + 1)}
                disabled={(filters.page || 1) >= totalPages}
              >
                Next
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
