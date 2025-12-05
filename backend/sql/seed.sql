-- KKB Firma İstihbarat - Seed Data
-- Test ve demo verileri

-- ============================================
-- Categories (Sektörler)
-- ============================================

INSERT INTO categories (name, code, description) VALUES
    ('Teknoloji', 'TECH', 'Yazılım, donanım, IT hizmetleri'),
    ('Üretim', 'MFG', 'İmalat ve üretim sektörü'),
    ('Perakende', 'RETAIL', 'Perakende satış ve e-ticaret'),
    ('Finans', 'FIN', 'Finans ve bankacılık'),
    ('Sağlık', 'HEALTH', 'Sağlık hizmetleri ve ilaç'),
    ('İnşaat', 'CONST', 'İnşaat ve gayrimenkul'),
    ('Tarım', 'AGRI', 'Tarım ve hayvancılık'),
    ('Lojistik', 'LOG', 'Taşımacılık ve lojistik'),
    ('Enerji', 'ENERGY', 'Enerji üretim ve dağıtım'),
    ('Turizm', 'TOURISM', 'Turizm ve otelcilik')
ON CONFLICT (code) DO NOTHING;

-- ============================================
-- Sample Companies
-- ============================================

INSERT INTO companies (id, name, tax_no, trade_registry_no, sector, city, address) VALUES
    ('550e8400-e29b-41d4-a716-446655440001', 'ABC Teknoloji A.Ş.', '1234567890', '123456', 'Teknoloji', 'İstanbul', 'Maslak, Sarıyer'),
    ('550e8400-e29b-41d4-a716-446655440002', 'XYZ Üretim Ltd. Şti.', '9876543210', '654321', 'Üretim', 'Ankara', 'OSTİM, Yenimahalle'),
    ('550e8400-e29b-41d4-a716-446655440003', 'Demo Lojistik A.Ş.', '5555555555', '555555', 'Lojistik', 'İzmir', 'Alsancak, Konak'),
    ('550e8400-e29b-41d4-a716-446655440004', 'Test Holding A.Ş.', '1111111111', '111111', 'Finans', 'İstanbul', 'Levent, Beşiktaş'),
    ('550e8400-e29b-41d4-a716-446655440005', 'Örnek İnşaat A.Ş.', '2222222222', '222222', 'İnşaat', 'Bursa', 'Nilüfer')
ON CONFLICT (tax_no) DO NOTHING;

-- ============================================
-- Sample Reports
-- ============================================

-- Tamamlanmış rapor - Düşük risk
INSERT INTO reports (
    id, company_name, company_tax_no, company_id, status,
    final_score, risk_level, decision,
    created_at, completed_at, duration_seconds,
    tsg_data, ihale_data, news_data
) VALUES (
    '660e8400-e29b-41d4-a716-446655440001',
    'ABC Teknoloji A.Ş.',
    '1234567890',
    '550e8400-e29b-41d4-a716-446655440001',
    'completed',
    25,
    'dusuk',
    'onay',
    NOW() - INTERVAL '2 days',
    NOW() - INTERVAL '2 days' + INTERVAL '35 minutes',
    2100,
    '{"kurulus_tarihi": "2018-03-15", "sermaye": 5000000, "ortaklar": [{"ad": "Ahmet Yılmaz", "pay_orani": 60}]}',
    '{"yasak_durumu": false, "aktif_yasak": null}',
    '{"toplam_haber": 10, "pozitif": 7, "negatif": 1, "sentiment_score": 0.6}'
) ON CONFLICT DO NOTHING;

-- Tamamlanmış rapor - Orta-yüksek risk
INSERT INTO reports (
    id, company_name, company_tax_no, company_id, status,
    final_score, risk_level, decision,
    created_at, completed_at, duration_seconds,
    tsg_data, ihale_data, news_data
) VALUES (
    '660e8400-e29b-41d4-a716-446655440002',
    'XYZ Üretim Ltd. Şti.',
    '9876543210',
    '550e8400-e29b-41d4-a716-446655440002',
    'completed',
    62,
    'orta_yuksek',
    'inceleme_gerek',
    NOW() - INTERVAL '5 days',
    NOW() - INTERVAL '5 days' + INTERVAL '40 minutes',
    2400,
    '{"kurulus_tarihi": "2015-06-20", "sermaye": 2000000, "yonetici_degisiklikleri": [{"tarih": "2024-01-15", "eski": "Ali", "yeni": "Veli"}]}',
    '{"yasak_durumu": false, "gecmis_yasaklar": [{"sebep": "İhale ihlali", "bitis": "2022-06-01"}]}',
    '{"toplam_haber": 5, "pozitif": 1, "negatif": 3, "sentiment_score": -0.4}'
) ON CONFLICT DO NOTHING;

