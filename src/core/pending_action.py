"""pending_action.py: 挂起动作系统。

处理需玩家选择的卡牌效果（弃牌/消耗/变化/三选一）。
打牌过程中若需选择，控制器设置 pending_action 后返回，
View 渲染选择 UI，玩家点击后 resolve_pending 完成。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from .card import Card


@dataclass
class PendingCardSelection:
    """待玩家选择手牌的挂起动作。"""
    prompt: str
    count: int  # 选择数量
    action: str  # discard/exhaust/transform
    callback: Callable[[list[Card]], None]
    exclude: list[Card] = field(default_factory=list)  # 不可选的牌（处理区中的）


@dataclass
class PendingCardChoice:
    """三选一挂起动作。"""
    prompt: str
    options: list[Card]
    callback: Callable[[Optional[Card]], None]


# 类型别名
PendingAction = Optional[PendingCardSelection | PendingCardChoice]
