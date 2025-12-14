/**
 * WebSocket Service
 * Real WebSocket + Mock WebSocket switch
 */

import type { WebSocketEvent, WebSocketConnectionState } from '@/types';
import { createMockWebSocket, MockWebSocket } from '@/mocks/mockWebSocket';

// ==================== Config ====================

const WS_BASE_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';
const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';

// Reconnection config
const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_DELAY_MS = 2000; // 2 saniye
const RECONNECT_DELAY_MAX_MS = 30000; // Max 30 saniye

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
  let reconnectAttempts = 0;
  let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
  let isManualClose = false; // Kullanıcı tarafından kapatıldı mı?

  const connect = () => {
    // Eski bağlantıyı temizle (connection leak önleme)
    if (ws) {
      ws.onopen = null;
      ws.onmessage = null;
      ws.onerror = null;
      ws.onclose = null;
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close();
      }
      ws = null;
    }

    try {
      ws = new WebSocket(url);

      ws.onopen = () => {
        isConnected = true;
        reconnectAttempts = 0; // Başarılı bağlantıda sıfırla
        callbacks.onOpen?.();
        console.log(`[WS] Connected to ${reportId}`);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as WebSocketEvent;
          callbacks.onEvent(data);
        } catch (err) {
          console.error('WebSocket message parse error:', err);
        }
      };

      ws.onerror = (error) => {
        console.error('[WS] Error:', error);
        callbacks.onError?.('WebSocket bağlantı hatası');
      };

      ws.onclose = (event) => {
        isConnected = false;
        console.log(`[WS] Disconnected: code=${event.code}, reason=${event.reason}`);

        // Manuel kapatma değilse ve max deneme aşılmadıysa yeniden bağlan
        if (!isManualClose && reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
          const delay = Math.min(
            RECONNECT_DELAY_MS * Math.pow(2, reconnectAttempts), // Exponential backoff
            RECONNECT_DELAY_MAX_MS
          );
          reconnectAttempts++;
          console.log(`[WS] Reconnecting in ${delay}ms (attempt ${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})`);

          reconnectTimeout = setTimeout(() => {
            connect();
          }, delay);
        } else {
          callbacks.onClose?.();
          if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
            callbacks.onError?.('Bağlantı kurulamadı, lütfen sayfayı yenileyin');
          }
        }
      };
    } catch (err) {
      callbacks.onError?.(err instanceof Error ? err.message : 'WebSocket hatası');
    }
  };

  // İlk bağlantıyı başlat
  connect();

  return {
    close: () => {
      isManualClose = true; // Reconnect'i engelle
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
        reconnectTimeout = null;
      }
      if (ws) {
        ws.onopen = null;
        ws.onmessage = null;
        ws.onerror = null;
        ws.onclose = null;
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
