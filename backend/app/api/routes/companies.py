"""
Companies API Endpoints
Firma arama ve autocomplete
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.models.company import Company
from app.models.report import Report

router = APIRouter()


@router.get("/search")
async def search_companies(
    q: str = Query(..., min_length=2, description="Arama sorgusu"),
    limit: int = Query(10, ge=1, le=20),
    db: Session = Depends(get_db)
):
    """
    Firma arama (autocomplete).
    Vergi numarası veya firma adı ile arama yapılabilir.

    Query Parameters:
    - q: Arama sorgusu (min 2 karakter)
    - limit: Maksimum sonuç sayısı (default: 10, max: 20)
    """
    # Database'den arama
    companies = db.query(Company).filter(
        or_(
            Company.name.ilike(f"%{q}%"),
            Company.tax_no.ilike(f"%{q}%")
        ),
        Company.deleted_at.is_(None),
        Company.is_active == True
    ).limit(limit).all()

    results = [
        {
            "name": c.name,
            "tax_no": c.tax_no,
            "city": c.city,
            "sector": c.sector
        }
        for c in companies
    ]

    return {
        "success": True,
        "data": {
            "items": results,
            "total": len(results)
        },
        "error": None
    }


@router.get("/{tax_no}")
async def get_company_by_tax_no(
    tax_no: str,
    db: Session = Depends(get_db)
):
    """
    Vergi numarasına göre firma bilgisi getirir.
    Daha önce rapor oluşturulmuş firmalar için geçmiş veriler döner.
    """
    # Firma bilgisi
    company = db.query(Company).filter(
        Company.tax_no == tax_no,
        Company.deleted_at.is_(None)
    ).first()

    if not company:
        return {
            "success": False,
            "data": None,
            "error": {
                "code": "COMPANY_NOT_FOUND",
                "message": "Firma bulunamadı"
            }
        }

    # Geçmiş raporlar
    reports = db.query(Report).filter(
        Report.company_tax_no == tax_no,
        Report.deleted_at.is_(None)
    ).order_by(Report.created_at.desc()).limit(5).all()

    return {
        "success": True,
        "data": {
            "name": company.name,
            "tax_no": company.tax_no,
            "city": company.city,
            "sector": company.sector,
            "address": company.address,
            "total_reports": len(reports),
            "recent_reports": [r.to_dict() for r in reports]
        },
        "error": None
    }
