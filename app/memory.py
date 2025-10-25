# app/memory.py
# حافظه‌ی ساده‌ی مکالمه برای نگهداری چند نوبت اخیر گفتگو

from dataclasses import dataclass, field
from typing import List


@dataclass
class Turn:
    """نماینده‌ی یک نوبت گفتگو (کاربر یا منتور)."""
    role: str   # "user" یا "assistant"
    content: str


@dataclass
class ChatMemory:
    """حافظه‌ی مکالمه که آخرین n نوبت را نگه می‌دارد."""
    turns: List[Turn] = field(default_factory=list)
    max_turns: int = 8  # حداکثر نوبت‌هایی که ذخیره می‌شوند

    def add(self, role: str, content: str):
        """افزودن یک نوبت جدید به حافظه"""
        self.turns.append(Turn(role=role, content=content))
        # فقط آخرین n نوبت نگه‌داری شود
        if len(self.turns) > self.max_turns:
            self.turns = self.turns[-self.max_turns:]

    def as_text(self) -> str:
        """برگرداندن متن کامل حافظه برای دادن به مدل زبانی"""
        lines = []
        for t in self.turns:
            prefix = "کاربر:" if t.role == "user" else "منتور:"
            lines.append(f"{prefix} {t.content}")
        return "\n".join(lines)
