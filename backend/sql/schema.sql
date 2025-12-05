-- KKB Firma İstihbarat - Database Schema
-- PostgreSQL 15+

-- ============================================
-- Extensions
-- ============================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- Fuzzy search için

-- ============================================
-- Enums
-- ============================================

-- Rapor durumu
CREATE TYPE report_status AS ENUM (
    'pending',
    'processing',
    'completed',
    'failed'
);

-- Risk seviyesi
CREATE TYPE risk_level AS ENUM (
    'dusuk',
    'orta_dusuk',
    'orta',
    'orta_yuksek',
    'yuksek'
);

-- Karar tipi
CREATE TYPE decision_type AS ENUM (
    'onay',
    'sartli_onay',
    'red',
    'inceleme_gerek'
);

-- Agent durumu
CREATE TYPE agent_status AS ENUM (
    'pending',
    'running',
    'completed',
    'failed'
);

-- ============================================
-- Tables
-- ============================================

-- Kategoriler (sektörler)
CREATE TABLE IF NOT EXISTS categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    code VARCHAR(20) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Firmalar (cache amaçlı)
CREATE TABLE IF NOT EXISTS companies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    tax_no VARCHAR(11) UNIQUE,
    trade_registry_no VARCHAR(20),
    sector VARCHAR(100),
    city VARCHAR(100),
    address TEXT,
    cached_data JSONB DEFAULT '{}',
    last_report_id UUID,
    total_reports INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Ana rapor tablosu
CREATE TABLE IF NOT EXISTS reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Firma bilgileri
    company_name VARCHAR(255) NOT NULL,
    company_tax_no VARCHAR(11),
    company_id UUID REFERENCES companies(id),

    -- Durum
    status report_status DEFAULT 'pending',

    -- Sonuçlar
    final_score INTEGER CHECK (final_score >= 0 AND final_score <= 100),
    risk_level risk_level,
    decision decision_type,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,

    -- JSON verileri
    tsg_data JSONB,
    ihale_data JSONB,
    news_data JSONB,
    council_data JSONB,

    -- Error tracking
    error_message TEXT,
    error_code VARCHAR(50)
);

-- Agent sonuçları
CREATE TABLE IF NOT EXISTS agent_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE,

    -- Agent bilgileri
    agent_id VARCHAR(50) NOT NULL,
    agent_name VARCHAR(100),
    status agent_status DEFAULT 'pending',

    -- Sonuçlar
    data JSONB,
    summary TEXT,
    key_findings JSONB DEFAULT '[]',
    warning_flags JSONB DEFAULT '[]',

    -- Timing
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,

    -- Error
    error_message TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Komite kararları
CREATE TABLE IF NOT EXISTS council_decisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE,

    -- Skorlar
    final_score INTEGER NOT NULL CHECK (final_score >= 0 AND final_score <= 100),
    risk_level risk_level NOT NULL,
    decision decision_type NOT NULL,
    consensus DECIMAL(3, 2) CHECK (consensus >= 0 AND consensus <= 1),

    -- Detaylar
    conditions JSONB DEFAULT '[]',
    summary TEXT,

    -- Üye skorları
    initial_scores JSONB DEFAULT '{}',
    final_scores JSONB DEFAULT '{}',

    -- Transcript
    transcript JSONB DEFAULT '[]',

    -- Timing
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- WebSocket session tracking
CREATE TABLE IF NOT EXISTS websocket_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    session_id VARCHAR(100) NOT NULL,
    connected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    disconnected_at TIMESTAMP WITH TIME ZONE,
    client_info JSONB DEFAULT '{}'
);

-- ============================================
-- Audit / History Tables
-- ============================================

-- Rapor geçmişi (audit log)
CREATE TABLE IF NOT EXISTS report_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL,  -- created, status_changed, completed, failed
    old_value JSONB,
    new_value JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- Functions
-- ============================================

-- Updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Auto-increment total_reports on company
CREATE OR REPLACE FUNCTION increment_company_reports()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.company_id IS NOT NULL THEN
        UPDATE companies
        SET total_reports = total_reports + 1,
            last_report_id = NEW.id
        WHERE id = NEW.company_id;
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- ============================================
-- Triggers
-- ============================================

-- Companies updated_at trigger
CREATE TRIGGER update_companies_updated_at
    BEFORE UPDATE ON companies
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Increment company reports count
CREATE TRIGGER increment_company_reports_trigger
    AFTER INSERT ON reports
    FOR EACH ROW
    EXECUTE FUNCTION increment_company_reports();

-- ============================================
-- Comments
-- ============================================

COMMENT ON TABLE reports IS 'Ana rapor tablosu - her firma analizi için bir kayıt';
COMMENT ON TABLE agent_results IS 'Agent sonuçları - TSG, İhale, Haber agent sonuçları';
COMMENT ON TABLE council_decisions IS 'Komite kararları - 6 kişilik AI komite kararları';
COMMENT ON TABLE companies IS 'Firma cache tablosu - önceki aramalardan cache';
COMMENT ON COLUMN reports.final_score IS 'Risk skoru (0-100, 0=risk yok, 100=çok riskli)';
COMMENT ON COLUMN council_decisions.consensus IS 'Konsensüs oranı (0-1)';
