import { useDatabaseHealth } from '@/hooks/useHealth';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { RefreshCw, XCircle, Database } from 'lucide-react';

const schemaColors = {
  superops: 'bg-blue-100 text-blue-700 border-blue-200',
  customer: 'bg-green-100 text-green-700 border-green-200',
  audit: 'bg-purple-100 text-purple-700 border-purple-200',
  knowledge_base: 'bg-orange-100 text-orange-700 border-orange-200',
} as const;

export function DatabaseStats() {
  const { data, isLoading, error, refetch, isFetching } = useDatabaseHealth(60000);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Database Statistics</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <RefreshCw className="w-8 h-8 animate-spin mx-auto text-muted-foreground" />
            <p className="mt-2 text-sm text-muted-foreground">Loading database stats...</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Database Statistics</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <XCircle className="w-8 h-8 mx-auto text-destructive" />
            <p className="mt-2 text-sm text-destructive">Failed to load database stats</p>
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
            <CardTitle>Database Statistics</CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              {data.total_records.toLocaleString()} total records across {data.tables.length} tables
            </p>
          </div>
          <Button onClick={() => refetch()} disabled={isFetching} variant="outline" size="sm">
            <RefreshCw className={`w-4 h-4 ${isFetching ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {/* Schema Summary */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          {Object.entries(data.schemas).map(([schema, count]) => {
            const colorClass = schemaColors[schema as keyof typeof schemaColors] || 'bg-gray-100 text-gray-700 border-gray-200';

            return (
              <div
                key={schema}
                className={`p-4 rounded-lg border-2 ${colorClass}`}
              >
                <div className="flex items-center gap-2 mb-2">
                  <Database className="w-4 h-4" />
                  <h4 className="font-semibold text-sm">{schema}</h4>
                </div>
                <div className="text-2xl font-bold">{count.toLocaleString()}</div>
                <div className="text-xs opacity-75 mt-1">records</div>
              </div>
            );
          })}
        </div>

        {/* Tables by Schema */}
        <div className="space-y-6">
          {Object.keys(data.schemas).map((schema) => {
            const schemaTables = data.tables.filter(t => t.schema_name === schema);
            const colorClass = schemaColors[schema as keyof typeof schemaColors] || 'bg-gray-100 text-gray-700 border-gray-200';

            if (schemaTables.length === 0) {
              return null;
            }

            return (
              <div key={schema}>
                <h3 className={`text-sm font-semibold mb-3 px-3 py-1.5 inline-block rounded border ${colorClass}`}>
                  {schema} schema ({schemaTables.length} tables)
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {schemaTables.map((table) => (
                    <div
                      key={`${table.schema_name}.${table.table_name}`}
                      className="border rounded-lg p-3 hover:bg-muted/50 transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <h4 className="font-mono text-sm font-semibold truncate">
                          {table.table_name}
                        </h4>
                        <span className="text-xs text-muted-foreground ml-2 whitespace-nowrap">
                          {table.row_count.toLocaleString()} rows
                        </span>
                      </div>

                      {/* Visual representation of row count */}
                      <div className="mt-2">
                        <div className="h-1 bg-muted rounded-full overflow-hidden">
                          <div
                            className="h-full bg-primary transition-all"
                            style={{
                              width: `${Math.min((table.row_count / Math.max(...data.tables.map(t => t.row_count))) * 100, 100)}%`
                            }}
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>

        {/* Empty schemas warning */}
        {Object.entries(data.schemas).some(([_, count]) => count === 0) && (
          <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
            <div className="flex items-start gap-2">
              <XCircle className="w-5 h-5 text-yellow-600 mt-0.5" />
              <div>
                <h4 className="font-semibold text-yellow-900 text-sm">Empty Schemas Detected</h4>
                <p className="text-xs text-yellow-700 mt-1">
                  Some schemas have no data. This may be expected if certain features haven't been used yet.
                </p>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
