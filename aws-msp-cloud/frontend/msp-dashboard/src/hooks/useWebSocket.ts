import { useEffect, useRef, useState, useCallback } from 'react';
import type { WebSocketMessage } from '@/types/api';

const WS_URL = import.meta.env.VITE_WS_URL;
const RECONNECT_DELAY = 5000;
const PING_INTERVAL = 30000;

export function useWebSocket(onMessage: (message: WebSocketMessage) => void) {
  const [isConnected, setIsConnected] = useState(false);
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<number>();
  const pingInterval = useRef<number>();

  const connect = useCallback(() => {
    console.log('WebSocket: Connecting...');

    try {
      ws.current = new WebSocket(WS_URL);

      ws.current.onopen = () => {
        console.log('WebSocket: Connected');
        setIsConnected(true);

        // Start ping interval
        pingInterval.current = window.setInterval(() => {
          if (ws.current?.readyState === WebSocket.OPEN) {
            ws.current.send(JSON.stringify({ type: 'ping' }));
          }
        }, PING_INTERVAL);
      };

      ws.current.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          console.log('WebSocket: Message received', message);
          onMessage(message);
        } catch (error) {
          console.error('WebSocket: Failed to parse message', error);
        }
      };

      ws.current.onerror = (error) => {
        console.error('WebSocket: Error', error);
      };

      ws.current.onclose = () => {
        console.log('WebSocket: Disconnected');
        setIsConnected(false);

        // Clear ping interval
        if (pingInterval.current) {
          clearInterval(pingInterval.current);
        }

        // Schedule reconnect
        reconnectTimeout.current = window.setTimeout(() => {
          console.log('WebSocket: Attempting to reconnect...');
          connect();
        }, RECONNECT_DELAY);
      };
    } catch (error) {
      console.error('WebSocket: Connection failed', error);
    }
  }, [onMessage]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
      }
      if (pingInterval.current) {
        clearInterval(pingInterval.current);
      }
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [connect]);

  return { isConnected };
}