-- Tamamlanmış rapor - Şartlı onay
INSERT INTO reports (
    id, company_name, company_tax_no, company_id, status,
    final_score, risk_level, decision,
    created_at, completed_at, duration_seconds
) VALUES (
    '660e8400-e29b-41d4-a716-446655440003',
    'Demo Lojistik A.Ş.',
    '5555555555',
    '550e8400-e29b-41d4-a716-446655440003',
    'completed',
    38,
    'orta_dusuk',
    'sartli_onay',
    NOW() - INTERVAL '10 days',
    NOW() - INTERVAL '10 days' + INTERVAL '32 minutes',
    1920
) ON CONFLICT DO NOTHING;

-- İşleme bekleyen rapor
INSERT INTO reports (
    id, company_name, company_tax_no, status, created_at
) VALUES (
    '660e8400-e29b-41d4-a716-446655440004',
    'Test Holding A.Ş.',
    '1111111111',
    'processing',
    NOW() - INTERVAL '5 minutes'
) ON CONFLICT DO NOTHING;

-- ============================================
-- Sample Agent Results
-- ============================================

-- TSG Agent sonucu
INSERT INTO agent_results (
    id, report_id, agent_id, agent_name, status,
    data, summary, key_findings, warning_flags,
    started_at, completed_at, duration_seconds
) VALUES (
    '770e8400-e29b-41d4-a716-446655440001',
    '660e8400-e29b-41d4-a716-446655440001',
    'tsg_agent',
    'TSG Agent',
    'completed',
    '{"kurulus_tarihi": "2018-03-15", "sermaye": 5000000, "tsg_ilan_sayisi": 3}',
    'Firma 2018 yılında kurulmuş, sermayesi 5M TL',
    '["Sermaye artışı tespit edildi"]',
    '[]',
    NOW() - INTERVAL '2 days',
    NOW() - INTERVAL '2 days' + INTERVAL '10 minutes',
    600
) ON CONFLICT DO NOTHING;

-- İhale Agent sonucu
INSERT INTO agent_results (
    id, report_id, agent_id, agent_name, status,
    data, summary, key_findings, warning_flags,
    started_at, completed_at, duration_seconds
) VALUES (
    '770e8400-e29b-41d4-a716-446655440002',
    '660e8400-e29b-41d4-a716-446655440001',
    'ihale_agent',
    'İhale Agent',
    'completed',
    '{"yasak_durumu": false, "aktif_yasak": null, "gecmis_yasaklar": []}',
    'İhale yasağı bulunmamaktadır',
    '["İhale yasağı yok"]',
    '[]',
    NOW() - INTERVAL '2 days',
    NOW() - INTERVAL '2 days' + INTERVAL '5 minutes',
    300
) ON CONFLICT DO NOTHING;

-- ============================================
-- Sample Council Decision
-- ============================================

INSERT INTO council_decisions (
    id, report_id, final_score, risk_level, decision, consensus,
    conditions, summary, initial_scores, final_scores,
    started_at, completed_at, duration_seconds
) VALUES (
    '880e8400-e29b-41d4-a716-446655440001',
    '660e8400-e29b-41d4-a716-446655440001',
    25,
    'dusuk',
    'onay',
    0.88,
    '[]',
    'Komite firmanın düşük riskli olduğuna karar vermiştir.',
    '{"risk_analyst": 35, "business_analyst": 20, "legal_expert": 25, "media_analyst": 22, "sector_expert": 28}',
    '{"risk_analyst": 30, "business_analyst": 20, "legal_expert": 25, "media_analyst": 22, "sector_expert": 28}',
    NOW() - INTERVAL '2 days' + INTERVAL '15 minutes',
    NOW() - INTERVAL '2 days' + INTERVAL '35 minutes',
    1200
) ON CONFLICT DO NOTHING;

-- ============================================
-- Sample Report History
-- ============================================

INSERT INTO report_history (report_id, action, old_value, new_value) VALUES
    ('660e8400-e29b-41d4-a716-446655440001', 'created', NULL, '{"status": "pending"}'),
    ('660e8400-e29b-41d4-a716-446655440001', 'status_changed', '{"status": "pending"}', '{"status": "processing"}'),
    ('660e8400-e29b-41d4-a716-446655440001', 'completed', '{"status": "processing"}', '{"status": "completed", "final_score": 25}')
ON CONFLICT DO NOTHING;

-- ============================================
-- Verify Data
-- ============================================

DO $$
BEGIN
    RAISE NOTICE 'Seed data inserted successfully!';
    RAISE NOTICE 'Categories: %', (SELECT COUNT(*) FROM categories);
    RAISE NOTICE 'Companies: %', (SELECT COUNT(*) FROM companies);
    RAISE NOTICE 'Reports: %', (SELECT COUNT(*) FROM reports);
    RAISE NOTICE 'Agent Results: %', (SELECT COUNT(*) FROM agent_results);
    RAISE NOTICE 'Council Decisions: %', (SELECT COUNT(*) FROM council_decisions);
END $$;
