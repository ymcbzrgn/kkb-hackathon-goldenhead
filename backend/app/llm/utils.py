"""
LLM Utilities
Yardımcı fonksiyonlar
"""
import base64
import io
from typing import List, Optional
from pathlib import Path


def encode_image_to_base64(image_path: str) -> str:
    """
    Görsel dosyasını base64'e çevir.

    Args:
        image_path: Görsel dosya yolu

    Returns:
        str: Base64 encoded string
    """
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def encode_bytes_to_base64(data: bytes) -> str:
    """Bytes'ı base64'e çevir"""
    return base64.b64encode(data).decode("utf-8")


def decode_base64_to_bytes(base64_str: str) -> bytes:
    """Base64'ü bytes'a çevir"""
    return base64.b64decode(base64_str)


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
    """
    Metni chunk'lara böl (RAG için).

    Args:
        text: Bölünecek metin
        chunk_size: Chunk boyutu (karakter)
        overlap: Örtüşme miktarı

    Returns:
        List[str]: Chunk listesi
    """
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        # Kelime sınırında kes
        if end < len(text):
            # Son boşluğu bul
            last_space = text.rfind(" ", start, end)
            if last_space > start:
                end = last_space

        chunks.append(text[start:end].strip())
        start = end - overlap

    return chunks


def estimate_tokens(text: str) -> int:
    """
    Token sayısını tahmin et (yaklaşık).

    Args:
        text: Metin

    Returns:
        int: Tahmini token sayısı
    """
    # Basit tahmin: ortalama 4 karakter = 1 token
    return len(text) // 4


def truncate_to_token_limit(text: str, max_tokens: int = 4000) -> str:
    """
    Metni token limitine göre kırp.

    Args:
        text: Metin
        max_tokens: Maksimum token

    Returns:
        str: Kırpılmış metin
    """
    estimated = estimate_tokens(text)
    if estimated <= max_tokens:
        return text

    # Yaklaşık karakter limitini hesapla
    char_limit = max_tokens * 4
    return text[:char_limit] + "..."


def format_messages_for_context(messages: List[dict]) -> str:
    """
    Mesaj listesini context string'e çevir.

    Args:
        messages: Mesaj listesi

    Returns:
        str: Formatlı context
    """
    formatted = []
    for msg in messages:
        role = msg.get("role", "user").upper()
        content = msg.get("content", "")
        formatted.append(f"{role}: {content}")

    return "\n\n".join(formatted)


def extract_json_from_response(response: str) -> Optional[dict]:
    """
    LLM yanıtından JSON çıkar.

    Args:
        response: LLM yanıtı

    Returns:
        dict or None: Çıkarılan JSON
    """
    import json
    import re

    # Direkt JSON parse dene
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    # Code block içinde ara
    json_pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
    matches = re.findall(json_pattern, response)

    for match in matches:
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue

    # { } arasını bul
    brace_pattern = r"\{[\s\S]*\}"
    matches = re.findall(brace_pattern, response)

    for match in matches:
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue

    return None


def clean_llm_response(response: str) -> str:
    """
    LLM yanıtını temizle.

    Args:
        response: Ham yanıt

    Returns:
        str: Temizlenmiş yanıt
    """
    # Başlangıç ve sondaki boşlukları temizle
    response = response.strip()

    # Markdown code block'ları kaldır (eğer sadece metin isteniyorsa)
    # response = re.sub(r"```[\s\S]*?```", "", response)

    # Çift boşlukları tek boşluğa çevir
    response = " ".join(response.split())

    return response


def build_system_prompt(
    base_prompt: str,
    context: Optional[str] = None,
    examples: Optional[List[str]] = None,
    constraints: Optional[List[str]] = None
) -> str:
    """
    Sistem prompt'u oluştur.

    Args:
        base_prompt: Ana prompt
        context: Ek context
        examples: Örnek listesi
        constraints: Kısıtlamalar

    Returns:
        str: Tam sistem prompt'u
    """
    parts = [base_prompt]

    if context:
        parts.append(f"\n## Bağlam\n{context}")

    if examples:
        parts.append("\n## Örnekler")
        for i, example in enumerate(examples, 1):
            parts.append(f"{i}. {example}")

    if constraints:
        parts.append("\n## Kısıtlamalar")
        for constraint in constraints:
            parts.append(f"- {constraint}")

    return "\n".join(parts)
