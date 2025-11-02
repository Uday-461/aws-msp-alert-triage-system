import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useUpdateTicket, useSyncTicket } from '@/hooks/useTickets';
import type { Ticket, TicketStatus, TicketPriority } from '@/types/api';
import { Loader2 } from 'lucide-react';

interface TicketDetailDialogProps {
  ticket: Ticket | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function TicketDetailDialog({ ticket, open, onOpenChange }: TicketDetailDialogProps) {
  const [newStatus, setNewStatus] = useState<TicketStatus | ''>('');
  const [newPriority, setNewPriority] = useState<TicketPriority | ''>('');

  const updateTicket = useUpdateTicket();
  const syncTicket = useSyncTicket();

  if (!ticket) return null;

  const handleUpdateStatus = () => {
    if (newStatus && newStatus !== ticket.status) {
      updateTicket.mutate(
        { ticketId: ticket.id, updates: { status: newStatus as TicketStatus } },
        {
          onSuccess: () => {
            setNewStatus('');
          },
        }
      );
    }
  };

  const handleUpdatePriority = () => {
    if (newPriority && newPriority !== ticket.priority) {
      updateTicket.mutate(
        { ticketId: ticket.id, updates: { priority: newPriority as TicketPriority } },
        {
          onSuccess: () => {
            setNewPriority('');
          },
        }
      );
    }
  };

  const handleSync = () => {
    syncTicket.mutate(ticket.id);
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
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-3">
            <span>{ticket.ticket_number}</span>
            {getStatusBadge(ticket.status)}
            {getPriorityBadge(ticket.priority)}
          </DialogTitle>
          <DialogDescription>
            Customer: {ticket.customer_id}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Subject */}
          <div>
            <h3 className="font-semibold mb-2">Subject</h3>
            <p className="text-sm">{ticket.subject}</p>
          </div>

          {/* Description */}
          <div>
            <h3 className="font-semibold mb-2">Description</h3>
            <p className="text-sm whitespace-pre-wrap">{ticket.description}</p>
          </div>

          {/* Metadata */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="font-semibold">Created:</span>{' '}
              {new Date(ticket.created_at).toLocaleString()}
            </div>
            {ticket.updated_at && (
              <div>
                <span className="font-semibold">Updated:</span>{' '}
                {new Date(ticket.updated_at).toLocaleString()}
              </div>
            )}
            {ticket.superops_ticket_id && (
              <div className="col-span-2">
                <span className="font-semibold">SuperOps ID:</span>{' '}
                <Badge variant="outline">{ticket.superops_ticket_id}</Badge>
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="space-y-4 border-t pt-4">
            <h3 className="font-semibold">Actions</h3>

            {/* Update Status */}
            <div className="flex gap-2">
              <Select value={newStatus || ticket.status} onValueChange={(val) => setNewStatus(val as TicketStatus)}>
                <SelectTrigger className="w-[200px]">
                  <SelectValue placeholder="Change Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="open">Open</SelectItem>
                  <SelectItem value="in_progress">In Progress</SelectItem>
                  <SelectItem value="resolved">Resolved</SelectItem>
                  <SelectItem value="closed">Closed</SelectItem>
                </SelectContent>
              </Select>
              <Button
                onClick={handleUpdateStatus}
                disabled={!newStatus || newStatus === ticket.status || updateTicket.isPending}
              >
                {updateTicket.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Update Status
              </Button>
            </div>

            {/* Update Priority */}
            <div className="flex gap-2">
              <Select value={newPriority || ticket.priority} onValueChange={(val) => setNewPriority(val as TicketPriority)}>
                <SelectTrigger className="w-[200px]">
                  <SelectValue placeholder="Change Priority" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="low">Low</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                  <SelectItem value="critical">Critical</SelectItem>
                </SelectContent>
              </Select>
              <Button
                onClick={handleUpdatePriority}
                disabled={!newPriority || newPriority === ticket.priority || updateTicket.isPending}
              >
                {updateTicket.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Update Priority
              </Button>
            </div>

            {/* Sync to SuperOps */}
            <div>
              <Button
                onClick={handleSync}
                disabled={syncTicket.isPending || !!ticket.superops_ticket_id}
                variant="outline"
              >
                {syncTicket.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {ticket.superops_ticket_id ? 'Already Synced' : 'Sync to SuperOps'}
              </Button>
              {syncTicket.isSuccess && (
                <p className="text-sm text-green-600 mt-2">✓ Synced successfully!</p>
              )}
              {syncTicket.isError && (
                <p className="text-sm text-red-600 mt-2">✗ Sync failed. Please try again.</p>
              )}
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
