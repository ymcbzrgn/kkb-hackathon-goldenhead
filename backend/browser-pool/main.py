"""
Browser Pool Service - Pre-warmed browser instances for parallel scraping.
Kubernetes microservice that manages a pool of Playwright browsers.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
from playwright.async_api import async_playwright, Browser, Page
import uuid
from typing import Dict, Optional
from contextlib import asynccontextmanager
import os
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

POOL_SIZE = int(os.getenv("POOL_SIZE", "10"))


class BrowserPoolManager:
    """Pre-warmed browser pool for fast scraping."""

    def __init__(self, pool_size: int = 10):
        self.pool_size = pool_size
        self.playwright = None
        self.browsers: Dict[str, Browser] = {}
        self.available: asyncio.Queue = None
        self.in_use: Dict[str, float] = {}
        self._initialized = False
        self._lock = asyncio.Lock()

    async def initialize(self):
        """Initialize browser pool with pre-warmed instances."""
        if self._initialized:
            return

        async with self._lock:
            if self._initialized:
                return

            logger.info(f"Initializing browser pool with {self.pool_size} instances...")

            self.playwright = await async_playwright().start()
            self.available = asyncio.Queue()

            # Pre-warm browsers in parallel
            async def create_browser(i: int) -> tuple:
                try:
                    browser = await self.playwright.chromium.launch(
                        headless=True,
                        args=[
                            '--no-sandbox',
                            '--disable-setuid-sandbox',
                            '--disable-dev-shm-usage',
                            '--disable-gpu',
                            '--single-process',
                            '--disable-web-security',
                            '--disable-features=IsolateOrigins,site-per-process'
                        ]
                    )
                    browser_id = f"browser-{i}-{str(uuid.uuid4())[:8]}"
                    logger.info(f"Browser {browser_id} created")
                    return browser_id, browser
                except Exception as e:
                    logger.error(f"Failed to create browser {i}: {e}")
                    return None, None

            tasks = [create_browser(i) for i in range(self.pool_size)]
            results = await asyncio.gather(*tasks)

            for browser_id, browser in results:
                if browser_id and browser:
                    self.browsers[browser_id] = browser
                    await self.available.put(browser_id)

            self._initialized = True
            logger.info(f"Browser pool initialized: {len(self.browsers)} browsers ready")

    async def acquire(self, timeout: int = 60) -> str:
        """Acquire a browser from the pool."""
        if not self._initialized:
            await self.initialize()

        try:
            browser_id = await asyncio.wait_for(
                self.available.get(),
                timeout=timeout
            )
            self.in_use[browser_id] = time.time()
            logger.info(f"Browser {browser_id} acquired")
            return browser_id
        except asyncio.TimeoutError:
            logger.error("No browsers available - timeout")
            raise HTTPException(503, "No browsers available")

    async def release(self, browser_id: str):
        """Release a browser back to the pool."""
        if browser_id in self.in_use:
            del self.in_use[browser_id]

        if browser_id in self.browsers:
            browser = self.browsers[browser_id]
            # Close all contexts to clean up
            try:
                for context in browser.contexts:
                    await context.close()
            except Exception as e:
                logger.warning(f"Error closing contexts for {browser_id}: {e}")

            await self.available.put(browser_id)
            logger.info(f"Browser {browser_id} released")

    async def get_page(self, browser_id: str) -> Page:
        """Get a new page from a browser."""
        if browser_id not in self.browsers:
            raise HTTPException(404, f"Browser {browser_id} not found")

        browser = self.browsers[browser_id]
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()
        return page

    async def navigate_and_screenshot(
        self,
        browser_id: str,
        url: str,
        wait_time: int = 3000
    ) -> bytes:
        """Navigate to URL and take screenshot."""
        if browser_id not in self.browsers:
            raise HTTPException(404, f"Browser {browser_id} not found")

        browser = self.browsers[browser_id]
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )

        try:
            page = await context.new_page()
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await page.wait_for_timeout(wait_time)
            screenshot = await page.screenshot(type='jpeg', quality=80, full_page=False)
            return screenshot
        finally:
            await context.close()

    def stats(self) -> dict:
        """Get pool statistics."""
        return {
            "total": self.pool_size,
            "available": self.available.qsize() if self.available else 0,
            "in_use": len(self.in_use),
            "initialized": self._initialized
        }

    async def cleanup(self):
        """Cleanup all browsers."""
        logger.info("Cleaning up browser pool...")
        for browser_id, browser in self.browsers.items():
            try:
                await browser.close()
            except Exception as e:
                logger.error(f"Error closing browser {browser_id}: {e}")

        if self.playwright:
            await self.playwright.stop()

        self.browsers.clear()
        self._initialized = False
        logger.info("Browser pool cleaned up")


# Global pool instance
pool = BrowserPoolManager(pool_size=POOL_SIZE)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan - initialize pool on startup."""
    await pool.initialize()
    yield
    await pool.cleanup()


app = FastAPI(
    title="Browser Pool Service",
    description="Pre-warmed browser pool for parallel news scraping",
    version="1.0.0",
    lifespan=lifespan
)


# Request/Response Models
class AcquireRequest(BaseModel):
    timeout: int = 60


class AcquireResponse(BaseModel):
    browser_id: str


class ReleaseRequest(BaseModel):
    browser_id: str


class ScreenshotRequest(BaseModel):
    browser_id: str
    url: str
    wait_time: int = 3000


class ScreenshotResponse(BaseModel):
    success: bool
    message: str


# Endpoints
@app.post("/acquire", response_model=AcquireResponse)
async def acquire_browser(request: AcquireRequest):
    """Acquire a browser from the pool."""
    browser_id = await pool.acquire(request.timeout)
    return AcquireResponse(browser_id=browser_id)


@app.post("/release")
async def release_browser(request: ReleaseRequest):
    """Release a browser back to the pool."""
    await pool.release(request.browser_id)
    return {"status": "released", "browser_id": request.browser_id}


@app.post("/screenshot")
async def take_screenshot(request: ScreenshotRequest):
    """Navigate to URL and take screenshot."""
    try:
        screenshot = await pool.navigate_and_screenshot(
            request.browser_id,
            request.url,
            request.wait_time
        )

        # Return as base64
        import base64
        screenshot_b64 = base64.b64encode(screenshot).decode('utf-8')

        return {
            "success": True,
            "screenshot_base64": screenshot_b64,
            "content_type": "image/jpeg"
        }
    except Exception as e:
        logger.error(f"Screenshot error: {e}")
        return {"success": False, "error": str(e)}


@app.get("/stats")
async def get_stats():
    """Get pool statistics."""
    return pool.stats()


@app.get("/health")
async def health():
    """Health check endpoint."""
    stats = pool.stats()
    is_healthy = stats["initialized"] and stats["available"] > 0
    return {
        "status": "healthy" if is_healthy else "degraded",
        **stats
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Browser Pool Service",
        "version": "1.0.0",
        "status": "running"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
