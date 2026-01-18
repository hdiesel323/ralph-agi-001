/**
 * React hook for WebSocket connection to RALPH-AGI backend.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { WS_URL } from '@/api/client';
import type { WebSocketEvent } from '@/types/task';

type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

interface UseWebSocketOptions {
  autoConnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  onEvent?: (event: WebSocketEvent) => void;
}

interface UseWebSocketReturn {
  status: ConnectionStatus;
  lastEvent: WebSocketEvent | null;
  connect: () => void;
  disconnect: () => void;
  send: (message: object) => void;
}

/**
 * Hook for WebSocket connection with auto-reconnect
 */
export function useWebSocket(options: UseWebSocketOptions = {}): UseWebSocketReturn {
  const {
    autoConnect = true,
    reconnectInterval = 3000,
    maxReconnectAttempts = 5,
    onEvent,
  } = options;

  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const [lastEvent, setLastEvent] = useState<WebSocketEvent | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const cleanup = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
  }, []);

  const disconnect = useCallback(() => {
    cleanup();
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setStatus('disconnected');
  }, [cleanup]);

  const connect = useCallback(() => {
    // Don't connect if already connected or connecting
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    cleanup();
    setStatus('connecting');

    try {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        setStatus('connected');
        reconnectAttemptsRef.current = 0;

        // Start ping interval
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          }
        }, 25000);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as WebSocketEvent;

          // Ignore pong messages
          if (data.type === 'pong' || data.type === 'ping') {
            return;
          }

          setLastEvent(data);
          onEvent?.(data);
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err);
        }
      };

      ws.onclose = () => {
        cleanup();
        setStatus('disconnected');
        wsRef.current = null;

        // Auto-reconnect
        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current++;
          reconnectTimeoutRef.current = setTimeout(connect, reconnectInterval);
        }
      };

      ws.onerror = (err) => {
        console.error('WebSocket error:', err);
        setStatus('error');
      };
    } catch (err) {
      console.error('Failed to create WebSocket:', err);
      setStatus('error');
    }
  }, [cleanup, reconnectInterval, maxReconnectAttempts, onEvent]);

  const send = useCallback((message: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  }, []);

  // Auto-connect on mount
  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [autoConnect, connect, disconnect]);

  return { status, lastEvent, connect, disconnect, send };
}
