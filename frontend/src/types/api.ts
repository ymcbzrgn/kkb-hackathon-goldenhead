/**
 * API Base Types
 * API.md'deki tanımlardan alınmıştır
 */

// ==================== Base Response Types ====================

/**
 * Tüm API response'ları bu formatta döner
 */
export interface ApiResponse<T> {
  success: boolean;
  data: T | null;
  error: ApiError | null;
}

export interface ApiError {
  code: string;
  message: string;
}

// ==================== Pagination ====================

export interface Pagination {
  page: number;
  limit: number;
  total_items: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface PaginatedResponse<T> {
  items: T[];
  pagination: Pagination;
}

// ==================== Request Types ====================

export interface CreateReportRequest {
  company_name: string;
  company_tax_no?: string;
}

export interface CreateReportResponse {
  report_id: string;
  status: ReportStatus;
  websocket_url: string;
}

export interface DeleteReportResponse {
  deleted: boolean;
  id: string;
}

export interface HealthCheckResponse {
  status: 'healthy' | 'unhealthy';
  version: string;
  timestamp: string;
  services: {
    database: 'up' | 'down';
    redis: 'up' | 'down';
    celery: 'up' | 'down';
  };
}

// ==================== Enums ====================

export type ReportStatus = 'pending' | 'processing' | 'completed' | 'failed';

export type RiskLevel = 'dusuk' | 'orta_dusuk' | 'orta' | 'orta_yuksek' | 'yuksek';

export type Decision = 'onay' | 'sartli_onay' | 'red' | 'inceleme_gerek';

export type AgentType = 'tsg_agent' | 'ihale_agent' | 'news_agent';

export type AgentStatus = 'pending' | 'running' | 'completed' | 'failed';

// ==================== Query Params ====================

export interface ReportsQueryParams {
  page?: number;
  limit?: number;
  status?: ReportStatus;
  sort?: 'created_at' | '-created_at' | 'company_name';
}
