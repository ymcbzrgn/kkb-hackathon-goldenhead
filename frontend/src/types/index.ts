/**
 * Types Index
 * Tüm type tanımlarını tek yerden export eder
 */

// API Base Types
export type {
  ApiResponse,
  ApiError,
  Pagination,
  PaginatedResponse,
  CreateReportRequest,
  CreateReportResponse,
  DeleteReportResponse,
  HealthCheckResponse,
  ReportStatus,
  RiskLevel,
  Decision,
  AgentType,
  AgentStatus,
  ReportsQueryParams,
} from './api';

// Report Types
export type {
  ReportListItem,
  ReportDetail,
  ReportState,
} from './report';

// Agent Types
export type {
  AgentResult,
  AgentResults,
  TsgData,
  Ortak,
  YonetimKuruluUyesi,
  SermayeDegisikligi,
  YoneticiDegisikligi,
  IhaleData,
  YasakBilgisi,
  NewsData,
  HaberItem,
  AgentProgress,
  AgentsState,
} from './agent';

// Council Types
export type {
  CouncilPhase,
  CouncilMemberId,
  CouncilMember,
  CouncilScores,
  TranscriptEntry,
  CouncilDecision,
  CouncilState,
  ScoreRevision,
} from './council';

// WebSocket Types
export type {
  BaseEvent,
  JobStartedEvent,
  JobCompletedEvent,
  JobFailedEvent,
  AgentStartedEvent,
  AgentProgressEvent,
  AgentCompletedEvent,
  AgentFailedEvent,
  CouncilStartedEvent,
  CouncilPhaseChangedEvent,
  CouncilSpeakerChangedEvent,
  CouncilSpeechEvent,
  CouncilScoreRevisionEvent,
  CouncilDecisionEvent,
  WebSocketEvent,
  WebSocketConnectionState,
  WebSocketState,
} from './websocket';

// WebSocket Type Guards
export {
  isJobEvent,
  isAgentEvent,
  isCouncilEvent,
} from './websocket';
