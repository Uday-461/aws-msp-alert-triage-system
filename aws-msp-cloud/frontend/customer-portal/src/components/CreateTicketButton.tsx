import React from 'react';
import { TicketIcon } from 'lucide-react';

interface CreateTicketButtonProps {
  onClick: () => void;
  disabled?: boolean;
  className?: string;
}

const CreateTicketButton: React.FC<CreateTicketButtonProps> = ({
  onClick,
  disabled = false,
  className = '',
}) => {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`flex items-center gap-2 px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors ${className}`}
      title="Create support ticket"
    >
      <TicketIcon size={18} />
      <span className="hidden sm:inline">Create Ticket</span>
    </button>
  );
};

export default CreateTicketButton;
