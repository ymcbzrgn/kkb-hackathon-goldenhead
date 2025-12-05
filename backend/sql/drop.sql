-- KKB Firma İstihbarat - Drop All
-- DİKKAT: Bu script tüm verileri siler!

-- ============================================
-- Drop Tables (reverse order due to FKs)
-- ============================================

DROP TABLE IF EXISTS report_history CASCADE;
DROP TABLE IF EXISTS websocket_sessions CASCADE;
DROP TABLE IF EXISTS council_decisions CASCADE;
DROP TABLE IF EXISTS agent_results CASCADE;
DROP TABLE IF EXISTS reports CASCADE;
DROP TABLE IF EXISTS companies CASCADE;
DROP TABLE IF EXISTS categories CASCADE;

-- ============================================
-- Drop Types
-- ============================================

DROP TYPE IF EXISTS report_status CASCADE;
DROP TYPE IF EXISTS risk_level CASCADE;
DROP TYPE IF EXISTS decision_type CASCADE;
DROP TYPE IF EXISTS agent_status CASCADE;

-- ============================================
-- Drop Functions
-- ============================================

DROP FUNCTION IF EXISTS update_updated_at_column CASCADE;
DROP FUNCTION IF EXISTS increment_company_reports CASCADE;

-- ============================================
-- Drop Extensions (optional, usually keep these)
-- ============================================

-- DROP EXTENSION IF EXISTS "uuid-ossp";
-- DROP EXTENSION IF EXISTS "pg_trgm";

-- ============================================
-- Verify
-- ============================================

DO $$
BEGIN
    RAISE NOTICE 'All tables and types dropped successfully!';
END $$;
