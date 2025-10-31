import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import type { TimeRange } from '@/types/api';

interface TimeRangeSelectorProps {
  value: TimeRange;
  onChange: (value: TimeRange) => void;
}

const timeRanges: { value: TimeRange; label: string }[] = [
  { value: '1h', label: 'Last Hour' },
  { value: '24h', label: 'Last 24 Hours' },
  { value: '7d', label: 'Last 7 Days' },
  { value: '30d', label: 'Last 30 Days' },
];

export function TimeRangeSelector({ value, onChange }: TimeRangeSelectorProps) {
  return (
    <Tabs value={value} onValueChange={(v) => onChange(v as TimeRange)}>
      <TabsList>
        {timeRanges.map((range) => (
          <TabsTrigger key={range.value} value={range.value}>
            {range.label}
          </TabsTrigger>
        ))}
      </TabsList>
    </Tabs>
  );
}
