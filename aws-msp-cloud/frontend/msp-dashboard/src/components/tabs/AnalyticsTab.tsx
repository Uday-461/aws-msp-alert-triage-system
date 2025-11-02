import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { TimeRangeSelector } from '@/components/analytics/TimeRangeSelector';
import { useAlertVolume, useClassificationDistribution, useLatencyDistribution } from '@/hooks/useAnalytics';
import { RefreshCw, TrendingDown, TrendingUp, AlertCircle, Clock, DollarSign, CheckCircle, XCircle } from 'lucide-react';
import { PieChart, Pie, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts';
import type { TimeRange } from '@/types/api';

export function AnalyticsTab() {
  const [timeRange, setTimeRange] = useState<TimeRange>('24h');

  const { data: volumeData, isLoading: volumeLoading } = useAlertVolume(timeRange);
  const { data: classificationData, isLoading: classificationLoading } = useClassificationDistribution(timeRange);
  const { data: latencyData, isLoading: latencyLoading } = useLatencyDistribution(timeRange);

  const isLoading = volumeLoading || classificationLoading || latencyLoading;

  // Calculate KPI metrics from volume data
  const totalAlerts = volumeData?.data.reduce((sum, p) => sum + p.total, 0) || 0;
  const suppressedAlerts = volumeData?.data.reduce((sum, p) => sum + p.suppressed, 0) || 0;
  const escalatedAlerts = volumeData?.data.reduce((sum, p) => sum + p.escalated, 0) || 0;
  const suppressionRate = totalAlerts > 0 ? (suppressedAlerts / totalAlerts) * 100 : 0;
  const avgLatency = latencyData?.avg_latency_ms || 0;

  // Calculate ROI metrics (based on time saved)
  // Assumption: Each suppressed alert saves 5 minutes of manual work at $75/hr
  const timeSavedMinutes = suppressedAlerts * 5;
  const timeSavedHours = timeSavedMinutes / 60;
  const costSaved = timeSavedHours * 75;

  // Calculate critical vs actionable breakdown
  const criticalAlerts = classificationData?.data.find(d => d.classification === 'CRITICAL')?.count || 0;
  const actionableAlerts = classificationData?.data.find(d => d.classification === 'ACTIONABLE')?.count || 0;

  // Performance indicators
  const suppressionMeetsTarget = suppressionRate >= 90;
  const latencyMeetsTarget = avgLatency < 60;

  return (
    <div className="space-y-6">
      {/* Header with Time Range Selector */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold">Analytics Dashboard</h2>
          <p className="text-muted-foreground mt-1">
            Key performance indicators and insights
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
          {/* Hero Metrics Row */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Total Alerts KPI */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total Alerts</CardTitle>
                <AlertCircle className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">{totalAlerts.toLocaleString()}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  {suppressedAlerts.toLocaleString()} suppressed, {escalatedAlerts.toLocaleString()} escalated
                </p>
              </CardContent>
            </Card>

            {/* Suppression Rate KPI */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Suppression Rate</CardTitle>
                {suppressionMeetsTarget ? (
                  <CheckCircle className="h-4 w-4 text-green-600" />
                ) : (
                  <XCircle className="h-4 w-4 text-amber-600" />
                )}
              </CardHeader>
              <CardContent>
                <div className={`text-3xl font-bold ${suppressionMeetsTarget ? 'text-green-600' : 'text-amber-600'}`}>
                  {suppressionRate.toFixed(1)}%
                </div>
                <div className="flex items-center gap-1 mt-1">
                  {suppressionMeetsTarget ? (
                    <>
                      <TrendingUp className="h-3 w-3 text-green-600" />
                      <p className="text-xs text-green-600">Above 90% target</p>
                    </>
                  ) : (
                    <>
                      <TrendingDown className="h-3 w-3 text-amber-600" />
                      <p className="text-xs text-amber-600">Below 90% target</p>
                    </>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Escalations KPI */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Escalations</CardTitle>
                <AlertCircle className="h-4 w-4 text-amber-600" />
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-amber-600">{escalatedAlerts.toLocaleString()}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  {criticalAlerts} critical, {actionableAlerts} actionable
                </p>
              </CardContent>
            </Card>

            {/* Avg Latency KPI */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Avg Latency</CardTitle>
                {latencyMeetsTarget ? (
                  <CheckCircle className="h-4 w-4 text-green-600" />
                ) : (
                  <Clock className="h-4 w-4 text-amber-600" />
                )}
              </CardHeader>
              <CardContent>
                <div className={`text-3xl font-bold ${latencyMeetsTarget ? 'text-green-600' : 'text-amber-600'}`}>
                  {avgLatency.toFixed(1)}ms
                </div>
                <div className="flex items-center gap-1 mt-1">
                  {latencyMeetsTarget ? (
                    <>
                      <CheckCircle className="h-3 w-3 text-green-600" />
                      <p className="text-xs text-green-600">Below 60ms target</p>
                    </>
                  ) : (
                    <>
                      <Clock className="h-3 w-3 text-amber-600" />
                      <p className="text-xs text-amber-600">Above 60ms target</p>
                    </>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Insights Row: Classification Distribution + ML Performance */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Classification Distribution (Pie Chart) */}
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

            {/* ML Performance Metrics */}
            <Card>
              <CardHeader>
                <CardTitle>ML Pipeline Performance</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {/* Total Classifications */}
                  <div className="flex justify-between items-center p-3 bg-muted rounded-lg">
                    <div>
                      <div className="text-sm text-muted-foreground">Total Classifications</div>
                      <div className="text-2xl font-bold">{latencyData?.total.toLocaleString()}</div>
                    </div>
                    <RefreshCw className="h-6 w-6 text-muted-foreground" />
                  </div>

                  {/* Average Latency */}
                  <div className="flex justify-between items-center p-3 bg-muted rounded-lg">
                    <div>
                      <div className="text-sm text-muted-foreground">Average Latency</div>
                      <div className={`text-2xl font-bold ${latencyMeetsTarget ? 'text-green-600' : 'text-amber-600'}`}>
                        {avgLatency.toFixed(1)}ms
                      </div>
                    </div>
                    <Clock className={`h-6 w-6 ${latencyMeetsTarget ? 'text-green-600' : 'text-amber-600'}`} />
                  </div>

                  {/* Suppression Accuracy */}
                  <div className="flex justify-between items-center p-3 bg-muted rounded-lg">
                    <div>
                      <div className="text-sm text-muted-foreground">Suppression Rate</div>
                      <div className={`text-2xl font-bold ${suppressionMeetsTarget ? 'text-green-600' : 'text-amber-600'}`}>
                        {suppressionRate.toFixed(1)}%
                      </div>
                    </div>
                    {suppressionMeetsTarget ? (
                      <CheckCircle className="h-6 w-6 text-green-600" />
                    ) : (
                      <XCircle className="h-6 w-6 text-amber-600" />
                    )}
                  </div>

                  {/* Performance Indicator */}
                  <div className="p-3 bg-muted rounded-lg text-sm">
                    <div className="flex items-center gap-2 mb-2">
                      <strong>Performance Status:</strong>
                      {suppressionMeetsTarget && latencyMeetsTarget ? (
                        <span className="text-green-600 flex items-center gap-1">
                          <CheckCircle className="h-4 w-4" />
                          Excellent
                        </span>
                      ) : (
                        <span className="text-amber-600 flex items-center gap-1">
                          <AlertCircle className="h-4 w-4" />
                          Needs Attention
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Target: ≥90% suppression, &lt;60ms latency
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Performance Row: Latency Distribution + ROI & Action Breakdown */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Latency Distribution (Bar Chart) */}
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
                  <strong>Average Latency:</strong> {avgLatency.toFixed(1)}ms
                  <span className="ml-4 text-muted-foreground">
                    Total: {latencyData?.total.toLocaleString()} classifications
                  </span>
                </div>
              </CardContent>
            </Card>

            {/* ROI & Action Breakdown */}
            <Card>
              <CardHeader>
                <CardTitle>ROI & Action Breakdown</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {/* Time Saved */}
                  <div className="flex justify-between items-center p-3 bg-green-50 dark:bg-green-950 rounded-lg">
                    <div>
                      <div className="text-sm text-muted-foreground">Time Saved</div>
                      <div className="text-2xl font-bold text-green-600">
                        {timeSavedHours.toFixed(1)} hrs
                      </div>
                    </div>
                    <Clock className="h-6 w-6 text-green-600" />
                  </div>

                  {/* Cost Saved */}
                  <div className="flex justify-between items-center p-3 bg-green-50 dark:bg-green-950 rounded-lg">
                    <div>
                      <div className="text-sm text-muted-foreground">Cost Saved</div>
                      <div className="text-2xl font-bold text-green-600">
                        ${costSaved.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                      </div>
                    </div>
                    <DollarSign className="h-6 w-6 text-green-600" />
                  </div>

                  {/* Action Breakdown */}
                  <div className="p-3 bg-muted rounded-lg">
                    <div className="text-sm font-medium mb-3">Action Breakdown</div>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Auto-Suppressed</span>
                        <span className="font-medium text-green-600">{suppressedAlerts.toLocaleString()}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Escalated</span>
                        <span className="font-medium text-amber-600">{escalatedAlerts.toLocaleString()}</span>
                      </div>
                      <div className="flex justify-between pt-2 border-t">
                        <span className="font-medium">Total Processed</span>
                        <span className="font-bold">{totalAlerts.toLocaleString()}</span>
                      </div>
                    </div>
                  </div>

                  {/* ROI Calculation Note */}
                  <div className="text-xs text-muted-foreground p-3 bg-muted rounded-lg">
                    <strong>Calculation:</strong> Each suppressed alert saves 5 minutes of manual work at $75/hr MSP rate.
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Summary Statistics (Keep for completeness) */}
          <Card>
            <CardHeader>
              <CardTitle>Summary Statistics</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div>
                  <div className="text-sm text-muted-foreground mb-1">Total Alerts</div>
                  <div className="text-3xl font-bold">{totalAlerts.toLocaleString()}</div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground mb-1">Suppressed</div>
                  <div className="text-3xl font-bold text-green-600">
                    {suppressedAlerts.toLocaleString()}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground mb-1">Escalated</div>
                  <div className="text-3xl font-bold text-amber-600">
                    {escalatedAlerts.toLocaleString()}
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
