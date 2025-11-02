import { useServicesHealth } from '@/hooks/useHealth';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { RefreshCw, CheckCircle2, AlertCircle, XCircle, HelpCircle } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import type { ServiceStatus } from '@/types/api';

const statusConfig = {
  healthy: {
    icon: CheckCircle2,
    color: 'text-green-600',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200',
    label: 'Healthy',
  },
  degraded: {
    icon: AlertCircle,
    color: 'text-yellow-600',
    bgColor: 'bg-yellow-50',
    borderColor: 'border-yellow-200',
    label: 'Degraded',
  },
  unhealthy: {
    icon: XCircle,
    color: 'text-red-600',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200',
    label: 'Unhealthy',
  },
  unknown: {
    icon: HelpCircle,
    color: 'text-gray-600',
    bgColor: 'bg-gray-50',
    borderColor: 'border-gray-200',
    label: 'Unknown',
  },
} as const;

export function ServiceHealthGrid() {
  const { data, isLoading, error, refetch, isFetching } = useServicesHealth(30000);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Service Health</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <RefreshCw className="w-8 h-8 animate-spin mx-auto text-muted-foreground" />
            <p className="mt-2 text-sm text-muted-foreground">Loading service health...</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Service Health</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <XCircle className="w-8 h-8 mx-auto text-destructive" />
            <p className="mt-2 text-sm text-destructive">Failed to load service health</p>
            <Button onClick={() => refetch()} variant="outline" size="sm" className="mt-4">
              Try Again
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!data) {
    return null;
  }

  const coreServices = data.services.filter(s => s.type === 'core');
  const infrastructureServices = data.services.filter(s => s.type === 'infrastructure');

  return (
    <div className="space-y-6">
      {/* Summary Stats */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Service Health</h2>
          <p className="text-sm text-muted-foreground">
            Last checked {formatDistanceToNow(new Date(data.checked_at), { addSuffix: true })}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-4 text-sm">
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 bg-green-500 rounded-full" />
              <span>{data.healthy} Healthy</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 bg-yellow-500 rounded-full" />
              <span>{data.degraded} Degraded</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 bg-red-500 rounded-full" />
              <span>{data.unhealthy} Unhealthy</span>
            </div>
          </div>
          <Button onClick={() => refetch()} disabled={isFetching} variant="outline" size="sm">
            <RefreshCw className={`w-4 h-4 ${isFetching ? 'animate-spin' : ''}`} />
            {isFetching ? 'Refreshing...' : 'Refresh'}
          </Button>
        </div>
      </div>

      {/* Core Services */}
      <div>
        <h3 className="text-lg font-semibold mb-3">Core Services</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {coreServices.map((service) => {
            const config = statusConfig[service.status as ServiceStatus];
            const Icon = config.icon;

            return (
              <Card
                key={service.name}
                className={`border-2 ${config.borderColor}`}
              >
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <Icon className={`w-5 h-5 ${config.color}`} />
                        <h4 className="font-semibold">{service.name}</h4>
                      </div>
                      <Badge
                        variant="outline"
                        className={`${config.color} ${config.bgColor} border-0`}
                      >
                        {config.label}
                      </Badge>
                    </div>
                  </div>

                  <div className="mt-3 space-y-1 text-sm">
                    {service.port && (
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Port:</span>
                        <span className="font-mono">{service.port}</span>
                      </div>
                    )}
                    {service.response_time_ms !== null && (
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Response:</span>
                        <span className="font-mono">{service.response_time_ms.toFixed(0)}ms</span>
                      </div>
                    )}
                    {service.endpoint && (
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Endpoint:</span>
                        <span className="font-mono text-xs truncate max-w-[120px]" title={service.endpoint}>
                          {service.endpoint}
                        </span>
                      </div>
                    )}
                    {service.error && (
                      <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700">
                        {service.error}
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>

      {/* Infrastructure Services */}
      <div>
        <h3 className="text-lg font-semibold mb-3">Infrastructure Services</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {infrastructureServices.map((service) => {
            const config = statusConfig[service.status as ServiceStatus];
            const Icon = config.icon;

            return (
              <Card
                key={service.name}
                className={`border-2 ${config.borderColor}`}
              >
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <Icon className={`w-5 h-5 ${config.color}`} />
                        <h4 className="font-semibold">{service.name}</h4>
                      </div>
                      <Badge
                        variant="outline"
                        className={`${config.color} ${config.bgColor} border-0`}
                      >
                        {config.label}
                      </Badge>
                    </div>
                  </div>

                  <div className="mt-3 space-y-1 text-sm">
                    {service.port && (
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Port:</span>
                        <span className="font-mono">{service.port}</span>
                      </div>
                    )}
                    {service.response_time_ms !== null && (
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Response:</span>
                        <span className="font-mono">{service.response_time_ms.toFixed(0)}ms</span>
                      </div>
                    )}
                    {service.endpoint && (
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Endpoint:</span>
                        <span className="font-mono text-xs truncate max-w-[120px]" title={service.endpoint}>
                          {service.endpoint}
                        </span>
                      </div>
                    )}
                    {service.error && (
                      <div className="mt-2 p-2 bg-gray-50 border border-gray-200 rounded text-xs text-gray-700">
                        {service.error}
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>
    </div>
  );
}
