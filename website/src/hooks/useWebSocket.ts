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
  const isConnectingRef = useRef(false);
  const isMountedRef = useRef(true);

  // Use ref for onEvent to avoid dependency changes
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

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
    isConnectingRef.current = false;
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setStatus('disconnected');
  }, [cleanup]);

  const connect = useCallback(() => {
    // Don't connect if already connected, connecting, or unmounted
    if (wsRef.current?.readyState === WebSocket.OPEN ||
        wsRef.current?.readyState === WebSocket.CONNECTING ||
        isConnectingRef.current ||
        !isMountedRef.current) {
      return;
    }

    cleanup();
    isConnectingRef.current = true;
    setStatus('connecting');

    try {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!isMountedRef.current) {
          ws.close();
          return;
        }
        isConnectingRef.current = false;
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
          onEventRef.current?.(data);
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err);
        }
      };

      ws.onclose = () => {
        cleanup();
        isConnectingRef.current = false;
        wsRef.current = null;

        if (!isMountedRef.current) return;

        setStatus('disconnected');

        // Auto-reconnect with exponential backoff
        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          const backoff = reconnectInterval * Math.pow(1.5, reconnectAttemptsRef.current);
          reconnectAttemptsRef.current++;
          reconnectTimeoutRef.current = setTimeout(() => {
            if (isMountedRef.current) {
              connect();
            }
          }, Math.min(backoff, 30000));
        }
      };

      ws.onerror = () => {
        // Error will be followed by close event
        isConnectingRef.current = false;
        if (isMountedRef.current) {
          setStatus('error');
        }
      };
    } catch (err) {
      console.error('Failed to create WebSocket:', err);
      isConnectingRef.current = false;
      setStatus('error');
    }
  }, [cleanup, reconnectInterval, maxReconnectAttempts]);

  const send = useCallback((message: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  }, []);

  // Auto-connect on mount
  useEffect(() => {
    isMountedRef.current = true;

    if (autoConnect) {
      connect();
    }

    return () => {
      isMountedRef.current = false;
      disconnect();
    };
  }, [autoConnect]); // Intentionally minimal dependencies

  return { status, lastEvent, connect, disconnect, send };
}
