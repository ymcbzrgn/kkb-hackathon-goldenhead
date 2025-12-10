"""
Ihale Agent Logger - Kapsamli logging icin yardimci.
TSG Logger'dan adapte edildi.
"""
import time
import asyncio
from datetime import datetime
from typing import Optional, Any, Callable
from functools import wraps


class IhaleLogger:
    """Ihale Agent icin merkezi logger."""

    PREFIX = "[IHALE]"

    @classmethod
    def log(cls, msg: str, level: str = "INFO"):
        """Ana log fonksiyonu."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"{cls.PREFIX}[{timestamp}][{level}] {msg}", flush=True)

    @classmethod
    def step(cls, name: str):
        """Buyuk adim baslangici."""
        cls.log(f"===== {name} =====")

    @classmethod
    def success(cls, msg: str):
        """Basarili islem."""
        cls.log(msg, "OK")

    @classmethod
    def error(cls, msg: str):
        """Hata mesaji."""
        cls.log(msg, "ERROR")

    @classmethod
    def warn(cls, msg: str):
        """Uyari mesaji."""
        cls.log(msg, "WARN")

    @classmethod
    def debug(cls, msg: str):
        """Debug mesaji."""
        cls.log(msg, "DEBUG")


# Kisa alias'lar
log = IhaleLogger.log
step = IhaleLogger.step
success = IhaleLogger.success
error = IhaleLogger.error
warn = IhaleLogger.warn
debug = IhaleLogger.debug


async def with_timeout(coro, timeout_sec: int, description: str):
    """
    Timeout korumali async cagri.

    Args:
        coro: Async coroutine
        timeout_sec: Maximum bekleme suresi (saniye)
        description: Islem aciklamasi

    Returns:
        Coroutine sonucu veya None (timeout durumunda)
    """
    log(f"{description} basliyor (max {timeout_sec}s)...")
    start = time.time()
    try:
        result = await asyncio.wait_for(coro, timeout=timeout_sec)
        elapsed = time.time() - start
        log(f"{description} tamamlandi ({elapsed:.1f}s)")
        return result
    except asyncio.TimeoutError:
        elapsed = time.time() - start
        error(f"{description} TIMEOUT! ({elapsed:.1f}s)")
        return None
    except Exception as e:
        elapsed = time.time() - start
        error(f"{description} HATA: {e} ({elapsed:.1f}s)")
        return None


class Timer:
    """Basit zamanlama sinifi."""

    def __init__(self, description: str = ""):
        self.description = description
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        if self.description:
            log(f"{self.description} basliyor...")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.time() - self.start_time
        if exc_type:
            error(f"{self.description} HATA: {exc_val} ({elapsed:.1f}s)")
        elif self.description:
            success(f"{self.description} tamamlandi ({elapsed:.1f}s)")
        return False

    @property
    def elapsed(self) -> float:
        """Gecen sure (saniye)."""
        if self.start_time:
            return time.time() - self.start_time
        return 0.0


# Test
if __name__ == "__main__":
    step("TEST BASLIYOR")
    log("Normal log mesaji")
    success("Basarili islem")
    warn("Uyari mesaji")
    error("Hata mesaji")
    debug("Debug mesaji")

    with Timer("Test islemi"):
        import time as t
        t.sleep(0.5)

    step("TEST BITTI")
