"""
Redis Pub/Sub Service
Celery → Redis → WebSocket köprüsü

Bu modül Celery worker'dan WebSocket'e real-time progress
gönderimi için Redis Pub/Sub mekanizması sağlar.

Mimari:
    Celery Worker (sync) → Redis PUBLISH → Uvicorn (async) → WebSocket

Kullanım:
    # Celery'den publish:
    from app.services.redis_pubsub import publish_agent_progress
    publish_agent_progress(report_id, agent_id, progress, message)

    # Uvicorn startup'ta subscribe:
    from app.services.redis_pubsub import pubsub_service
    await pubsub_service.start_listener(handler)
"""
import json
import asyncio
from typing import Optional, Callable
from datetime import datetime

import redis
import redis.asyncio as aioredis

from app.core.config import settings


# Redis channel isimleri
PROGRESS_CHANNEL = "report_progress"


class RedisPubSubService:
    """
    Redis Pub/Sub yöneticisi.

    Publisher (sync) - Celery worker'lar için
    Subscriber (async) - Uvicorn için
    """

    def __init__(self):
        self._subscriber: Optional[aioredis.Redis] = None
        self._publisher: Optional[redis.Redis] = None
        self._pubsub = None
        self._listener_task: Optional[asyncio.Task] = None
        self._message_handler: Optional[Callable] = None
        self._running = False

    # ========================================================================
    # PUBLISHER (Sync - Celery için)
    # ========================================================================

    def get_publisher(self) -> redis.Redis:
        """
        Sync Redis client döndür.
        Celery task'lar için kullanılır.
        """
        if not self._publisher:
            self._publisher = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True
            )
        return self._publisher

    def publish_progress(
        self,
        report_id: str,
        event_type: str,
        payload: dict
    ) -> bool:
        """
        Progress event'i Redis'e publish et.

        Args:
            report_id: Rapor ID'si
            event_type: Event tipi (agent_progress, agent_completed, vs.)
            payload: Event verisi

        Returns:
            bool: Başarılı ise True
        """
        try:
            message = {
                "report_id": str(report_id),
                "event_type": event_type,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "payload": payload
            }
            publisher = self.get_publisher()
            result = publisher.publish(PROGRESS_CHANNEL, json.dumps(message))
            return result > 0  # En az 1 subscriber varsa True
        except Exception as e:
            print(f"[REDIS] Publish error: {e}")
            return False

    # ========================================================================
    # SUBSCRIBER (Async - Uvicorn için)
    # ========================================================================

    async def start_listener(self, message_handler: Callable) -> None:
        """
        Redis listener'ı başlat.
        Uvicorn startup'ta çağrılır.

        Args:
            message_handler: async def handler(report_id, event_type, payload)
        """
        if self._running:
            print("[REDIS] Listener zaten çalışıyor")
            return

        self._message_handler = message_handler
        self._running = True

        try:
            self._subscriber = aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True
            )
            self._pubsub = self._subscriber.pubsub()

            await self._pubsub.subscribe(PROGRESS_CHANNEL)
            self._listener_task = asyncio.create_task(self._listen())

            print(f"[REDIS] PubSub listener başlatıldı: {PROGRESS_CHANNEL}")
        except Exception as e:
            print(f"[REDIS] Listener başlatma hatası: {e}")
            self._running = False
            raise

    async def _listen(self) -> None:
        """Redis mesajlarını dinle ve handler'a ilet."""
        try:
            async for message in self._pubsub.listen():
                if not self._running:
                    break

                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        await self._message_handler(
                            data["report_id"],
                            data["event_type"],
                            data["payload"]
                        )
                    except json.JSONDecodeError as e:
                        print(f"[REDIS] JSON decode error: {e}")
                    except Exception as e:
                        print(f"[REDIS] Message handler error: {e}")

        except asyncio.CancelledError:
            print("[REDIS] Listener iptal edildi")
        except Exception as e:
            print(f"[REDIS] Listener error: {e}")
        finally:
            self._running = False

    async def stop_listener(self) -> None:
        """
        Listener'ı durdur.
        Uvicorn shutdown'da çağrılır.
        """
        self._running = False

        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            self._listener_task = None

        if self._pubsub:
            try:
                await self._pubsub.unsubscribe(PROGRESS_CHANNEL)
                await self._pubsub.close()
            except Exception:
                pass
            self._pubsub = None

        if self._subscriber:
            try:
                await self._subscriber.close()
            except Exception:
                pass
            self._subscriber = None

        if self._publisher:
            try:
                self._publisher.close()
            except Exception:
                pass
            self._publisher = None

        print("[REDIS] PubSub listener durduruldu")

    @property
    def is_running(self) -> bool:
        """Listener çalışıyor mu?"""
        return self._running


# Global instance
pubsub_service = RedisPubSubService()


# ============================================================================
# Helper Functions (Celery task'lardan kolay kullanım için)
# ============================================================================

def publish_agent_progress(
    report_id: str,
    agent_id: str,
    progress: int,
    message: str
) -> bool:
    """
    Agent progress'i Redis'e publish et.

    Args:
        report_id: Rapor ID'si
        agent_id: Agent ID'si (tsg_agent, ihale_agent, news_agent)
        progress: İlerleme yüzdesi (0-100)
        message: İlerleme mesajı

    Returns:
        bool: Başarılı ise True

    Örnek:
        publish_agent_progress(
            report_id="abc-123",
            agent_id="tsg_agent",
            progress=50,
            message="TSG verileri işleniyor..."
        )
    """
    return pubsub_service.publish_progress(
        report_id=report_id,
        event_type="agent_progress",
        payload={
            "agent_id": agent_id,
            "progress": progress,
            "message": message
        }
    )


def publish_agent_event(
    report_id: str,
    event_type: str,
    payload: dict
) -> bool:
    """
    Genel agent event'i Redis'e publish et.

    Args:
        report_id: Rapor ID'si
        event_type: Event tipi (agent_started, agent_completed, agent_failed, vs.)
        payload: Event verisi

    Returns:
        bool: Başarılı ise True
    """
    return pubsub_service.publish_progress(
        report_id=report_id,
        event_type=event_type,
        payload=payload
    )
