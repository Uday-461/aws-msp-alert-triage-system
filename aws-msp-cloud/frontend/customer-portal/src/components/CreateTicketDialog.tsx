import React, { useState, useEffect } from 'react';
import { X, CheckCircle, AlertCircle } from 'lucide-react';
import { useCreateTicket, type CreateTicketRequest } from '../hooks/useCreateTicket';
import type { Message } from '../types';

interface CreateTicketDialogProps {
  isOpen: boolean;
  onClose: () => void;
  conversationId: string | null;
  userId: string;
  messages: Message[];
}

const CreateTicketDialog: React.FC<CreateTicketDialogProps> = ({
  isOpen,
  onClose,
  conversationId,
  userId,
  messages,
}) => {
  const [subject, setSubject] = useState('');
  const [description, setDescription] = useState('');
  const [priority, setPriority] = useState<'low' | 'medium' | 'high'>('medium');

  const { createTicket, isCreating, error, createdTicket, reset } = useCreateTicket();

  // Pre-fill description with recent conversation messages
  useEffect(() => {
    if (isOpen && messages.length > 0) {
      // Get last 3 messages (or fewer if less available)
      const recentMessages = messages.slice(-6);
      const conversationText = recentMessages
        .map((msg) => `${msg.role === 'user' ? 'User' : 'Assistant'}: ${msg.content}`)
        .join('\n\n');
      setDescription(conversationText);
    }
  }, [isOpen, messages]);

  // Reset form when dialog closes
  useEffect(() => {
    if (!isOpen) {
      setTimeout(() => {
        setSubject('');
        setDescription('');
        setPriority('medium');
        reset();
      }, 300); // Wait for animation to complete
    }
  }, [isOpen, reset]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!subject.trim()) {
      return;
    }

    const request: CreateTicketRequest = {
      customer_id: userId,
      subject: subject.trim(),
      description: description.trim() || 'No description provided',
      priority,
      conversation_id: conversationId || undefined,
    };

    try {
      await createTicket(request);
      // Don't close immediately - show success state first
    } catch (err) {
      // Error is handled by the hook
      console.error('Failed to create ticket:', err);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">
            {createdTicket ? 'Ticket Created Successfully' : 'Create Support Ticket'}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="Close dialog"
          >
            <X size={24} />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {createdTicket ? (
            // Success State
            <div className="text-center py-6">
              <div className="flex justify-center mb-4">
                <CheckCircle size={64} className="text-green-500" />
              </div>
              <h3 className="text-2xl font-bold text-gray-900 mb-2">
                Ticket #{createdTicket.ticket_number}
              </h3>
              <p className="text-gray-600 mb-4">
                Your support ticket has been created successfully.
              </p>
              <div className="bg-gray-50 rounded-lg p-4 text-left mb-6">
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <span className="font-semibold text-gray-700">Subject:</span>
                    <p className="text-gray-600">{createdTicket.subject}</p>
                  </div>
                  <div>
                    <span className="font-semibold text-gray-700">Priority:</span>
                    <p className="text-gray-600 capitalize">{createdTicket.priority}</p>
                  </div>
                  <div>
                    <span className="font-semibold text-gray-700">Status:</span>
                    <p className="text-gray-600 capitalize">{createdTicket.status}</p>
                  </div>
                  <div>
                    <span className="font-semibold text-gray-700">Created:</span>
                    <p className="text-gray-600">
                      {new Date(createdTicket.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>
              </div>
              <button
                onClick={onClose}
                className="px-6 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
              >
                Close
              </button>
            </div>
          ) : (
            // Form State
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Error Message */}
              {error && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
                  <AlertCircle size={20} className="text-red-500 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-semibold text-red-800">Failed to create ticket</p>
                    <p className="text-sm text-red-700">{error}</p>
                  </div>
                </div>
              )}

              {/* Subject */}
              <div>
                <label htmlFor="subject" className="block text-sm font-medium text-gray-700 mb-1">
                  Subject <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  id="subject"
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  placeholder="Brief description of the issue"
                  required
                  disabled={isCreating}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
                />
              </div>

              {/* Priority */}
              <div>
                <label htmlFor="priority" className="block text-sm font-medium text-gray-700 mb-1">
                  Priority
                </label>
                <select
                  id="priority"
                  value={priority}
                  onChange={(e) => setPriority(e.target.value as 'low' | 'medium' | 'high')}
                  disabled={isCreating}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
              </div>

              {/* Description */}
              <div>
                <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-1">
                  Description
                </label>
                <textarea
                  id="description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Detailed description of the issue (optional)"
                  rows={8}
                  disabled={isCreating}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed resize-vertical"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Pre-filled with recent conversation. Feel free to edit.
                </p>
              </div>

              {/* Actions */}
              <div className="flex justify-end gap-3 pt-4">
                <button
                  type="button"
                  onClick={onClose}
                  disabled={isCreating}
                  className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!subject.trim() || isCreating}
                  className="px-6 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
                >
                  {isCreating ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                      <span>Creating...</span>
                    </>
                  ) : (
                    'Create Ticket'
                  )}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};

export default CreateTicketDialog;
