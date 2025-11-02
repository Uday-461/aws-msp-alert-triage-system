import React from 'react';
import { User, Bot } from 'lucide-react';
import type { Message } from '../types';
import { cn } from '../utils/cn';

interface MessageBubbleProps {
  message: Message;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isUser = message.role === 'user';

  const formatTime = (date: Date) => {
    return new Date(date).toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
    });
  };

  const formatContent = (content: string) => {
    // Simple formatting: preserve line breaks
    return content.split('\n').map((line, i) => (
      <React.Fragment key={i}>
        {line}
        {i < content.split('\n').length - 1 && <br />}
      </React.Fragment>
    ));
  };

  return (
    <div
      className={cn(
        'flex gap-3 mb-4',
        isUser ? 'flex-row-reverse' : 'flex-row'
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center',
          isUser
            ? 'bg-primary-500 text-white'
            : 'bg-gray-200 text-gray-700'
        )}
      >
        {isUser ? <User size={18} /> : <Bot size={18} />}
      </div>

      {/* Message Content */}
      <div className={cn('flex flex-col max-w-[70%]', isUser ? 'items-end' : 'items-start')}>
        <div
          className={cn(
            'rounded-lg px-4 py-2 break-words',
            isUser
              ? 'bg-primary-500 text-white'
              : 'bg-white text-gray-800 border border-gray-200'
          )}
        >
          <div className="text-sm leading-relaxed whitespace-pre-wrap">
            {formatContent(message.content)}
          </div>
        </div>

        {/* Timestamp */}
        <span className="text-xs text-gray-500 mt-1 px-1">
          {formatTime(message.timestamp)}
        </span>

        {/* Sources (if any) */}
        {message.sources && message.sources.length > 0 && (
          <div className="mt-2 text-xs text-gray-600 bg-gray-50 rounded px-2 py-1">
            <div className="font-semibold mb-1">Sources:</div>
            <ul className="list-disc list-inside space-y-1">
              {message.sources.map((source, idx) => (
                <li key={idx} className="truncate">{source}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};

export default MessageBubble;
