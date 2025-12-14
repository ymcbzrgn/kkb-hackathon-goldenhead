"""
Report Service
Rapor iş mantığı
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime, timezone

from app.models.report import Report, ReportStatus


class ReportService:
    """Rapor servis sınıfı"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, company_name: str, company_tax_no: Optional[str] = None) -> Report:
        """Yeni rapor oluştur"""
        report = Report(
            company_name=company_name,
            company_tax_no=company_tax_no,
            status=ReportStatus.PENDING.value
        )
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    def get_by_id(self, report_id: UUID) -> Optional[Report]:
        """ID ile rapor getir"""
        return self.db.query(Report).filter(
            Report.id == report_id,
            Report.deleted_at.is_(None)
        ).first()

    def list(
        self,
        page: int = 1,
        limit: int = 10,
        status: Optional[str] = None,
        sort: str = "-created_at"
    ) -> tuple[List[Report], int]:
        """
        Raporları listele.

        Args:
            page: Sayfa numarası
            limit: Sayfa başı kayıt sayısı
            status: Filtre (pending, processing, completed, failed)
            sort: Sıralama (-created_at, created_at, -company_name, company_name)
        """
        query = self.db.query(Report).filter(Report.deleted_at.is_(None))

        if status:
            query = query.filter(Report.status == status)

        total = query.count()

        # Sort parametresini işle
        if sort.startswith("-"):
            sort_field = sort[1:]
            descending = True
        else:
            sort_field = sort
            descending = False

        # Sort alanını belirle
        if sort_field == "created_at":
            order_column = Report.created_at
        elif sort_field == "company_name":
            order_column = Report.company_name
        else:
            order_column = Report.created_at  # Fallback
            descending = True

        if descending:
            query = query.order_by(order_column.desc())
        else:
            query = query.order_by(order_column.asc())

        reports = query.offset((page - 1) * limit).limit(limit).all()

        return reports, total

    def update_status(self, report_id: UUID, status: str, message: Optional[str] = None) -> Optional[Report]:
        """Rapor durumunu güncelle"""
        report = self.get_by_id(report_id)
        if report:
            report.status = status
            if message:
                report.status_message = message
            if status == ReportStatus.PROCESSING.value:
                report.started_at = datetime.now(timezone.utc)
            elif status == ReportStatus.COMPLETED.value:
                report.completed_at = datetime.now(timezone.utc)
                if report.started_at:
                    report.duration_seconds = int((report.completed_at - report.started_at).total_seconds())
            self.db.commit()
            self.db.refresh(report)
        return report

    def update_result(
        self,
        report_id: UUID,
        final_score: int,
        risk_level: str,
        decision: str,
        decision_summary: Optional[str] = None
    ) -> Optional[Report]:
        """Rapor sonucunu güncelle"""
        report = self.get_by_id(report_id)
        if report:
            report.final_score = final_score
            report.risk_level = risk_level
            report.decision = decision
            report.decision_summary = decision_summary
            self.db.commit()
            self.db.refresh(report)
        return report

    def delete(self, report_id: UUID) -> bool:
        """Raporu sil (soft delete) - her durumda silinebilir"""
        report = self.get_by_id(report_id)
        if report:
            report.deleted_at = datetime.now(timezone.utc)
            self.db.commit()
            return True
        return False

    def update_agent_progress(
        self,
        report_id: UUID,
        agent_id: str,
        progress: int,
        message: str,
        status: str = "running"
    ) -> Optional[Report]:
        """Agent progress güncelle (reserved_json içinde)"""
        report = self.get_by_id(report_id)
        if not report:
            return None

        current_data = report.reserved_json or {}
        agent_progresses = current_data.get("agent_progresses", {})

        # Progress %100 ise status'ü otomatik "completed" yap
        if progress >= 100:
            status = "completed"

        agent_progresses[agent_id] = {
            "progress": progress,
            "message": message,
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        current_data["agent_progresses"] = agent_progresses
        report.reserved_json = current_data

        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(report, "reserved_json")

        self.db.commit()
        return report

    def get_live_state(self, report_id: UUID) -> Optional[dict]:
        """Canlı durum bilgisini getir (reconnect için)"""
        report = self.get_by_id(report_id)
        if not report:
            return None

        return {
            "status": report.status,
            "phase": (report.reserved_json or {}).get("current_phase", "pending"),
            "agent_progresses": (report.reserved_json or {}).get("agent_progresses", {})
        }
