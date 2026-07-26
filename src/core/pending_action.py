"""pending_action.py: 挂起动作系统。

处理需玩家选择的卡牌效果（弃牌/消耗/变化/三选一/自定义）。
打牌过程中若需选择，控制器设置 pending_action 后返回，
View 渲染选择 UI，玩家点击后 resolve_pending 完成。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from .card import Card


@dataclass
class PendingCardSelection:
    """待玩家选择卡牌的挂起动作。

    支持动作:
    - discard: 选中牌弃置
    - exhaust: 选中牌消耗
    - custom: 回调自行处理（如加入手牌）
    """
    prompt: str
    count: int  # 选择数量
    action: str  # discard/exhaust/custom
    cards: list[Card]  # 可选的牌（来源不限：手牌/弃牌堆/抽牌堆）
    callback: Callable[[list[Card]], None]


@dataclass
class PendingCardChoice:
    """三选一挂起动作。"""
    prompt: str
    options: list[Card]
    callback: Callable[[Optional[Card]], None]


# 类型别名
PendingAction = Optional[PendingCardSelection | PendingCardChoice]
