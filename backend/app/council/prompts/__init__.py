"""
Council Prompts
Her komite üyesi için system prompt'lar
"""
from app.council.prompts.risk_analyst import RISK_ANALYST_PROMPT
from app.council.prompts.business_analyst import BUSINESS_ANALYST_PROMPT
from app.council.prompts.legal_expert import LEGAL_EXPERT_PROMPT
from app.council.prompts.media_analyst import MEDIA_ANALYST_PROMPT
from app.council.prompts.sector_expert import SECTOR_EXPERT_PROMPT
from app.council.prompts.moderator import MODERATOR_PROMPT


PROMPTS = {
    "risk_analyst": RISK_ANALYST_PROMPT,
    "business_analyst": BUSINESS_ANALYST_PROMPT,
    "legal_expert": LEGAL_EXPERT_PROMPT,
    "media_analyst": MEDIA_ANALYST_PROMPT,
    "sector_expert": SECTOR_EXPERT_PROMPT,
    "moderator": MODERATOR_PROMPT,
}


def get_system_prompt(member_id: str) -> str:
    """Üye için system prompt getir"""
    return PROMPTS.get(member_id, "")


__all__ = [
    "get_system_prompt",
    "PROMPTS",
    "RISK_ANALYST_PROMPT",
    "BUSINESS_ANALYST_PROMPT",
    "LEGAL_EXPERT_PROMPT",
    "MEDIA_ANALYST_PROMPT",
    "SECTOR_EXPERT_PROMPT",
    "MODERATOR_PROMPT",
]
