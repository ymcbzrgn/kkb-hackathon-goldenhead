"""
WebSocket Handler
Real-time rapor takibi için WebSocket endpoint
"""
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set
import json
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter()

# Active connections per report
active_connections: Dict[str, Set[WebSocket]] = {}


class ConnectionManager:
    """WebSocket bağlantı yöneticisi"""

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, report_id: str):
        """Yeni bağlantı kabul et"""
        await websocket.accept()
        if report_id not in self.active_connections:
            self.active_connections[report_id] = set()
        self.active_connections[report_id].add(websocket)

    def disconnect(self, websocket: WebSocket, report_id: str):
        """Bağlantıyı kapat"""
        if report_id in self.active_connections:
            self.active_connections[report_id].discard(websocket)
            if not self.active_connections[report_id]:
                del self.active_connections[report_id]

    async def send_event(self, report_id: str, event_type: str, payload: dict):
        """Belirli bir rapora ait tüm bağlantılara event gönder"""
        if report_id not in self.active_connections:
            return

        event = {
            "type": event_type,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "payload": payload
        }

        dead_connections = set()
        for connection in self.active_connections[report_id]:
            try:
                await connection.send_json(event)
            except Exception:
                dead_connections.add(connection)

        # Ölü bağlantıları temizle
        for connection in dead_connections:
            self.active_connections[report_id].discard(connection)

    async def broadcast_to_all(self, event_type: str, payload: dict):
        """Tüm bağlantılara broadcast (dead connection temizleme ile)"""
        event = {
            "type": event_type,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "payload": payload
        }

        # Her report için dead connection'ları takip et
        all_dead_connections: dict[str, set] = {}

        for report_id, connections in self.active_connections.items():
            dead_connections = set()
            for connection in connections:
                try:
                    await connection.send_json(event)
                except Exception as e:
                    logger.warning(f"Broadcast error for report {report_id}: {e}")
                    dead_connections.add(connection)
            if dead_connections:
                all_dead_connections[report_id] = dead_connections

        # Dead connection'ları temizle
        for report_id, dead_conns in all_dead_connections.items():
            if report_id in self.active_connections:
                for conn in dead_conns:
                    self.active_connections[report_id].discard(conn)
                if not self.active_connections[report_id]:
                    del self.active_connections[report_id]


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws/{report_id}")
async def websocket_endpoint(websocket: WebSocket, report_id: str):
    """
    WebSocket endpoint for real-time report updates.

    Event Types:
    - job_started: İş başladı
    - job_completed: İş tamamlandı
    - job_failed: İş hata aldı
    - agent_started: Agent başladı
    - agent_progress: Agent ilerleme
    - agent_completed: Agent tamamlandı
    - agent_failed: Agent hata aldı
    - council_started: Komite toplantısı başladı
    - council_phase_changed: Aşama değişti
    - council_speaker_changed: Konuşmacı değişti
    - council_speech: Konuşma (streaming)
    - council_score_revision: Skor revizyonu
    - council_decision: Final karar
    """
    await manager.connect(websocket, report_id)

    try:
        # Bağlantı onayı gönder
        await websocket.send_json({
            "type": "connected",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "payload": {
                "report_id": report_id,
                "message": "WebSocket bağlantısı kuruldu"
            }
        })

        # Mevcut durumu gönder (reconnect state restore)
        await _send_current_state(websocket, report_id)

        # Mesajları dinle (heartbeat için)
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0  # 30 saniye timeout
                )

                # Ping/Pong
                if data == "ping":
                    await websocket.send_text("pong")

            except asyncio.TimeoutError:
                # Timeout olursa heartbeat gönder
                await websocket.send_json({
                    "type": "heartbeat",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "payload": {}
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket, report_id)
    except Exception as e:
        manager.disconnect(websocket, report_id)


# Helper functions for sending events from other parts of the application
async def send_job_started(report_id: str, company_name: str, estimated_duration: int = 2400):
    await manager.send_event(report_id, "job_started", {
        "report_id": report_id,
        "company_name": company_name,
        "estimated_duration_seconds": estimated_duration
    })


async def send_job_completed(report_id: str, duration: int, score: int, risk_level: str, decision: str):
    await manager.send_event(report_id, "job_completed", {
        "report_id": report_id,
        "duration_seconds": duration,
        "final_score": score,
        "risk_level": risk_level,
        "decision": decision
    })


async def send_agent_progress(report_id: str, agent_id: str, progress: int, message: str):
    await manager.send_event(report_id, "agent_progress", {
        "agent_id": agent_id,
        "progress": progress,
        "message": message
    })


async def send_council_speech(report_id: str, speaker_id: str, chunk: str, is_complete: bool, risk_score: int = None):
    payload = {
        "speaker_id": speaker_id,
        "chunk": chunk,
        "is_complete": is_complete
    }
    if risk_score is not None:
        payload["risk_score"] = risk_score

    await manager.send_event(report_id, "council_speech", payload)


async def _send_current_state(websocket: WebSocket, report_id: str):
    """
    Reconnect'te mevcut durumu mevcut event formatlarında gönder.
    Frontend değişikliği gerektirmez - standart event'leri kullanır.
    """
    from app.core.database import SessionLocal
    from app.services.report_service import ReportService

    db = None
    try:
        db = SessionLocal()
        service = ReportService(db)
        state = service.get_live_state(report_id)

        if not state:
            return

        # Sadece processing durumundaysa state restore yap
        if state["status"] != "processing":
            return

        # Her agent için mevcut event'leri gönder
        agent_progresses = state.get("agent_progresses", {})
        for agent_id, agent_state in agent_progresses.items():
            # agent_started event'i
            await websocket.send_json({
                "type": "agent_started",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "payload": {
                    "agent_id": agent_id,
                    "agent_name": agent_id.replace("_", " ").title(),
                    "agent_description": "Devam ediyor..."
                }
            })

            # agent_progress event'i
            await websocket.send_json({
                "type": "agent_progress",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "payload": {
                    "agent_id": agent_id,
                    "progress": agent_state.get("progress", 0),
                    "message": agent_state.get("message", "")
                }
            })

            # Eğer completed ise
            if agent_state.get("status") == "completed":
                await websocket.send_json({
                    "type": "agent_completed",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "payload": {
                        "agent_id": agent_id,
                        "duration_seconds": 0,
                        "summary": {}
                    }
                })

    except Exception as e:
        logger.error(f"State restore error for report {report_id}: {e}")
    finally:
        if db:
            db.close()
