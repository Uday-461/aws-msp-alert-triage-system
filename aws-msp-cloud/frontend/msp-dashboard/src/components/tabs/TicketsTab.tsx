import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { TicketFilters } from '@/components/tickets/TicketFilters';
import { TicketDetailDialog } from '@/components/tickets/TicketDetailDialog';
import { useTickets } from '@/hooks/useTickets';
import type { Ticket, TicketFilters as Filters } from '@/types/api';
import { Loader2, RefreshCw } from 'lucide-react';

export function TicketsTab() {
  const [filters, setFilters] = useState<Filters>({ limit: 50 });
  const [selectedTicket, setSelectedTicket] = useState<Ticket | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  const { data: ticketsResponse, isLoading, error, refetch } = useTickets({ filters, autoRefresh: true });

  const tickets = ticketsResponse?.tickets || [];

  const handleFilterChange = (newFilters: Partial<Filters>) => {
    setFilters((prev: Filters) => ({ ...prev, ...newFilters }));
  };

  const handleClearFilters = () => {
    setFilters({ limit: 50 });
  };

  const handleTicketClick = (ticket: Ticket) => {
    setSelectedTicket(ticket);
    setDialogOpen(true);
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
      open: 'default',
      in_progress: 'secondary',
      resolved: 'outline',
      closed: 'outline',
    };
    return <Badge variant={variants[status] || 'default'}>{status.replace('_', ' ')}</Badge>;
  };

  const getPriorityBadge = (priority: string) => {
    const colors: Record<string, string> = {
      low: 'bg-gray-500',
      medium: 'bg-blue-500',
      high: 'bg-orange-500',
      critical: 'bg-red-500',
    };
    return (
      <Badge className={`${colors[priority] || 'bg-gray-500'} text-white`}>
        {priority}
      </Badge>
    );
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Tickets</h2>
        <p className="text-muted-foreground">
          View and manage customer support tickets
        </p>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle>Filters</CardTitle>
          <CardDescription>Filter tickets by customer, status, or priority</CardDescription>
        </CardHeader>
        <CardContent>
          <TicketFilters onFilterChange={handleFilterChange} onClear={handleClearFilters} />
        </CardContent>
      </Card>

      {/* Tickets List */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>All Tickets</CardTitle>
              <CardDescription>
                {tickets ? `${tickets.length} ticket(s) found` : 'Loading tickets...'}
              </CardDescription>
            </div>
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading && (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          )}

          {error && (
            <div className="text-center py-12">
              <p className="text-red-600">Failed to load tickets. Please try again.</p>
              <Button variant="outline" onClick={() => refetch()} className="mt-4">
                Retry
              </Button>
            </div>
          )}

          {tickets && tickets.length === 0 && (
            <div className="text-center py-12 text-muted-foreground">
              No tickets found. Try adjusting your filters.
            </div>
          )}

          {tickets && tickets.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left p-3 font-semibold">Ticket #</th>
                    <th className="text-left p-3 font-semibold">Customer</th>
                    <th className="text-left p-3 font-semibold">Subject</th>
                    <th className="text-left p-3 font-semibold">Status</th>
                    <th className="text-left p-3 font-semibold">Priority</th>
                    <th className="text-left p-3 font-semibold">Created</th>
                  </tr>
                </thead>
                <tbody>
                  {tickets.map((ticket) => (
                    <tr
                      key={ticket.id}
                      className="border-b hover:bg-muted/50 cursor-pointer transition-colors"
                      onClick={() => handleTicketClick(ticket)}
                    >
                      <td className="p-3">
                        <code className="text-sm font-mono">{ticket.ticket_number}</code>
                      </td>
                      <td className="p-3 text-sm">{ticket.customer_id}</td>
                      <td className="p-3 text-sm max-w-md truncate">{ticket.subject}</td>
                      <td className="p-3">{getStatusBadge(ticket.status)}</td>
                      <td className="p-3">{getPriorityBadge(ticket.priority)}</td>
                      <td className="p-3 text-sm text-muted-foreground">
                        {new Date(ticket.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Ticket Detail Dialog */}
      <TicketDetailDialog
        ticket={selectedTicket}
        open={dialogOpen}
        onOpenChange={setDialogOpen}
      />
    </div>
  );
}
