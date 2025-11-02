import React, { useState } from 'react';
import { RefreshCw, Ticket as TicketIcon, AlertCircle, Loader2, Plus } from 'lucide-react';
import { useCustomerTickets } from '../hooks/useCustomerTickets';
import TicketCard from './TicketCard';

const MyTicketsView: React.FC = () => {
  const { tickets, isLoading, error, refreshTickets } = useCustomerTickets();
  const [filterStatus, setFilterStatus] = useState<string>('all');

  // Filter tickets by status
  const filteredTickets = tickets.filter((ticket) => {
    if (filterStatus === 'all') return true;
    return ticket.status === filterStatus;
  });

  // Count tickets by status
  const statusCounts = tickets.reduce(
    (acc, ticket) => {
      acc[ticket.status] = (acc[ticket.status] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  );

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-primary-600 text-white p-4 shadow-md">
        <div className="max-w-6xl mx-auto">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold">My Tickets</h1>
              <p className="text-sm text-primary-100">
                Track your support requests
              </p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={refreshTickets}
                disabled={isLoading}
                className="flex items-center gap-2 px-3 py-2 bg-primary-700 hover:bg-primary-800 rounded-md transition-colors text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                title="Refresh tickets"
              >
                <RefreshCw size={16} className={isLoading ? 'animate-spin' : ''} />
                Refresh
              </button>
              <button
                onClick={() => {
                  // TODO: Implement create ticket flow
                  console.log('Create new ticket');
                }}
                className="flex items-center gap-2 px-3 py-2 bg-green-500 hover:bg-green-600 rounded-md transition-colors text-sm"
                title="Create new ticket"
              >
                <Plus size={16} />
                New Ticket
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-3">
          <div className="flex items-center gap-2 overflow-x-auto">
            <span className="text-sm text-gray-600 font-medium mr-2">Filter:</span>
            {[
              { key: 'all', label: 'All', count: tickets.length },
              { key: 'open', label: 'Open', count: statusCounts.open || 0 },
              {
                key: 'in_progress',
                label: 'In Progress',
                count: statusCounts.in_progress || 0,
              },
              { key: 'resolved', label: 'Resolved', count: statusCounts.resolved || 0 },
              { key: 'closed', label: 'Closed', count: statusCounts.closed || 0 },
            ].map((filter) => (
              <button
                key={filter.key}
                onClick={() => setFilterStatus(filter.key)}
                className={`
                  px-3 py-1.5 rounded-md text-sm font-medium transition-colors whitespace-nowrap
                  ${
                    filterStatus === filter.key
                      ? 'bg-primary-100 text-primary-700 border border-primary-300'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }
                `}
              >
                {filter.label}
                {filter.count > 0 && (
                  <span className="ml-1.5 text-xs">({filter.count})</span>
                )}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-6xl mx-auto px-4 py-6">
          {/* Loading State */}
          {isLoading && tickets.length === 0 && (
            <div className="flex flex-col items-center justify-center py-12">
              <Loader2 size={48} className="text-primary-500 animate-spin mb-4" />
              <p className="text-gray-600">Loading your tickets...</p>
            </div>
          )}

          {/* Error State */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
              <AlertCircle size={20} className="text-red-600 mt-0.5 flex-shrink-0" />
              <div>
                <h3 className="text-red-800 font-semibold mb-1">
                  Failed to load tickets
                </h3>
                <p className="text-red-700 text-sm">{error}</p>
                <button
                  onClick={refreshTickets}
                  className="mt-2 text-red-600 hover:text-red-800 text-sm font-medium underline"
                >
                  Try again
                </button>
              </div>
            </div>
          )}

          {/* Empty State */}
          {!isLoading && !error && filteredTickets.length === 0 && (
            <div className="text-center py-12">
              <div className="text-gray-400 mb-4">
                <TicketIcon size={64} className="mx-auto" strokeWidth={1.5} />
              </div>
              <h2 className="text-xl font-semibold text-gray-700 mb-2">
                {filterStatus === 'all'
                  ? 'No tickets yet'
                  : `No ${filterStatus.replace('_', ' ')} tickets`}
              </h2>
              <p className="text-gray-500 mb-4">
                {filterStatus === 'all'
                  ? "You haven't created any support tickets yet."
                  : `You don't have any tickets with status: ${filterStatus.replace(
                      '_',
                      ' '
                    )}`}
              </p>
              {filterStatus === 'all' && (
                <button
                  onClick={() => {
                    // TODO: Implement create ticket flow
                    console.log('Create first ticket');
                  }}
                  className="px-4 py-2 bg-primary-500 text-white rounded-md hover:bg-primary-600 transition-colors"
                >
                  Create Your First Ticket
                </button>
              )}
            </div>
          )}

          {/* Tickets List */}
          {!isLoading && !error && filteredTickets.length > 0 && (
            <div className="space-y-4">
              <div className="text-sm text-gray-600 mb-4">
                Showing {filteredTickets.length} of {tickets.length} ticket
                {tickets.length !== 1 ? 's' : ''}
              </div>
              {filteredTickets.map((ticket) => (
                <TicketCard key={ticket.id} ticket={ticket} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MyTicketsView;
