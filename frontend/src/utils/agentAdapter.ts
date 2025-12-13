/**
 * Backend agent_results formatini frontend AgentResults formatina donusturur
 *
 * Backend'den gelen format (wrapped):
 * {
 *   "tsg": { "status": "completed", "duration_seconds": 50, "data": {...} },
 *   "ihale": { "status": "completed", "duration_seconds": 1, "data": {...} },
 *   "news": { "status": "completed", "duration_seconds": 2, "data": {...} }
 * }
 *
 * ONEMLI: Frontend component'leri artik direkt backend verisini kabul ediyor.
 * Bu adapter sadece wrapper (status, duration_seconds) bilgilerini korur
 * ve data'yi olduğu gibi geçirir.
 */

// Backend'den gelen wrapper format
export interface WrappedAgentResult {
  status?: string;
  duration_seconds?: number;
  data?: unknown;
  summary?: string;
  key_findings?: string[];
  warning_flags?: string[];
}

// Backend'den gelen tam response
export interface RawAgentResults {
  tsg?: WrappedAgentResult | null;
  ihale?: WrappedAgentResult | null;
  news?: WrappedAgentResult | null;
}

// Frontend'e dondurulen format (data tipi artik any)
interface TransformedAgentResult {
  status: 'pending' | 'running' | 'completed' | 'failed';
  duration_seconds: number | null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data: any;
}

interface TransformedAgentResults {
  tsg: TransformedAgentResult;
  ihale: TransformedAgentResult;
  news: TransformedAgentResult;
}

/**
 * Tek bir agent sonucunu transform et - data'yi olduğu gibi geçir
 */
function transformAgent(wrapped: WrappedAgentResult | null | undefined): TransformedAgentResult {
  if (!wrapped) {
    return { status: 'pending', duration_seconds: null, data: null };
  }

  const status = (wrapped.status as TransformedAgentResult['status']) || 'pending';
  const duration_seconds = wrapped.duration_seconds || null;

  // Data'yi olduğu gibi geçir - component'ler backend formatını direkt kullanıyor
  return {
    status,
    duration_seconds,
    data: wrapped.data || null
  };
}

/**
 * Ana transform fonksiyonu - Backend agent_results'i frontend formatina donusturur
 * Artik data transformation yapmiyor, sadece wrapper bilgilerini koruyor.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function transformAgentResults(raw: any): TransformedAgentResults {
  const typedRaw = raw as RawAgentResults | null | undefined;
  return {
    tsg: transformAgent(typedRaw?.tsg),
    ihale: transformAgent(typedRaw?.ihale),
    news: transformAgent(typedRaw?.news)
  };
}
