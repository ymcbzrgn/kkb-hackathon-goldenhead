/**
 * WebSocket Service
 * Real WebSocket + Mock WebSocket switch
 */

import type { WebSocketEvent, WebSocketConnectionState } from '@/types';
import { createMockWebSocket, MockWebSocket } from '@/mocks/mockWebSocket';

// ==================== Config ====================

const WS_BASE_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';
const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';

// ==================== Types ====================

export interface WebSocketCallbacks {
  onEvent: (event: WebSocketEvent) => void;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (error: string) => void;
}

export interface WebSocketConnection {
  close: () => void;
  isConnected: () => boolean;
}

// ==================== Real WebSocket ====================

function createRealWebSocket(
  reportId: string,
  callbacks: WebSocketCallbacks
): WebSocketConnection {
  const url = `${WS_BASE_URL}/ws/${reportId}`;
  let ws: WebSocket | null = null;
  let isConnected = false;

  try {
    ws = new WebSocket(url);

    ws.onopen = () => {
      isConnected = true;
      callbacks.onOpen?.();
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as WebSocketEvent;
        callbacks.onEvent(data);
      } catch (err) {
        console.error('WebSocket message parse error:', err);
      }
    };

    ws.onerror = () => {
      callbacks.onError?.('WebSocket bağlantı hatası');
    };

    ws.onclose = () => {
      isConnected = false;
      callbacks.onClose?.();
    };
  } catch (err) {
    callbacks.onError?.(err instanceof Error ? err.message : 'WebSocket hatası');
  }

  return {
    close: () => {
      if (ws) {
        ws.close();
        ws = null;
        isConnected = false;
      }
    },
    isConnected: () => isConnected,
  };
}

// ==================== Mock WebSocket Wrapper ====================

function createMockWebSocketConnection(
  reportId: string,
  companyName: string,
  callbacks: WebSocketCallbacks
): WebSocketConnection {
  let mockWs: MockWebSocket | null = null;
  let isConnected = false;

  mockWs = createMockWebSocket(reportId, companyName, {
    onEvent: callbacks.onEvent,
    onOpen: () => {
      isConnected = true;
      callbacks.onOpen?.();
    },
    onClose: () => {
      isConnected = false;
      callbacks.onClose?.();
    },
    onError: callbacks.onError,
    speed: 2, // 2x hızlı (demo için)
  });

  // Başlat
  mockWs.start();

  return {
    close: () => {
      if (mockWs) {
        mockWs.close();
        mockWs = null;
        isConnected = false;
      }
    },
    isConnected: () => isConnected,
  };
}

// ==================== Main Factory ====================

/**
 * WebSocket bağlantısı oluştur
 * Mock modda MockWebSocket, aksi halde gerçek WebSocket kullanır
 */
export function connectWebSocket(
  reportId: string,
  companyName: string,
  callbacks: WebSocketCallbacks
): WebSocketConnection {
  if (USE_MOCK) {
    return createMockWebSocketConnection(reportId, companyName, callbacks);
  }
  return createRealWebSocket(reportId, callbacks);
}

// ==================== Export Config ====================

export const wsConfig = {
  baseUrl: WS_BASE_URL,
  useMock: USE_MOCK,
};

export type { WebSocketConnectionState };
