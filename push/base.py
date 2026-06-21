from abc import ABC, abstractmethod
from typing import List, Dict


class AbstractPushChannel(ABC):
    """Abstract base for push channels (WeChat, Feishu, DingTalk, etc.)"""

    @abstractmethod
    def send(self, papers: List[Dict], date: str) -> bool:
        """Send push notification. Returns True on success."""
        ...

    @abstractmethod
    def channel_name(self) -> str:
        """Human-readable channel name for logging."""
        ...
