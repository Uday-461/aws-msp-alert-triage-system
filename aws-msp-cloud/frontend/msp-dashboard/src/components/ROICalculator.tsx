import { useState } from 'react';
import { useMetrics } from '@/hooks/useMetrics';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';

export function ROICalculator() {
  const [hourlyRate, setHourlyRate] = useState(75);
  const { data: metrics } = useMetrics(24);

  if (!metrics) return null;

  const suppressionRate = metrics.suppression_rate / 100;
  const alertsPerDay = metrics.total_alerts;
  const minutesPerAlert = 5;

  const calculateROI = (days: number) => {
    const alerts = alertsPerDay * days;
    const suppressedAlerts = alerts * suppressionRate;
    const minutesSaved = suppressedAlerts * minutesPerAlert;
    const hoursSaved = minutesSaved / 60;
    const costSaved = hoursSaved * hourlyRate;
    return { hoursSaved, costSaved };
  };

  const periods = [
    { label: 'Daily', days: 1 },
    { label: 'Weekly', days: 7 },
    { label: 'Monthly', days: 30 },
    { label: 'Annual', days: 365 },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>ROI Calculator</CardTitle>
        <div className="flex items-center gap-2 mt-2">
          <label className="text-sm text-muted-foreground">Hourly Rate ($):</label>
          <Input
            type="number"
            value={hourlyRate}
            onChange={(e) => setHourlyRate(Number(e.target.value))}
            className="w-24"
          />
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* CRITICAL: Every period MUST have unique key */}
          {periods.map((period) => {
            const roi = calculateROI(period.days);
            return (
              <div key={period.label} className="border border-border rounded-lg p-4">
                <h3 className="font-semibold mb-2">{period.label}</h3>
                <div className="space-y-1">
                  <div className="text-2xl font-bold text-green-400">
                    ${roi.costSaved.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {roi.hoursSaved.toFixed(1)}h saved
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
