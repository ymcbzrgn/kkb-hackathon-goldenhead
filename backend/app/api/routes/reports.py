"""
Reports API Endpoints
Rapor CRUD işlemleri
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel
from typing import Optional
from uuid import UUID

from app.core.database import get_db
from app.services.report_service import ReportService
from app.services.pdf_export import PDFExportService
from app.models.report import Report, ReportStatus
from app.models.council_decision import AgentResult, CouncilDecision
# V2: Agent-level parallelism - her agent ayrı task, work-stealing
from app.workers.agent_tasks import generate_report_task_v2


class ReportCreateRequest(BaseModel):
    """Rapor oluşturma isteği"""
    company_name: str
    company_tax_no: Optional[str] = None
    demo_mode: bool = False  # Demo mode: ~10dk, Normal: ~40dk


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

    # V2: Agent-level parallelism - 3 agent task paralel başlar
    # Bir agent bitince worker diğer raporların agent'larını alabilir
    generate_report_task_v2.delay(
        report_id=str(report.id),
        company_name=request.company_name,
        demo_mode=request.demo_mode
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

    # Agent sonuçları ekle (frontend tsg, ihale, news bekliyor)
    # Frontend status, duration_seconds ve data bekliyor
    if report.agent_results:
        # agent_results tablosundan al (eski yöntem)
        report_data["agent_results"] = {
            result.agent_id.replace("_agent", ""): {
                "status": result.status,
                "duration_seconds": result.duration_seconds,
                "data": result.data,
                "summary": result.summary,
                "key_findings": result.key_findings,
                "warning_flags": result.warning_flags
            }
            for result in report.agent_results
        }
    else:
        # FALLBACK: agent_results tablosu boşsa, JSONB alanlarından oluştur
        # Celery task'lar veriyi tsg_data, ihale_data, news_data'ya kaydediyor
        report_data["agent_results"] = {}

        # TSG
        if report.tsg_data:
            report_data["agent_results"]["tsg"] = {
                "status": report.tsg_data.get("status", "completed") if isinstance(report.tsg_data, dict) else "completed",
                "duration_seconds": None,
                "data": report.tsg_data,
                "summary": None,
                "key_findings": [],
                "warning_flags": []
            }

        # İhale
        if report.ihale_data:
            ihale_status = "completed"
            if isinstance(report.ihale_data, dict):
                if report.ihale_data.get("timeout"):
                    ihale_status = "completed"  # partial data var
                elif report.ihale_data.get("hata"):
                    ihale_status = "failed"
            report_data["agent_results"]["ihale"] = {
                "status": ihale_status,
                "duration_seconds": None,
                "data": report.ihale_data,
                "summary": None,
                "key_findings": [],
                "warning_flags": ["TIMEOUT"] if isinstance(report.ihale_data, dict) and report.ihale_data.get("timeout") else []
            }

        # News
        if report.news_data:
            news_status = "completed"
            if isinstance(report.news_data, dict):
                if report.news_data.get("timeout"):
                    news_status = "completed"  # partial data var
            report_data["agent_results"]["news"] = {
                "status": news_status,
                "duration_seconds": None,
                "data": report.news_data,
                "summary": None,
                "key_findings": [],
                "warning_flags": ["TIMEOUT"] if isinstance(report.news_data, dict) and report.news_data.get("timeout") else []
            }

    # Council kararı ekle (frontend beklentilerine uygun format)
    if report.council_decision:
        report_data["council_decision"] = {
            "final_score": report.council_decision.final_score,
            "risk_level": report.council_decision.risk_level,
            "decision": report.council_decision.decision,
            "consensus": float(report.council_decision.consensus) if report.council_decision.consensus else None,
            "conditions": report.council_decision.conditions,
            "summary": report.council_decision.summary,
            "dissent_note": report.council_decision.summary,  # Frontend beklentisi
            "transcript": report.council_decision.transcript,
            "duration_seconds": report.council_decision.duration_seconds,
            # Scores objesi - frontend beklentisi
            "scores": {
                "initial": report.council_decision.initial_scores,
                "final": report.council_decision.final_scores
            },
            # Ayrıca flat olarak da dön (geriye uyumluluk)
            "initial_scores": report.council_decision.initial_scores,
            "final_scores": report.council_decision.final_scores
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
    # 1. UUID validation
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

    # 2. Raporu getir (PDF için ilişkileri eager load et)
    report = db.query(Report).options(
        joinedload(Report.agent_results),
        joinedload(Report.council_decision)
    ).filter(
        Report.id == report_uuid,
        Report.deleted_at.is_(None)
    ).first()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "data": None,
                "error": {
                    "code": "REPORT_NOT_FOUND",
                    "message": "Rapor bulunamadı"
                }
            }
        )

    # 3. Rapor tamamlanmış mı kontrol et
    if report.status != ReportStatus.COMPLETED.value:
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

    # 4. Rapor verisini hazırla
    report_data = {
        "company_name": report.company_name,
        "company_tax_no": report.company_tax_no,
        "final_score": report.final_score,
        "risk_level": report.risk_level,
        "decision": report.decision,
        "decision_summary": report.decision_summary,
        "created_at": report.created_at,
        "completed_at": report.completed_at,
        "duration_seconds": report.duration_seconds,
        "agent_results": {},
        "council_decision": None
    }

    # 5. Agent sonuçlarını ekle
    if report.agent_results:
        for result in report.agent_results:
            if result.agent_id:
                report_data["agent_results"][result.agent_id] = {
                    "summary": result.summary,
                    "key_findings": result.key_findings,
                    "warning_flags": result.warning_flags,
                    "data": result.data
                }

    # 6. Council kararını ekle
    if report.council_decision:
        report_data["council_decision"] = {
            "final_score": report.council_decision.final_score,
            "risk_level": report.council_decision.risk_level,
            "decision": report.council_decision.decision,
            "consensus": float(report.council_decision.consensus) if report.council_decision.consensus else None,
            "initial_scores": report.council_decision.initial_scores,
            "final_scores": report.council_decision.final_scores,
            "conditions": report.council_decision.conditions,
            "summary": report.council_decision.summary,
            "transcript": report.council_decision.transcript
        }

    # 7. PDF oluştur
    pdf_service = PDFExportService()
    pdf_buffer = pdf_service.generate_report_pdf(report_data)

    # 8. Dosya adı oluştur
    filename = pdf_service.generate_filename(report.company_name)

    # 9. PDF'i döndür
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )
