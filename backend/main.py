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
    print("🚀 Firma İstihbarat API başlatılıyor...")
    yield
    # Shutdown
    print("👋 Firma İstihbarat API kapatılıyor...")


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
