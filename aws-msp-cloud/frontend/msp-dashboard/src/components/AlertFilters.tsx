import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';
import type { AlertFilters as AlertFiltersType } from '@/types/api';

interface AlertFiltersProps {
  onFiltersChange: (filters: AlertFiltersType) => void;
}

export function AlertFilters({ onFiltersChange }: AlertFiltersProps) {
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState<string>('');
  const [severity, setSeverity] = useState<string>('');

  const handleApply = () => {
    onFiltersChange({
      search: search || undefined,
      status: status as any || undefined,
      severity: severity as any || undefined,
    });
  };

  const handleClear = () => {
    setSearch('');
    setStatus('');
    setSeverity('');
    onFiltersChange({});
  };

  return (
    <Card className="mb-4">
      <CardContent className="pt-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Input
            placeholder="Search alerts..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <select
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          >
            <option value="">All Statuses</option>
            <option value="AUTO_SUPPRESS">Suppressed</option>
            <option value="ESCALATE">Escalated</option>
            <option value="REVIEW">Review</option>
            <option value="pending">Pending</option>
          </select>
          <select
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2"
            value={severity}
            onChange={(e) => setSeverity(e.target.value)}
          >
            <option value="">All Severities</option>
            <option value="LOW">Low</option>
            <option value="MEDIUM">Medium</option>
            <option value="HIGH">High</option>
            <option value="CRITICAL">Critical</option>
          </select>
          <div className="flex gap-2">
            <Button onClick={handleApply} className="flex-1">Apply</Button>
            <Button onClick={handleClear} variant="outline">Clear</Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
