"""
LLM Model Configurations
KKB Kloudeks API desteklediği modeller
"""
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class ModelConfig:
    """Model konfigürasyonu"""
    id: str
    name: str
    description: str
    context_length: int
    capabilities: List[str]
    recommended_temperature: float
    max_output_tokens: int


AVAILABLE_MODELS = {
    "gpt-oss-120b": ModelConfig(
        id="gpt-oss-120b",
        name="GPT OSS 120B",
        description="Ana chat modeli - council konuşmaları, analiz, rapor yazma",
        context_length=32768,
        capabilities=["chat", "analysis", "summarization", "reasoning"],
        recommended_temperature=0.7,
        max_output_tokens=4096
    ),

    "qwen3-omni-30b": ModelConfig(
        id="qwen3-omni-30b",
        name="Qwen3 Omni 30B",
        description="Vision modeli - PDF okuma, görsel analiz",
        context_length=32768,
        capabilities=["vision", "ocr", "document_analysis", "chat"],
        recommended_temperature=0.3,
        max_output_tokens=4096
    ),

    "qwen3-embedding-8b": ModelConfig(
        id="qwen3-embedding-8b",
        name="Qwen3 Embedding 8B",
        description="Embedding modeli - RAG, semantic search",
        context_length=8192,
        capabilities=["embedding"],
        recommended_temperature=0.0,
        max_output_tokens=0  # Embedding modeli output üretmez
    ),
}


# Model seçim yardımcıları
def get_chat_model() -> str:
    """Ana chat modeli"""
    return "gpt-oss-120b"


def get_vision_model() -> str:
    """Vision modeli"""
    return "qwen3-omni-30b"


def get_embedding_model() -> str:
    """Embedding modeli"""
    return "qwen3-embedding-8b"


def get_model_for_task(task: str) -> str:
    """
    Görev tipine göre uygun model seç.

    Args:
        task: Görev tipi (chat, vision, embedding, analysis, summarization)

    Returns:
        str: Model ID
    """
    task_model_map = {
        "chat": "gpt-oss-120b",
        "analysis": "gpt-oss-120b",
        "summarization": "gpt-oss-120b",
        "reasoning": "gpt-oss-120b",
        "council": "gpt-oss-120b",
        "vision": "qwen3-omni-30b",
        "ocr": "qwen3-omni-30b",
        "pdf": "qwen3-omni-30b",
        "document": "qwen3-omni-30b",
        "embedding": "qwen3-embedding-8b",
        "search": "qwen3-embedding-8b",
        "rag": "qwen3-embedding-8b",
    }

    return task_model_map.get(task.lower(), "gpt-oss-120b")
