"""
Reports API Endpoints
Rapor CRUD işlemleri
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from uuid import UUID

from app.core.database import get_db
from app.core.security import generate_report_id


class ReportCreateRequest(BaseModel):
    """Rapor oluşturma isteği"""
    company_name: str
    company_tax_no: Optional[str] = None


router = APIRouter()


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_report(
    request: ReportCreateRequest,
    db: Session = Depends(get_db)
):
    """
    Yeni rapor oluşturma işlemi başlatır.
    İşlem arka planda Celery ile çalışır, WebSocket ile takip edilir.

    Request Body:
    - company_name: Firma adı (zorunlu)
    - company_tax_no: Vergi numarası (opsiyonel)

    Returns:
    - report_id: Oluşturulan rapor ID'si
    - status: pending
    - websocket_url: WebSocket bağlantı URL'i
    """
    if not request.company_name or len(request.company_name) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "data": None,
                "error": {
                    "code": "COMPANY_NAME_TOO_SHORT",
                    "message": "Firma adı en az 2 karakter olmalı"
                }
            }
        )

    report_id = generate_report_id()

    # TODO: Database'e kaydet
    # TODO: Celery task başlat

    return {
        "success": True,
        "data": {
            "report_id": report_id,
            "status": "pending",
            "websocket_url": f"/ws/{report_id}"
        },
        "error": None
    }


@router.get("")
async def list_reports(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    status: Optional[str] = None,
    sort: str = "-created_at",
    db: Session = Depends(get_db)
):
    """
    Tüm raporları listeler.

    Query Parameters:
    - page: Sayfa numarası (default: 1)
    - limit: Sayfa başı kayıt (default: 10, max: 50)
    - status: Filtre (pending, processing, completed, failed)
    - sort: Sıralama (created_at, -created_at, company_name)
    """
    # TODO: Database'den çek

    return {
        "success": True,
        "data": {
            "items": [],
            "pagination": {
                "page": page,
                "limit": limit,
                "total_items": 0,
                "total_pages": 0,
                "has_next": False,
                "has_prev": False
            }
        },
        "error": None
    }


@router.get("/{report_id}")
async def get_report(
    report_id: str,
    db: Session = Depends(get_db)
):
    """
    Tek bir raporun tam detayını döner.
    Agent sonuçları ve Council kararı dahil.
    """
    # TODO: Database'den çek

    # Mock response for now
    return {
        "success": False,
        "data": None,
        "error": {
            "code": "REPORT_NOT_FOUND",
            "message": "Rapor bulunamadı"
        }
    }


@router.delete("/{report_id}")
async def delete_report(
    report_id: str,
    db: Session = Depends(get_db)
):
    """
    Raporu siler.
    İşlemi devam eden rapor silinemez.
    """
    # TODO: Database'den sil

    return {
        "success": True,
        "data": {
            "deleted": True,
            "id": report_id
        },
        "error": None
    }


@router.get("/{report_id}/pdf")
async def export_pdf(
    report_id: str,
    db: Session = Depends(get_db)
):
    """
    Raporun PDF versiyonunu indirir.
    Sadece completed durumundaki raporlar için çalışır.
    """
    # TODO: PDF oluştur ve döndür

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={
            "success": False,
            "data": None,
            "error": {
                "code": "REPORT_NOT_COMPLETED",
                "message": "Tamamlanmamış raporun PDF'i oluşturulamaz"
            }
        }
    )
