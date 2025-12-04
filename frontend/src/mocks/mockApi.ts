/**
 * Mock API Service
 * Backend hazır olana kadar kullanılacak mock API
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
import { 
  MOCK_REPORTS, 
  MOCK_REPORT_DETAIL, 
  delay 
} from './mockData';

// ==================== Config ====================

const MOCK_DELAY_MS = 500; // Gerçekçi gecikme simülasyonu

// ==================== Helper Functions ====================

function success<T>(data: T): ApiResponse<T> {
  return { success: true, data, error: null };
}

function error<T>(code: string, message: string): ApiResponse<T> {
  return { success: false, data: null, error: { code, message } };
}

function generateUUID(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

// ==================== Mock API Functions ====================

/**
 * POST /api/reports - Yeni rapor oluştur
 */
export async function createReport(
  request: CreateReportRequest
): Promise<ApiResponse<CreateReportResponse>> {
  await delay(MOCK_DELAY_MS);

  // Validation
  if (!request.company_name) {
    return error('VALIDATION_ERROR', 'company_name zorunlu');
  }
  if (request.company_name.length < 2) {
    return error('COMPANY_NAME_TOO_SHORT', 'Firma adı en az 2 karakter olmalı');
  }

  const reportId = generateUUID();
  
  return success({
    report_id: reportId,
    status: 'pending',
    websocket_url: `/ws/${reportId}`,
  });
}

/**
 * GET /api/reports - Rapor listesi
 */
export async function getReports(
  params?: ReportsQueryParams
): Promise<ApiResponse<PaginatedResponse<ReportListItem>>> {
  await delay(MOCK_DELAY_MS);

  let items = [...MOCK_REPORTS];

  // Status filter
  if (params?.status) {
    items = items.filter(r => r.status === params.status);
  }

  // Sort
  if (params?.sort) {
    const sortField = params.sort.replace('-', '') as keyof ReportListItem;
    const isDesc = params.sort.startsWith('-');
    
    items.sort((a, b) => {
      const aVal = a[sortField];
      const bVal = b[sortField];
      
      if (aVal === null) return 1;
      if (bVal === null) return -1;
      if (aVal < bVal) return isDesc ? 1 : -1;
      if (aVal > bVal) return isDesc ? -1 : 1;
      return 0;
    });
  }

  // Pagination
  const page = params?.page || 1;
  const limit = Math.min(params?.limit || 10, 50);
  const total = items.length;
  const start = (page - 1) * limit;
  const paginatedItems = items.slice(start, start + limit);

  return success({
    items: paginatedItems,
    pagination: {
      page,
      limit,
      total_items: total,
      total_pages: Math.ceil(total / limit),
      has_next: start + limit < total,
      has_prev: page > 1,
    },
  });
}

/**
 * GET /api/reports/:id - Rapor detayı
 */
export async function getReport(id: string): Promise<ApiResponse<ReportDetail>> {
  await delay(MOCK_DELAY_MS);

  // İlk mock raporu detaylı döndür
  if (id === MOCK_REPORTS[0].id) {
    return success(MOCK_REPORT_DETAIL);
  }

  // Diğer raporlar için basit detay oluştur
  const report = MOCK_REPORTS.find(r => r.id === id);
  
  if (!report) {
    return error('REPORT_NOT_FOUND', 'Rapor bulunamadı');
  }

  // Basit detay (agent sonuçları olmadan)
  const detail: ReportDetail = {
    ...report,
    agent_results: {
      tsg: { status: report.status === 'completed' ? 'completed' : 'pending', duration_seconds: null, data: null },
      ihale: { status: report.status === 'completed' ? 'completed' : 'pending', duration_seconds: null, data: null },
      news: { status: report.status === 'completed' ? 'completed' : 'pending', duration_seconds: null, data: null },
    },
    council_decision: null,
  };

  return success(detail);
}

/**
 * DELETE /api/reports/:id - Rapor sil
 */
export async function deleteReport(id: string): Promise<ApiResponse<DeleteReportResponse>> {
  await delay(MOCK_DELAY_MS);

  const report = MOCK_REPORTS.find(r => r.id === id);
  
  if (!report) {
    return error('REPORT_NOT_FOUND', 'Rapor bulunamadı');
  }

  if (report.status === 'processing') {
    return error('REPORT_IN_PROGRESS', 'İşlemi devam eden rapor silinemez');
  }

  return success({ deleted: true, id });
}

/**
 * GET /api/health - Health check
 */
export async function healthCheck(): Promise<ApiResponse<HealthCheckResponse>> {
  await delay(100);

  return success({
    status: 'healthy',
    version: '1.0.0',
    timestamp: new Date().toISOString(),
    services: {
      database: 'up',
      redis: 'up',
      celery: 'up',
    },
  });
}
