import { useState, useEffect } from 'react';

interface Ticket {
  id: string;
  ticket_number: string;
  subject: string;
  description: string;
  status: 'open' | 'in_progress' | 'resolved' | 'closed';
  priority: 'low' | 'medium' | 'high' | 'critical';
  created_at: string;
  updated_at?: string;
}

const API_URL = import.meta.env.VITE_TICKET_API_URL || 'http://localhost:8020';

export default function MyTickets({ customerId }: { customerId: string }) {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTicket, setSelectedTicket] = useState<Ticket | null>(null);

  useEffect(() => {
    fetchTickets();
  }, [customerId]);

  const fetchTickets = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/tickets?customer_id=${customerId}&limit=20`);
      const data = await response.json();
      setTickets(data.tickets || []);
    } catch (error) {
      console.error('Failed to fetch tickets:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    const colors = {
      open: 'bg-blue-100 text-blue-800',
      in_progress: 'bg-yellow-100 text-yellow-800',
      resolved: 'bg-green-100 text-green-800',
      closed: 'bg-gray-100 text-gray-800',
    };
    return colors[status as keyof typeof colors] || 'bg-gray-100 text-gray-800';
  };

  const getPriorityColor = (priority: string) => {
    const colors = {
      low: 'bg-gray-200 text-gray-700',
      medium: 'bg-blue-200 text-blue-700',
      high: 'bg-orange-200 text-orange-700',
      critical: 'bg-red-200 text-red-700',
    };
    return colors[priority as keyof typeof colors] || 'bg-gray-200 text-gray-700';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600">Loading your tickets...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">My Tickets</h1>
        <button
          onClick={fetchTickets}
          className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
        >
          Refresh
        </button>
      </div>

      {tickets.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg shadow">
          <p className="text-gray-600">No tickets found. Create your first ticket to get help!</p>
        </div>
      ) : (
        <div className="space-y-4">
          {tickets.map((ticket) => (
            <div
              key={ticket.id}
              className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow cursor-pointer"
              onClick={() => setSelectedTicket(selectedTicket?.id === ticket.id ? null : ticket)}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="text-lg font-semibold text-gray-900">{ticket.subject}</h3>
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(ticket.status)}`}>
                      {ticket.status.replace('_', ' ')}
                    </span>
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${getPriorityColor(ticket.priority)}`}>
                      {ticket.priority}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 mb-2">Ticket #{ticket.ticket_number}</p>
                  {selectedTicket?.id === ticket.id && (
                    <div className="mt-4 pt-4 border-t border-gray-200">
                      <p className="text-gray-700 whitespace-pre-wrap">{ticket.description}</p>
                      <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="font-medium text-gray-900">Created:</span>{' '}
                          <span className="text-gray-600">
                            {new Date(ticket.created_at).toLocaleString()}
                          </span>
                        </div>
                        {ticket.updated_at && (
                          <div>
                            <span className="font-medium text-gray-900">Updated:</span>{' '}
                            <span className="text-gray-600">
                              {new Date(ticket.updated_at).toLocaleString()}
                            </span>
                          </div>
                        )}
                      </div>

                      {/* Status Timeline */}
                      <div className="mt-6">
                        <h4 className="text-sm font-semibold text-gray-900 mb-3">Status Timeline</h4>
                        <div className="flex items-center gap-2">
                          {['open', 'in_progress', 'resolved', 'closed'].map((status, index) => {
                            const isActive = ['open', 'in_progress', 'resolved', 'closed'].indexOf(ticket.status) >= index;
                            return (
                              <div key={status} className="flex items-center flex-1">
                                <div className={`flex-1 h-1 ${isActive ? 'bg-blue-600' : 'bg-gray-200'}`} />
                                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium ${
                                  isActive ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-600'
                                }`}>
                                  {index + 1}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                        <div className="flex justify-between mt-2 text-xs text-gray-600">
                          <span>Open</span>
                          <span>In Progress</span>
                          <span>Resolved</span>
                          <span>Closed</span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
                <div className="ml-4 text-sm text-gray-500">
                  {new Date(ticket.created_at).toLocaleDateString()}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
