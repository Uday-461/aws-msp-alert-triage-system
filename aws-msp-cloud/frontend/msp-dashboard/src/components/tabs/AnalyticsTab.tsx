import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { TimeRangeSelector } from '@/components/analytics/TimeRangeSelector';
import { useAlertVolume, useClassificationDistribution, useLatencyDistribution } from '@/hooks/useAnalytics';
import { RefreshCw } from 'lucide-react';
import { LineChart, Line, AreaChart, Area, PieChart, Pie, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts';
import { format } from 'date-fns';
import type { TimeRange } from '@/types/api';

export function AnalyticsTab() {
  const [timeRange, setTimeRange] = useState<TimeRange>('24h');

  const { data: volumeData, isLoading: volumeLoading } = useAlertVolume(timeRange);
  const { data: classificationData, isLoading: classificationLoading } = useClassificationDistribution(timeRange);
  const { data: latencyData, isLoading: latencyLoading } = useLatencyDistribution(timeRange);

  const isLoading = volumeLoading || classificationLoading || latencyLoading;

  // Format volume data for charts
  const volumeChartData = volumeData?.data.map(point => ({
    time: format(new Date(point.timestamp), 'MMM d, HH:mm'),
    Total: point.total,
    Suppressed: point.suppressed,
    Escalated: point.escalated,
    'Suppression Rate': point.suppression_rate,
  })) || [];

  return (
    <div className="space-y-6">
      {/* Header with Time Range Selector */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold">Analytics Dashboard</h2>
          <p className="text-muted-foreground mt-1">
            Historical data and insights
          </p>
        </div>
        <TimeRangeSelector value={timeRange} onChange={setTimeRange} />
      </div>

      {isLoading && (
        <div className="text-center py-12">
          <RefreshCw className="w-8 h-8 animate-spin mx-auto text-muted-foreground" />
          <p className="mt-2 text-sm text-muted-foreground">Loading analytics...</p>
        </div>
      )}

      {!isLoading && (
        <>
          {/* Alert Volume Chart (Line) */}
          <Card>
            <CardHeader>
              <CardTitle>Alert Volume Over Time</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={volumeChartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="Total" stroke="#8884d8" strokeWidth={2} />
                  <Line type="monotone" dataKey="Suppressed" stroke="#82ca9d" strokeWidth={2} />
                  <Line type="monotone" dataKey="Escalated" stroke="#ffc658" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Suppression Rate Trend (Area) */}
          <Card>
            <CardHeader>
              <CardTitle>Suppression Rate Trend</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={250}>
                <AreaChart data={volumeChartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" />
                  <YAxis domain={[0, 100]} />
                  <Tooltip />
                  <Legend />
                  <Area
                    type="monotone"
                    dataKey="Suppression Rate"
                    stroke="#10b981"
                    fill="#10b981"
                    fillOpacity={0.6}
                  />
                </AreaChart>
              </ResponsiveContainer>
              <div className="mt-4 p-3 bg-muted rounded-lg text-sm">
                <strong>Target:</strong> ≥90% suppression rate (shown as horizontal reference)
              </div>
            </CardContent>
          </Card>

          {/* Charts Row */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Classification Distribution (Pie) */}
            <Card>
              <CardHeader>
                <CardTitle>Classification Distribution</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={(classificationData?.data || []) as any}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={(entry) => `${entry.classification}: ${entry.percentage}%`}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="count"
                    >
                      {(classificationData?.data || []).map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
                <div className="mt-4 grid grid-cols-2 gap-2 text-sm">
                  {classificationData?.data.map((item) => (
                    <div key={item.classification} className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded" style={{ backgroundColor: item.color }} />
                      <span>{item.classification}: {item.count.toLocaleString()}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Latency Distribution (Bar) */}
            <Card>
              <CardHeader>
                <CardTitle>Latency Distribution</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={latencyData?.data || []}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="range" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="count" fill="#8b5cf6" />
                  </BarChart>
                </ResponsiveContainer>
                <div className="mt-4 p-3 bg-muted rounded-lg text-sm">
                  <strong>Average Latency:</strong> {latencyData?.avg_latency_ms.toFixed(1)}ms
                  <span className="ml-4 text-muted-foreground">
                    Total: {latencyData?.total.toLocaleString()} classifications
                  </span>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Summary Statistics */}
          <Card>
            <CardHeader>
              <CardTitle>Summary Statistics</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div>
                  <div className="text-sm text-muted-foreground mb-1">Total Alerts</div>
                  <div className="text-3xl font-bold">{volumeData?.data.reduce((sum, p) => sum + p.total, 0).toLocaleString()}</div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground mb-1">Suppressed</div>
                  <div className="text-3xl font-bold text-green-600">
                    {volumeData?.data.reduce((sum, p) => sum + p.suppressed, 0).toLocaleString()}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground mb-1">Escalated</div>
                  <div className="text-3xl font-bold text-amber-600">
                    {volumeData?.data.reduce((sum, p) => sum + p.escalated, 0).toLocaleString()}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
