import { useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useAlerts } from '@/hooks/useAlerts';
import { formatDistanceToNow } from 'date-fns';
import { Activity } from 'lucide-react';
import type { Alert } from '@/types/api';

const MAX_FEED_ITEMS = 20;

export function LiveAlertFeed() {
  const { data, isLoading } = useAlerts({ page_size: 50 });
  const feedRef = useRef<HTMLDivElement>(null);

  const alerts = data?.alerts || [];

  // Auto-scroll to bottom when new alert arrives
  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight;
    }
  }, [alerts]);

  // Show only the most recent alerts
  const recentAlerts = alerts.slice(-MAX_FEED_ITEMS);
  const connected = !isLoading;

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

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="w-5 h-5 text-blue-500" />
            <CardTitle>Live Alert Feed</CardTitle>
          </div>
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500 animate-pulse' : 'bg-gray-500'}`} />
            <span className="text-xs text-muted-foreground">
              {connected ? 'Connected' : 'Loading...'}
            </span>
            <Badge variant="outline" className="text-xs">
              {alerts.length} total
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading && (
          <div className="text-center py-8 text-muted-foreground">
            <Activity className="w-12 h-12 mx-auto mb-2 text-gray-500 animate-spin" />
            <p>Loading alerts...</p>
          </div>
        )}

        {!isLoading && alerts.length === 0 && (
          <div className="text-center py-8 text-muted-foreground">
            <Activity className="w-12 h-12 mx-auto mb-2 text-gray-500" />
            <p>No alerts yet</p>
            <p className="text-xs mt-1">Start the demo to generate alerts</p>
          </div>
        )}

        {!isLoading && recentAlerts.length > 0 && (
          <div
            ref={feedRef}
            className="space-y-2 max-h-[500px] overflow-y-auto scrollbar-thin scrollbar-thumb-border scrollbar-track-background pr-2"
          >
            {recentAlerts.map((alert: Alert, index: number) => (
              <div
                key={`${alert.id}-${index}`}
                className="border border-border rounded-lg p-3 hover:bg-muted/30 transition-all animate-in fade-in slide-in-from-top-2 duration-300"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                      <Badge variant="outline" className={`${getStatusColor(alert.status)} text-xs`}>
                        {alert.status}
                      </Badge>
                      <Badge variant="outline" className={`${getSeverityColor(alert.severity)} text-xs`}>
                        {alert.severity}
                      </Badge>
                      {alert.ml_classification && (
                        <Badge variant="outline" className="text-xs bg-purple-500/20 text-purple-400 border-purple-500/50">
                          {alert.ml_classification}
                        </Badge>
                      )}
                    </div>
                    <p className="text-sm font-medium mb-1 truncate" title={alert.message}>
                      {alert.message}
                    </p>
                    <div className="flex items-center gap-3 text-xs text-muted-foreground flex-wrap">
                      {alert.client_name && (
                        <span className="truncate" title={alert.client_name}>
                          Client: {alert.client_name}
                        </span>
                      )}
                      {alert.asset_name && (
                        <span className="truncate" title={alert.asset_name}>
                          Asset: {alert.asset_name}
                        </span>
                      )}
                      <span className="whitespace-nowrap">
                        {formatDistanceToNow(new Date(alert.created_at), { addSuffix: true })}
                      </span>
                    </div>
                  </div>
                  {alert.ml_confidence && (
                    <div className="text-right shrink-0">
                      <div className="text-xs text-muted-foreground">Confidence</div>
                      <div className="text-sm font-medium">
                        {(alert.ml_confidence * 100).toFixed(0)}%
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
