"""
LLM Client
KKB Kloudeks API wrapper
"""
import logging
import httpx
import json
from typing import AsyncGenerator, List, Dict, Optional, Any
from app.core.config import settings
from app.llm.models import AVAILABLE_MODELS, ModelConfig

logger = logging.getLogger(__name__)


class LLMClient:
    """
    KKB Kloudeks LLM API Client.

    Desteklenen modeller:
    - gpt-oss-120b: Ana chat modeli (council konuşmaları, analiz)
    - qwen3-omni-30b: Vision modeli (PDF okuma)
    - qwen3-embedding-8b: Embedding modeli (RAG)
    """

    def __init__(self):
        self.base_url = settings.KKB_API_URL
        self.api_key = settings.KKB_API_KEY
        self.default_model = "gpt-oss-120b"
        self.timeout = httpx.Timeout(120.0, connect=10.0)

    def _get_headers(self) -> Dict[str, str]:
        """API headers"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-oss-120b",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> str:
        """
        Chat completion (non-streaming).

        Args:
            messages: Mesaj listesi [{"role": "user", "content": "..."}]
            model: Kullanılacak model
            temperature: Yaratıcılık (0-1)
            max_tokens: Maksimum token sayısı

        Returns:
            str: Model yanıtı
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._get_headers(),
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    **kwargs
                }
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"].get("content")
            return content if content else ""

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-oss-120b",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Chat completion (streaming).

        Args:
            messages: Mesaj listesi
            model: Kullanılacak model
            temperature: Yaratıcılık
            max_tokens: Maksimum token

        Yields:
            str: Token chunk'ları
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self._get_headers(),
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": True,
                    **kwargs
                }
            ) as response:
                response.raise_for_status()
                try:
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                # Check for API errors in stream
                                if "error" in data:
                                    logger.error(f"LLM API error in stream: {data['error']}")
                                    break
                                delta = data.get("choices", [{}])[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                continue
                except httpx.ReadError as e:
                    logger.error(f"Network read error during LLM stream: {e}")
                    raise
                except httpx.RemoteProtocolError as e:
                    logger.error(f"Remote protocol error during LLM stream: {e}")
                    raise

    async def vision(
        self,
        image_base64: str,
        prompt: str,
        model: str = "qwen3-omni-30b"
    ) -> str:
        """
        Vision API - Görsel/PDF analizi.

        Args:
            image_base64: Base64 encoded görsel
            prompt: Analiz prompt'u
            model: Vision modeli

        Returns:
            str: Analiz sonucu
        """
        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{image_base64}"
                    }
                }
            ]
        }]

        return await self.chat(messages, model=model)

    async def vision_pdf(
        self,
        pdf_pages_base64: List[str],
        prompt: str,
        model: str = "qwen3-omni-30b"
    ) -> str:
        """
        PDF analizi - Birden fazla sayfa.

        Args:
            pdf_pages_base64: Sayfa görsellerinin base64 listesi
            prompt: Analiz prompt'u
            model: Vision modeli

        Returns:
            str: Analiz sonucu
        """
        content = [{"type": "text", "text": prompt}]

        for i, page_base64 in enumerate(pdf_pages_base64):
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{page_base64}"
                }
            })

        messages = [{"role": "user", "content": content}]
        return await self.chat(messages, model=model, max_tokens=4096)

    async def embed(
        self,
        texts: List[str],
        model: str = "qwen3-embedding-8b"
    ) -> List[List[float]]:
        """
        Text embedding.

        Args:
            texts: Metinler
            model: Embedding modeli

        Returns:
            List[List[float]]: Embedding vektörleri
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/embeddings",
                headers=self._get_headers(),
                json={
                    "model": model,
                    "input": texts
                }
            )
            response.raise_for_status()
            data = response.json()
            return [d["embedding"] for d in data["data"]]

    async def embed_single(self, text: str, model: str = "qwen3-embedding-8b") -> List[float]:
        """Tek metin için embedding"""
        embeddings = await self.embed([text], model)
        return embeddings[0]

    async def analyze_sentiment(
        self,
        text: str,
        model: str = "gpt-oss-120b"
    ) -> Dict[str, Any]:
        """
        Sentiment analizi.

        Args:
            text: Analiz edilecek metin

        Returns:
            dict: {sentiment: str, score: float, explanation: str}
        """
        messages = [{
            "role": "system",
            "content": """Sen bir sentiment analiz uzmanısın.
Verilen metni analiz et ve JSON formatında yanıt ver:
{
    "sentiment": "pozitif" | "negatif" | "notr",
    "score": -1.0 ile 1.0 arası (negatiften pozitife),
    "explanation": "kısa açıklama"
}
Sadece JSON döndür, başka bir şey yazma."""
        }, {
            "role": "user",
            "content": text
        }]

        response = await self.chat(messages, model=model, temperature=0.3)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {
                "sentiment": "notr",
                "score": 0.0,
                "explanation": "Analiz yapılamadı"
            }

    async def extract_structured_data(
        self,
        text: str,
        schema: Dict[str, Any],
        model: str = "gpt-oss-120b"
    ) -> Dict[str, Any]:
        """
        Yapısal veri çıkarma.

        Args:
            text: Kaynak metin
            schema: İstenilen JSON şeması

        Returns:
            dict: Çıkarılan veriler
        """
        messages = [{
            "role": "system",
            "content": f"""Verilen metinden aşağıdaki şemaya uygun veri çıkar.
Şema: {json.dumps(schema, ensure_ascii=False)}
Sadece JSON döndür, başka bir şey yazma."""
        }, {
            "role": "user",
            "content": text
        }]

        response = await self.chat(messages, model=model, temperature=0.1)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {}

    def get_model_config(self, model: str) -> Optional[ModelConfig]:
        """Model konfigürasyonunu getir"""
        return AVAILABLE_MODELS.get(model)
