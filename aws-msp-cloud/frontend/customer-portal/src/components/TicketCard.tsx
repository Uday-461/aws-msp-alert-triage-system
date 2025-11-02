import React, { useState } from 'react';
import { ChevronDown, ChevronRight, ExternalLink, MessageCircle } from 'lucide-react';
import type { Ticket } from '../types';
import StatusTimeline from './StatusTimeline';

interface TicketCardProps {
  ticket: Ticket;
}

const TicketCard: React.FC<TicketCardProps> = ({ ticket }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const getStatusColor = (status: Ticket['status']) => {
    switch (status) {
      case 'open':
        return 'bg-blue-100 text-blue-800';
      case 'in_progress':
        return 'bg-yellow-100 text-yellow-800';
      case 'resolved':
        return 'bg-green-100 text-green-800';
      case 'closed':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getPriorityColor = (priority: Ticket['priority']) => {
    switch (priority) {
      case 'critical':
        return 'bg-red-100 text-red-800';
      case 'high':
        return 'bg-orange-100 text-orange-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'low':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateString;
    }
  };

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition-shadow">
      {/* Card Header */}
      <div
        className="p-4 cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <button
                className="text-gray-400 hover:text-gray-600"
                onClick={(e) => {
                  e.stopPropagation();
                  setIsExpanded(!isExpanded);
                }}
              >
                {isExpanded ? <ChevronDown size={20} /> : <ChevronRight size={20} />}
              </button>
              <span className="text-sm font-mono text-gray-500">
                {ticket.ticket_number}
              </span>
              <span
                className={`px-2 py-1 text-xs font-medium rounded ${getStatusColor(
                  ticket.status
                )}`}
              >
                {ticket.status.replace('_', ' ').toUpperCase()}
              </span>
              <span
                className={`px-2 py-1 text-xs font-medium rounded ${getPriorityColor(
                  ticket.priority
                )}`}
              >
                {ticket.priority.toUpperCase()}
              </span>
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-1 truncate">
              {ticket.subject}
            </h3>
            <p className="text-sm text-gray-500">
              Created: {formatDate(ticket.created_at)}
            </p>
          </div>

          {ticket.conversation_id && (
            <div className="ml-4 text-gray-400" title="Created from chat">
              <MessageCircle size={20} />
            </div>
          )}
        </div>
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="border-t border-gray-200 p-4 bg-gray-50">
          {/* Description */}
          <div className="mb-4">
            <h4 className="text-sm font-semibold text-gray-700 mb-2">
              Description
            </h4>
            <p className="text-sm text-gray-600 whitespace-pre-wrap">
              {ticket.description}
            </p>
          </div>

          {/* Status Timeline */}
          <div className="mb-4">
            <h4 className="text-sm font-semibold text-gray-700 mb-2">
              Status Timeline
            </h4>
            <StatusTimeline
              currentStatus={ticket.status}
              createdAt={ticket.created_at}
              updatedAt={ticket.updated_at}
            />
          </div>

          {/* Actions */}
          <div className="flex gap-2">
            {ticket.conversation_id && (
              <button
                className="flex items-center gap-2 px-4 py-2 text-sm bg-primary-500 text-white rounded-md hover:bg-primary-600 transition-colors"
                onClick={() => {
                  // TODO: Navigate to conversation (implement in parent)
                  console.log('View conversation:', ticket.conversation_id);
                }}
              >
                <MessageCircle size={16} />
                View Conversation
              </button>
            )}
            <button
              className="flex items-center gap-2 px-4 py-2 text-sm bg-white border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 transition-colors"
              onClick={() => {
                // TODO: Implement ticket details modal or page
                console.log('View full ticket:', ticket.id);
              }}
            >
              <ExternalLink size={16} />
              View Details
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default TicketCard;
