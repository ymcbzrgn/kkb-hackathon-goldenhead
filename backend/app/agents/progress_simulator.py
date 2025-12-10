"""
Progress Simulator
K8s HTTP cagrilari beklerken gercekci ilerleme simule eder.

Kullanim:
    simulator = ProgressSimulator(progress_callback, config, messages)
    task = asyncio.create_task(simulator.start())

    # ... gercek is ...

    simulator.stop()
    await task
"""
import asyncio
from typing import Callable, Optional, List
from dataclasses import dataclass


@dataclass
class SimulatorConfig:
    """Progress simulasyon konfigurasyonu."""
    start_progress: int = 10       # Baslangic yuzde
    max_progress: int = 90         # Maksimum yuzde (100'e birakmak icin)
    initial_speed: float = 2.0     # Saniyede ilerleme
    decay_rate: float = 0.95       # Hiz azalma orani (zamanla yavaslar)
    tick_interval: float = 1.0     # Guncelleme araligi (saniye)
    min_speed: float = 0.5         # Minimum ilerleme hizi


class ProgressSimulator:
    """
    K8s beklerken gercekci progress simule eder.

    Exponential decay kullanarak:
    - Baslangicta hizli (setup asamasi)
    - Zamanla yavaslar (gercek is)
    - 100%'e hic ulasmaz (tamamlanana kadar)
    """

    def __init__(
        self,
        progress_callback: Callable[[int, str], None],
        config: Optional[SimulatorConfig] = None,
        messages: Optional[List[str]] = None
    ):
        self.callback = progress_callback
        self.config = config or SimulatorConfig()
        self.running = False
        self.current_progress = self.config.start_progress
        self.current_speed = self.config.initial_speed

        # Varsayilan mesajlar
        self.messages = messages or [
            "Baglanti kuruluyor...",
            "Veri toplaniyor...",
            "Analiz ediliyor...",
            "Sonuclar isleniyor...",
            "Dogrulama yapiliyor...",
        ]

    async def start(self):
        """Simulasyonu baslat."""
        self.running = True

        while self.running and self.current_progress < self.config.max_progress:
            # Ilerleme hesapla
            increment = max(self.current_speed, self.config.min_speed)
            self.current_progress = min(
                self.current_progress + increment,
                self.config.max_progress
            )

            # Mesaj sec
            message = self._get_message()

            # Progress bildir
            self.callback(int(self.current_progress), message)

            # Hizi azalt (zamanla yavasla)
            self.current_speed *= self.config.decay_rate

            # Sonraki tick'i bekle
            await asyncio.sleep(self.config.tick_interval)

    def stop(self):
        """Simulasyonu durdur."""
        self.running = False

    def _get_message(self) -> str:
        """Ilerlemeye gore mesaj sec."""
        if not self.messages:
            return "Isleniyor..."

        progress_range = self.config.max_progress - self.config.start_progress
        if progress_range <= 0:
            return self.messages[0]

        # Mesajlari ilerlemeye gore dagit
        relative_progress = self.current_progress - self.config.start_progress
        target_index = int(relative_progress / (progress_range / len(self.messages)))
        target_index = min(target_index, len(self.messages) - 1)
        return self.messages[target_index]
