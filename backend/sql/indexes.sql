-- KKB Firma İstihbarat - Database Indexes
-- Performance optimizasyonu için indexler

-- ============================================
-- Reports Table Indexes
-- ============================================

-- Status ile filtreleme (en sık kullanılan)
CREATE INDEX IF NOT EXISTS idx_reports_status
    ON reports(status);

-- Firma adı araması (LIKE için)
CREATE INDEX IF NOT EXISTS idx_reports_company_name_trgm
    ON reports USING gin(company_name gin_trgm_ops);

-- Vergi no ile arama
CREATE INDEX IF NOT EXISTS idx_reports_company_tax_no
    ON reports(company_tax_no);

-- Tarih sıralaması
CREATE INDEX IF NOT EXISTS idx_reports_created_at
    ON reports(created_at DESC);

-- Company ID ile join
CREATE INDEX IF NOT EXISTS idx_reports_company_id
    ON reports(company_id);

-- Composite: Status + Created (liste görünümü için)
CREATE INDEX IF NOT EXISTS idx_reports_status_created
    ON reports(status, created_at DESC);

-- Risk seviyesi filtreleme
CREATE INDEX IF NOT EXISTS idx_reports_risk_level
    ON reports(risk_level);

-- Karar filtreleme
CREATE INDEX IF NOT EXISTS idx_reports_decision
    ON reports(decision);

-- ============================================
-- Companies Table Indexes
-- ============================================

-- İsim araması (fuzzy search)
CREATE INDEX IF NOT EXISTS idx_companies_name_trgm
    ON companies USING gin(name gin_trgm_ops);

-- Vergi no (unique zaten var ama explicit index)
CREATE INDEX IF NOT EXISTS idx_companies_tax_no
    ON companies(tax_no);

-- Sektör filtreleme
CREATE INDEX IF NOT EXISTS idx_companies_sector
    ON companies(sector);

-- Şehir filtreleme
CREATE INDEX IF NOT EXISTS idx_companies_city
    ON companies(city);

-- ============================================
-- Agent Results Table Indexes
-- ============================================

-- Report ID ile join
CREATE INDEX IF NOT EXISTS idx_agent_results_report_id
    ON agent_results(report_id);

-- Agent ID filtreleme
CREATE INDEX IF NOT EXISTS idx_agent_results_agent_id
    ON agent_results(agent_id);

-- Status filtreleme
CREATE INDEX IF NOT EXISTS idx_agent_results_status
    ON agent_results(status);

-- Composite: Report + Agent
CREATE INDEX IF NOT EXISTS idx_agent_results_report_agent
    ON agent_results(report_id, agent_id);

-- ============================================
-- Council Decisions Table Indexes
-- ============================================

-- Report ID ile join
CREATE INDEX IF NOT EXISTS idx_council_decisions_report_id
    ON council_decisions(report_id);

-- Risk seviyesi filtreleme
CREATE INDEX IF NOT EXISTS idx_council_decisions_risk_level
    ON council_decisions(risk_level);

-- Karar filtreleme
CREATE INDEX IF NOT EXISTS idx_council_decisions_decision
    ON council_decisions(decision);

-- ============================================
-- WebSocket Sessions Table Indexes
-- ============================================

-- Report ID
CREATE INDEX IF NOT EXISTS idx_websocket_sessions_report_id
    ON websocket_sessions(report_id);

-- Active sessions
CREATE INDEX IF NOT EXISTS idx_websocket_sessions_active
    ON websocket_sessions(report_id)
    WHERE disconnected_at IS NULL;

-- ============================================
-- Report History Table Indexes
-- ============================================

-- Report ID
CREATE INDEX IF NOT EXISTS idx_report_history_report_id
    ON report_history(report_id);

-- Action type
CREATE INDEX IF NOT EXISTS idx_report_history_action
    ON report_history(action);

-- Tarih sıralaması
CREATE INDEX IF NOT EXISTS idx_report_history_created_at
    ON report_history(created_at DESC);

-- ============================================
-- JSONB Indexes (GIN)
-- ============================================

-- TSG data içinde arama
CREATE INDEX IF NOT EXISTS idx_reports_tsg_data
    ON reports USING gin(tsg_data);

-- İhale data içinde arama
CREATE INDEX IF NOT EXISTS idx_reports_ihale_data
    ON reports USING gin(ihale_data);

-- News data içinde arama
CREATE INDEX IF NOT EXISTS idx_reports_news_data
    ON reports USING gin(news_data);

-- Council data içinde arama
CREATE INDEX IF NOT EXISTS idx_reports_council_data
    ON reports USING gin(council_data);

-- Agent key_findings içinde arama
CREATE INDEX IF NOT EXISTS idx_agent_results_key_findings
    ON agent_results USING gin(key_findings);

-- Agent warning_flags içinde arama
CREATE INDEX IF NOT EXISTS idx_agent_results_warning_flags
    ON agent_results USING gin(warning_flags);

-- ============================================
-- Partial Indexes
-- ============================================

-- Sadece tamamlanmış raporlar
CREATE INDEX IF NOT EXISTS idx_reports_completed
    ON reports(completed_at DESC)
    WHERE status = 'completed';

-- Sadece başarısız raporlar (debugging için)
CREATE INDEX IF NOT EXISTS idx_reports_failed
    ON reports(created_at DESC)
    WHERE status = 'failed';

-- Yüksek riskli raporlar
CREATE INDEX IF NOT EXISTS idx_reports_high_risk
    ON reports(created_at DESC)
    WHERE risk_level IN ('orta_yuksek', 'yuksek');
