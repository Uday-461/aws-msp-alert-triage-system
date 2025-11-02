import { useMetrics } from '@/hooks/useMetrics';
import { useDemo } from '@/hooks/useDemo';
import { formatDistanceToNow } from 'date-fns';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { RefreshCw } from 'lucide-react';
import CountUp from 'react-countup';

export function MetricsCards() {
  // Check if demo is running to adjust refresh rate
  const { status: demoStatus } = useDemo();
  const isDemoRunning = demoStatus?.is_running ?? false;

  // Poll every 3 seconds when demo is running, otherwise every 30 seconds
  const refetchInterval = isDemoRunning ? 3000 : 30000;

  const { data: metrics, isLoading, error, refetch, isFetching } = useMetrics(24, refetchInterval);

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[1, 2, 3, 4].map((i) => (
          <Card key={i} className="animate-pulse">
            <CardHeader className="pb-3">
              <div className="h-4 bg-muted rounded w-1/2"></div>
            </CardHeader>
            <CardContent>
              <div className="h-8 bg-muted rounded w-3/4 mb-2"></div>
              <div className="h-3 bg-muted rounded w-1/3"></div>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <Card className="border-destructive">
        <CardContent className="pt-6">
          <p className="text-destructive">Error loading metrics: {error.message}</p>
        </CardContent>
      </Card>
    );
  }

  if (!metrics) return null;

  const cards = [
    {
      label: 'Total Alerts (24h)',
      value: metrics.total_alerts,
      suffix: '',
      decimals: 0,
      subtitle: `${metrics.suppressed_alerts} suppressed`,
      color: 'text-blue-400',
    },
    {
      label: 'Suppression Rate',
      value: metrics.suppression_rate,
      suffix: '%',
      decimals: 1,
      subtitle: `Target: ≥90%`,
      color: metrics.suppression_rate >= 90 ? 'text-green-400' : 'text-yellow-400',
    },
    {
      label: 'Time Saved',
      value: metrics.time_saved_hours,
      suffix: 'h',
      decimals: 1,
      subtitle: `$${metrics.cost_saved_usd.toLocaleString()} saved`,
      color: 'text-purple-400',
    },
    {
      label: 'Annual ROI',
      value: Math.round(metrics.roi_annual_usd / 1000),
      suffix: 'K',
      prefix: '$',
      decimals: 0,
      subtitle: `${metrics.roi_weekly_hours.toFixed(0)}h/week saved`,
      color: 'text-emerald-400',
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">Dashboard Metrics</h2>
        <div className="flex items-center gap-3">
          {metrics.calculated_at && (
            <span className="text-sm text-muted-foreground">
              Updated {formatDistanceToNow(new Date(metrics.calculated_at), { addSuffix: true })}
            </span>
          )}
          {isDemoRunning && (
            <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded-full bg-green-500/10 text-green-600 text-xs font-medium">
              <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
              Live (updates every 3s)
            </span>
          )}
          <Button
            onClick={() => refetch()}
            disabled={isFetching}
            variant="outline"
            size="sm"
            className="gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${isFetching ? 'animate-spin' : ''}`} />
            {isFetching ? 'Refreshing...' : 'Refresh'}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {cards.map((card, index) => (
          <Card key={index}>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {card.label}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-1">
                <p className={`${card.color} text-2xl font-bold`}>
                  {card.prefix}
                  <CountUp
                    end={card.value}
                    decimals={card.decimals}
                    duration={1.5}
                    preserveValue={true}
                    separator=","
                  />
                  {card.suffix}
                </p>
                <p className="text-xs text-muted-foreground">{card.subtitle}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Additional metrics row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Escalation Rate
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-1">
              <p className="text-orange-400 text-2xl font-bold">
                <CountUp
                  end={metrics.escalation_rate}
                  decimals={1}
                  duration={1.5}
                  preserveValue={true}
                />
                %
              </p>
              <p className="text-xs text-muted-foreground">
                {metrics.escalated_alerts} alerts escalated
              </p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Review Queue
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-1">
              <p className="text-yellow-400 text-2xl font-bold">
                <CountUp
                  end={metrics.review_alerts}
                  duration={1.5}
                  preserveValue={true}
                  separator=","
                />
              </p>
              <p className="text-xs text-muted-foreground">Awaiting human review</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              ML Latency
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-1">
              <p className="text-cyan-400 text-2xl font-bold">
                {metrics.avg_ml_latency_ms ? (
                  <>
                    <CountUp
                      end={metrics.avg_ml_latency_ms}
                      decimals={0}
                      duration={1.5}
                      preserveValue={true}
                    />
                    ms
                  </>
                ) : 'N/A'}
              </p>
              <p className="text-xs text-muted-foreground">Average processing time</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
