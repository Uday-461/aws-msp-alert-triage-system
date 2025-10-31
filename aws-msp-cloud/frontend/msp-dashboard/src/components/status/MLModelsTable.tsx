import { useMLModelsHealth } from '@/hooks/useHealth';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { RefreshCw, XCircle, Activity, Zap, Brain } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

const tierIcons = {
  1: { icon: Zap, color: 'text-blue-600', label: 'Tier 1' },
  2: { icon: Activity, color: 'text-purple-600', label: 'Tier 2' },
  3: { icon: Brain, color: 'text-indigo-600', label: 'Tier 3' },
} as const;

export function MLModelsTable() {
  const { data, isLoading, error, refetch, isFetching } = useMLModelsHealth(30000);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>ML Pipeline Performance</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <RefreshCw className="w-8 h-8 animate-spin mx-auto text-muted-foreground" />
            <p className="mt-2 text-sm text-muted-foreground">Loading ML model stats...</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>ML Pipeline Performance</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <XCircle className="w-8 h-8 mx-auto text-destructive" />
            <p className="mt-2 text-sm text-destructive">Failed to load ML model stats</p>
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

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>ML Pipeline Performance</CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              {data.total_classifications.toLocaleString()} classifications processed
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-right">
              <div className="text-sm text-muted-foreground">Avg Pipeline Latency</div>
              <div className="text-2xl font-bold">
                {data.avg_pipeline_latency_ms ? `${data.avg_pipeline_latency_ms.toFixed(1)}ms` : 'N/A'}
              </div>
            </div>
            <Button onClick={() => refetch()} disabled={isFetching} variant="outline" size="sm">
              <RefreshCw className={`w-4 h-4 ${isFetching ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {data.models.map((model) => {
            const tierConfig = tierIcons[model.tier as keyof typeof tierIcons];
            const Icon = tierConfig.icon;

            return (
              <div
                key={model.tier}
                className="border rounded-lg p-4 hover:bg-muted/50 transition-colors"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg bg-muted ${tierConfig.color}`}>
                      <Icon className="w-5 h-5" />
                    </div>
                    <div>
                      <h4 className="font-semibold">{model.model_name}</h4>
                      <Badge variant="outline" className="mt-1">
                        {tierConfig.label}
                      </Badge>
                    </div>
                  </div>
                  {model.last_processed && (
                    <span className="text-xs text-muted-foreground">
                      Last: {formatDistanceToNow(new Date(model.last_processed), { addSuffix: true })}
                    </span>
                  )}
                </div>

                <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                  <div>
                    <div className="text-xs text-muted-foreground mb-1">Processed</div>
                    <div className="text-lg font-semibold">
                      {model.total_processed.toLocaleString()}
                    </div>
                  </div>

                  <div>
                    <div className="text-xs text-muted-foreground mb-1">Avg Latency</div>
                    <div className="text-lg font-semibold">
                      {model.avg_latency_ms !== null ? `${model.avg_latency_ms.toFixed(1)}ms` : 'N/A'}
                    </div>
                  </div>

                  <div>
                    <div className="text-xs text-muted-foreground mb-1">Min Latency</div>
                    <div className="text-lg font-semibold">
                      {model.min_latency_ms !== null ? `${model.min_latency_ms.toFixed(1)}ms` : 'N/A'}
                    </div>
                  </div>

                  <div>
                    <div className="text-xs text-muted-foreground mb-1">Max Latency</div>
                    <div className="text-lg font-semibold">
                      {model.max_latency_ms !== null ? `${model.max_latency_ms.toFixed(1)}ms` : 'N/A'}
                    </div>
                  </div>

                  <div>
                    <div className="text-xs text-muted-foreground mb-1">Accuracy</div>
                    <div className="text-lg font-semibold">
                      {model.accuracy_pct !== null ? `${model.accuracy_pct.toFixed(1)}%` : 'N/A'}
                    </div>
                  </div>
                </div>

                {/* Performance indicators */}
                {model.avg_latency_ms !== null && (
                  <div className="mt-3">
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className="text-muted-foreground">Latency Performance</span>
                      <span className="font-medium">
                        {model.avg_latency_ms < 50 ? '🟢 Excellent' :
                         model.avg_latency_ms < 100 ? '🟡 Good' :
                         model.avg_latency_ms < 200 ? '🟠 Fair' : '🔴 Needs Attention'}
                      </span>
                    </div>
                    <div className="h-2 bg-muted rounded-full overflow-hidden">
                      <div
                        className={`h-full transition-all ${
                          model.avg_latency_ms < 50 ? 'bg-green-500' :
                          model.avg_latency_ms < 100 ? 'bg-yellow-500' :
                          model.avg_latency_ms < 200 ? 'bg-orange-500' : 'bg-red-500'
                        }`}
                        style={{
                          width: `${Math.min((model.avg_latency_ms / 200) * 100, 100)}%`
                        }}
                      />
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        <div className="mt-6 p-4 bg-muted rounded-lg">
          <div className="text-sm text-muted-foreground mb-2">Performance Targets</div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
            <div>
              <span className="font-semibold">Tier 1 (Duplicate Detection):</span>
              <span className="ml-2">Target &lt; 10ms</span>
            </div>
            <div>
              <span className="font-semibold">Tier 2 (Classification):</span>
              <span className="ml-2">Target &lt; 50ms</span>
            </div>
            <div>
              <span className="font-semibold">Tier 3 (Contextual Scoring):</span>
              <span className="ml-2">Target &lt; 200ms</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
