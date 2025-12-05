"""
Companies API Endpoints
Firma arama ve autocomplete
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db

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
    # TODO: Gerçek arama implementasyonu
    # Şimdilik mock data

    mock_results = []

    # Basit mock matching
    if "abc" in q.lower():
        mock_results.append({
            "name": "ABC Teknoloji A.Ş.",
            "tax_no": "1234567890",
            "city": "İstanbul"
        })
    if "xyz" in q.lower():
        mock_results.append({
            "name": "XYZ Yazılım Ltd. Şti.",
            "tax_no": "0987654321",
            "city": "Ankara"
        })

    return {
        "success": True,
        "data": {
            "items": mock_results[:limit],
            "total": len(mock_results)
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
    # TODO: Database'den firma bilgisi çek

    return {
        "success": False,
        "data": None,
        "error": {
            "code": "COMPANY_NOT_FOUND",
            "message": "Firma bulunamadı"
        }
    }
