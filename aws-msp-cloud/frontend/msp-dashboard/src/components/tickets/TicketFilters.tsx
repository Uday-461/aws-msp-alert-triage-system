import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { TicketStatus, TicketPriority } from '@/types/api';

interface TicketFiltersProps {
  onFilterChange: (filters: {
    customer_id?: string;
    status?: TicketStatus;
    priority?: TicketPriority;
  }) => void;
  onClear: () => void;
}

export function TicketFilters({ onFilterChange, onClear }: TicketFiltersProps) {
  const handleCustomerIdChange = (value: string) => {
    onFilterChange({ customer_id: value || undefined });
  };

  const handleStatusChange = (value: string) => {
    onFilterChange({ status: value === 'all' ? undefined : value as TicketStatus });
  };

  const handlePriorityChange = (value: string) => {
    onFilterChange({ priority: value === 'all' ? undefined : value as TicketPriority });
  };

  return (
    <div className="flex flex-wrap gap-4 items-end">
      <div className="flex-1 min-w-[200px]">
        <label className="text-sm font-medium mb-2 block">Customer ID</label>
        <Input
          placeholder="Search by customer ID..."
          onChange={(e) => handleCustomerIdChange(e.target.value)}
        />
      </div>

      <div className="min-w-[150px]">
        <label className="text-sm font-medium mb-2 block">Status</label>
        <Select defaultValue="all" onValueChange={handleStatusChange}>
          <SelectTrigger>
            <SelectValue placeholder="All Statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Statuses</SelectItem>
            <SelectItem value="open">Open</SelectItem>
            <SelectItem value="in_progress">In Progress</SelectItem>
            <SelectItem value="resolved">Resolved</SelectItem>
            <SelectItem value="closed">Closed</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="min-w-[150px]">
        <label className="text-sm font-medium mb-2 block">Priority</label>
        <Select defaultValue="all" onValueChange={handlePriorityChange}>
          <SelectTrigger>
            <SelectValue placeholder="All Priorities" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Priorities</SelectItem>
            <SelectItem value="low">Low</SelectItem>
            <SelectItem value="medium">Medium</SelectItem>
            <SelectItem value="high">High</SelectItem>
            <SelectItem value="critical">Critical</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <Button variant="outline" onClick={onClear}>
        Clear Filters
      </Button>
    </div>
  );
}
