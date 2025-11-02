import React from 'react';
import { CheckCircle2, Circle, Clock } from 'lucide-react';

interface StatusTimelineProps {
  currentStatus: 'open' | 'in_progress' | 'resolved' | 'closed';
  createdAt: string;
  updatedAt?: string;
}

const StatusTimeline: React.FC<StatusTimelineProps> = ({
  currentStatus,
  createdAt,
  updatedAt,
}) => {
  const statuses = [
    { key: 'open', label: 'Open', icon: Circle },
    { key: 'in_progress', label: 'In Progress', icon: Clock },
    { key: 'resolved', label: 'Resolved', icon: CheckCircle2 },
    { key: 'closed', label: 'Closed', icon: CheckCircle2 },
  ] as const;

  const currentStatusIndex = statuses.findIndex((s) => s.key === currentStatus);

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateString;
    }
  };

  return (
    <div className="py-4">
      <div className="flex items-center justify-between mb-4">
        {statuses.map((status, index) => {
          const Icon = status.icon;
          const isActive = index <= currentStatusIndex;
          const isCurrent = index === currentStatusIndex;

          return (
            <React.Fragment key={status.key}>
              <div className="flex flex-col items-center">
                <div
                  className={`
                    w-10 h-10 rounded-full flex items-center justify-center
                    transition-colors duration-200
                    ${
                      isActive
                        ? isCurrent
                          ? 'bg-primary-500 text-white'
                          : 'bg-green-500 text-white'
                        : 'bg-gray-200 text-gray-400'
                    }
                  `}
                >
                  <Icon size={20} />
                </div>
                <div className="mt-2 text-center">
                  <div
                    className={`text-xs font-medium ${
                      isActive ? 'text-gray-900' : 'text-gray-400'
                    }`}
                  >
                    {status.label}
                  </div>
                  {isCurrent && (
                    <div className="text-xs text-gray-500 mt-1">
                      {formatDate(updatedAt || createdAt)}
                    </div>
                  )}
                </div>
              </div>

              {index < statuses.length - 1 && (
                <div
                  className={`
                    flex-1 h-1 mx-2 rounded transition-colors duration-200
                    ${isActive ? 'bg-green-500' : 'bg-gray-200'}
                  `}
                  style={{ maxWidth: '60px' }}
                />
              )}
            </React.Fragment>
          );
        })}
      </div>

      <div className="text-xs text-gray-500 text-center">
        Created: {formatDate(createdAt)}
        {updatedAt && updatedAt !== createdAt && (
          <> • Last updated: {formatDate(updatedAt)}</>
        )}
      </div>
    </div>
  );
};

export default StatusTimeline;
