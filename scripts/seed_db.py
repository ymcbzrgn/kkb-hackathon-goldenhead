#!/usr/bin/env python3
"""
Database Seeder
Test verileri ile veritabanını doldurur
"""
import os
import sys
from datetime import datetime, timedelta
from uuid import uuid4

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import models
try:
    from app.models.report import Report, ReportStatus, RiskLevel, Decision
    from app.models.company import Company, Category
    from app.models.council_decision import CouncilDecision as CouncilDecisionModel, AgentResult
    from app.core.database import Base
    from app.core.config import settings
except ImportError:
    print("Warning: Could not import models. Make sure you're in the correct directory.")
    print("Running with basic schema...")
    settings = None


def get_database_url():
    """Get database URL from environment or default"""
    return os.getenv(
        'DATABASE_URL',
        'postgresql://kkb:hackathon2024@localhost:5432/firma_istihbarat'
    )


def seed_categories(session):
    """Seed categories"""
    categories = [
        {"name": "Teknoloji", "code": "TECH"},
        {"name": "Üretim", "code": "MFG"},
        {"name": "Perakende", "code": "RETAIL"},
        {"name": "Finans", "code": "FIN"},
        {"name": "Sağlık", "code": "HEALTH"},
        {"name": "İnşaat", "code": "CONST"},
        {"name": "Tarım", "code": "AGRI"},
        {"name": "Lojistik", "code": "LOG"},
    ]

    for cat_data in categories:
        existing = session.query(Category).filter_by(code=cat_data["code"]).first()
        if not existing:
            category = Category(
                id=str(uuid4()),
                name=cat_data["name"],
                code=cat_data["code"]
            )
            session.add(category)

    session.commit()
    print(f"✓ Seeded {len(categories)} categories")


def seed_companies(session):
    """Seed sample companies"""
    companies = [
        {
            "name": "ABC Teknoloji A.Ş.",
            "tax_no": "1234567890",
            "trade_registry_no": "123456",
            "sector": "Teknoloji",
            "city": "İstanbul"
        },
        {
            "name": "XYZ Üretim Ltd. Şti.",
            "tax_no": "9876543210",
            "trade_registry_no": "654321",
            "sector": "Üretim",
            "city": "Ankara"
        },
        {
            "name": "Demo Lojistik A.Ş.",
            "tax_no": "5555555555",
            "trade_registry_no": "555555",
            "sector": "Lojistik",
            "city": "İzmir"
        },
    ]

    for comp_data in companies:
        existing = session.query(Company).filter_by(tax_no=comp_data["tax_no"]).first()
        if not existing:
            company = Company(
                id=str(uuid4()),
                name=comp_data["name"],
                tax_no=comp_data["tax_no"],
                trade_registry_no=comp_data["trade_registry_no"],
                sector=comp_data["sector"],
                city=comp_data["city"],
                cached_data={},
                created_at=datetime.utcnow()
            )
            session.add(company)

    session.commit()
    print(f"✓ Seeded {len(companies)} companies")


def seed_sample_reports(session):
    """Seed sample reports for testing"""
    sample_reports = [
        {
            "company_name": "Test Firması A.Ş.",
            "company_tax_no": "1111111111",
            "status": ReportStatus.COMPLETED,
            "final_score": 35,
            "risk_level": RiskLevel.ORTA_DUSUK,
            "decision": Decision.SARTLI_ONAY,
            "days_ago": 2
        },
        {
            "company_name": "Demo Şirketi Ltd.",
            "company_tax_no": "2222222222",
            "status": ReportStatus.COMPLETED,
            "final_score": 65,
            "risk_level": RiskLevel.ORTA_YUKSEK,
            "decision": Decision.INCELEME_GEREK,
            "days_ago": 5
        },
        {
            "company_name": "Örnek Holding A.Ş.",
            "company_tax_no": "3333333333",
            "status": ReportStatus.COMPLETED,
            "final_score": 20,
            "risk_level": RiskLevel.DUSUK,
            "decision": Decision.ONAY,
            "days_ago": 10
        },
        {
            "company_name": "İşleme Bekleyen Firma",
            "company_tax_no": "4444444444",
            "status": ReportStatus.PROCESSING,
            "final_score": None,
            "risk_level": None,
            "decision": None,
            "days_ago": 0
        },
    ]

    for report_data in sample_reports:
        existing = session.query(Report).filter_by(
            company_tax_no=report_data["company_tax_no"]
        ).first()

        if not existing:
            created_at = datetime.utcnow() - timedelta(days=report_data["days_ago"])
            completed_at = created_at + timedelta(minutes=35) if report_data["status"] == ReportStatus.COMPLETED else None

            report = Report(
                id=str(uuid4()),
                company_name=report_data["company_name"],
                company_tax_no=report_data["company_tax_no"],
                status=report_data["status"],
                final_score=report_data["final_score"],
                risk_level=report_data["risk_level"],
                decision=report_data["decision"],
                created_at=created_at,
                completed_at=completed_at,
                duration_seconds=2100 if completed_at else None
            )
            session.add(report)

    session.commit()
    print(f"✓ Seeded {len(sample_reports)} sample reports")


def main():
    """Main seeder function"""
    print("=" * 50)
    print("KKB Firma İstihbarat - Database Seeder")
    print("=" * 50)
    print()

    # Get database URL
    database_url = get_database_url()
    print(f"Database: {database_url.split('@')[1] if '@' in database_url else database_url}")
    print()

    # Create engine and session
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        print("Seeding database...")
        print()

        # Seed data
        seed_categories(session)
        seed_companies(session)
        seed_sample_reports(session)

        print()
        print("=" * 50)
        print("✓ Database seeding complete!")
        print("=" * 50)

    except Exception as e:
        print(f"Error: {e}")
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
