import { useClients } from '@/hooks/useClients';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

export function ClientList() {
  const { data, isLoading, error } = useClients();

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Monitored Clients</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-24 bg-muted/50 animate-pulse rounded"></div>
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
          <CardTitle>Monitored Clients</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-destructive">Error loading clients: {error.message}</p>
        </CardContent>
      </Card>
    );
  }

  if (!data) return null;

  const getTierColor = (tier: string) => {
    switch (tier.toLowerCase()) {
      case 'premium':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/50';
      case 'standard':
        return 'bg-blue-500/20 text-blue-400 border-blue-500/50';
      default:
        return 'bg-gray-500/20 text-gray-400 border-gray-500/50';
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Monitored Clients ({data.total_count})</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {/* CRITICAL: Every client MUST have key={client.id} */}
          {data.clients.map((client) => (
            <div
              key={client.id}
              className="border border-border rounded-lg p-4 hover:bg-muted/50 transition-colors"
            >
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="font-semibold">{client.name}</h3>
                  <Badge variant="outline" className={getTierColor(client.tier)}>
                    {client.tier}
                  </Badge>
                </div>
                <div className="text-right text-xs text-muted-foreground">
                  {client.active_assets} assets
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div>
                  <div className="text-muted-foreground">Total (24h)</div>
                  <div className="font-medium">{client.total_alerts_24h}</div>
                </div>
                <div>
                  <div className="text-muted-foreground">Suppressed</div>
                  <div className="font-medium text-green-400">{client.suppressed_alerts_24h}</div>
                </div>
                <div>
                  <div className="text-muted-foreground">Escalated</div>
                  <div className="font-medium text-red-400">{client.escalated_alerts_24h}</div>
                </div>
                <div>
                  <div className="text-muted-foreground">Critical</div>
                  <div className="font-medium text-orange-400">{client.critical_alerts_24h}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
