/**
 * API Service
 * REST API client - Mock/Real switch destekli
 */

import type {
  ApiResponse,
  PaginatedResponse,
  ReportListItem,
  ReportDetail,
  CreateReportRequest,
  CreateReportResponse,
  DeleteReportResponse,
  HealthCheckResponse,
  ReportsQueryParams,
} from '@/types';
import * as mockApi from '@/mocks/mockApi';

// ==================== Config ====================

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';

// ==================== Fetch Wrapper ====================

async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<ApiResponse<T>> {
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    });

    const data = await response.json();
    return data as ApiResponse<T>;
  } catch (error) {
    return {
      success: false,
      data: null,
      error: {
        code: 'NETWORK_ERROR',
        message: error instanceof Error ? error.message : 'Bağlantı hatası',
      },
    };
  }
}

// ==================== API Functions ====================

/**
 * POST /api/reports - Yeni rapor oluştur
 */
export async function createReport(
  request: CreateReportRequest
): Promise<ApiResponse<CreateReportResponse>> {
  if (USE_MOCK) {
    return mockApi.createReport(request);
  }

  return fetchApi<CreateReportResponse>('/reports', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

/**
 * GET /api/reports - Rapor listesi
 */
export async function getReports(
  params?: ReportsQueryParams
): Promise<ApiResponse<PaginatedResponse<ReportListItem>>> {
  if (USE_MOCK) {
    return mockApi.getReports(params);
  }

  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set('page', String(params.page));
  if (params?.limit) searchParams.set('limit', String(params.limit));
  if (params?.status) searchParams.set('status', params.status);
  if (params?.sort) searchParams.set('sort', params.sort);

  const query = searchParams.toString();
  return fetchApi<PaginatedResponse<ReportListItem>>(
    `/reports${query ? `?${query}` : ''}`
  );
}

/**
 * GET /api/reports/:id - Rapor detayı
 */
export async function getReport(id: string): Promise<ApiResponse<ReportDetail>> {
  if (USE_MOCK) {
    return mockApi.getReport(id);
  }

  return fetchApi<ReportDetail>(`/reports/${id}`);
}

/**
 * DELETE /api/reports/:id - Rapor sil
 */
export async function deleteReport(id: string): Promise<ApiResponse<DeleteReportResponse>> {
  if (USE_MOCK) {
    return mockApi.deleteReport(id);
  }

  return fetchApi<DeleteReportResponse>(`/reports/${id}`, {
    method: 'DELETE',
  });
}

/**
 * GET /api/reports/:id/pdf - PDF indir
 */
export async function downloadReportPdf(id: string): Promise<Blob | null> {
  if (USE_MOCK) {
    // Mock modda PDF yok
    console.warn('PDF download mock modda desteklenmiyor');
    return null;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/reports/${id}/pdf`);
    if (!response.ok) return null;
    return response.blob();
  } catch {
    return null;
  }
}

/**
 * GET /api/health - Health check
 */
export async function healthCheck(): Promise<ApiResponse<HealthCheckResponse>> {
  if (USE_MOCK) {
    return mockApi.healthCheck();
  }

  return fetchApi<HealthCheckResponse>('/health');
}

// ==================== Export Config ====================

export const apiConfig = {
  baseUrl: API_BASE_URL,
  useMock: USE_MOCK,
};
