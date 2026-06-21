from pydantic import BaseModel, Field
from typing import List


class RelevanceFilter(BaseModel):
    """LLM structured output for relevance filtering"""

    is_relevant: bool = Field(description="是否与目标研究方向相关")
    matched_topics: List[str] = Field(description="匹配的子方向 id 列表，如 ['vla', 'navigation']")
    from_watchlist: bool = Field(description="是否来自关注列表（名组/大厂/名作者）")
    confidence: float = Field(description="0-1 置信度")
    reason: str = Field(description="一句话相关性理由")
