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
from app.services.report_service import ReportService
from app.workers.tasks import generate_report_task


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

    # Database'e kaydet
    report_service = ReportService(db)
    report = report_service.create(
        company_name=request.company_name,
        company_tax_no=request.company_tax_no
    )

    # Celery task başlat
    generate_report_task.delay(
        report_id=str(report.id),
        company_name=request.company_name
    )

    return {
        "success": True,
        "data": {
            "report_id": str(report.id),
            "status": report.status,
            "websocket_url": f"/ws/{report.id}"
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
    report_service = ReportService(db)
    reports, total = report_service.list(
        page=page,
        limit=limit,
        status=status
    )

    total_pages = (total + limit - 1) // limit

    return {
        "success": True,
        "data": {
            "items": [r.to_dict() for r in reports],
            "pagination": {
                "page": page,
                "limit": limit,
                "total_items": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
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
    # UUID validation
    try:
        report_uuid = UUID(report_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "data": None,
                "error": {
                    "code": "INVALID_REPORT_ID",
                    "message": "Geçersiz rapor ID formatı"
                }
            }
        )

    report_service = ReportService(db)
    report = report_service.get_by_id(report_uuid)

    if not report:
        return {
            "success": False,
            "data": None,
            "error": {
                "code": "REPORT_NOT_FOUND",
                "message": "Rapor bulunamadı"
            }
        }

    # Rapor detayı dönüş
    report_data = report.to_dict()

    # Agent sonuçları ekle
    if report.agent_results:
        report_data["agent_results"] = {
            result.agent_type: result.processed_data
            for result in report.agent_results
        }

    # Council kararı ekle
    if report.council_decision:
        report_data["council_decision"] = {
            "final_score": report.council_decision.final_score,
            "risk_level": report.council_decision.risk_level,
            "decision": report.council_decision.decision,
            "consensus": report.council_decision.consensus,
            "conditions": report.council_decision.conditions,
            "dissent_note": report.council_decision.dissent_note,
            "transcript": report.council_decision.transcript
        }

    return {
        "success": True,
        "data": report_data,
        "error": None
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
    # UUID validation
    try:
        report_uuid = UUID(report_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "data": None,
                "error": {
                    "code": "INVALID_REPORT_ID",
                    "message": "Geçersiz rapor ID formatı"
                }
            }
        )

    report_service = ReportService(db)

    try:
        deleted = report_service.delete(report_uuid)

        if not deleted:
            return {
                "success": False,
                "data": None,
                "error": {
                    "code": "REPORT_NOT_FOUND",
                    "message": "Rapor bulunamadı"
                }
            }

        return {
            "success": True,
            "data": {
                "deleted": True,
                "id": report_id
            },
            "error": None
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "data": None,
                "error": {
                    "code": "DELETE_FAILED",
                    "message": str(e)
                }
            }
        )


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
