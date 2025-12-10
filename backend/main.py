"""
Firma İstihbarat API - FastAPI Entry Point
KKB Agentic AI Hackathon 2024
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api.routes import reports, companies, health
from app.api.websocket import router as ws_router
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("[INFO] Firma Istihbarat API baslatiliyor...")

    # Redis PubSub listener başlat (Celery → WebSocket köprüsü)
    from app.services.redis_pubsub import pubsub_service
    from app.api.websocket import manager as ws_manager

    async def handle_redis_message(report_id: str, event_type: str, payload: dict):
        """Redis'ten gelen mesajı WebSocket'e ilet."""
        await ws_manager.send_event(report_id, event_type, payload)

    try:
        await pubsub_service.start_listener(handle_redis_message)
        print("[INFO] Redis PubSub listener başlatıldı")
    except Exception as e:
        print(f"[WARN] Redis PubSub başlatılamadı: {e}")

    yield

    # Shutdown
    try:
        await pubsub_service.stop_listener()
    except Exception as e:
        print(f"[WARN] Redis PubSub durdurma hatası: {e}")

    print("[INFO] Firma Istihbarat API kapatiliyor...")


app = FastAPI(
    title="Firma İstihbarat API",
    description="KKB Agentic AI Hackathon 2024 - Firma istihbarat raporu sistemi",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Production'da spesifik origin'ler kullanılmalı
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(companies.router, prefix="/api/companies", tags=["companies"])
app.include_router(ws_router, tags=["websocket"])


@app.get("/")
async def root():
    return {
        "message": "Firma İstihbarat API",
        "version": "1.0.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
