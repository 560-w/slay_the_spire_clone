"""card.py: Card 抽象基类。

定义卡牌的通用属性与抽象行为：
- 费用（Cost）：固定费用，或 X 费（消耗所有能量）
- 名字（Name）/ 类型（Type: Attack / Skill / Power）
- 指向性（needs_target）：是否须选目标，与类别无关
- 词条:
  - 消耗（exhausts）：打出后进消耗堆
  - 虚无（ethereal）：回合结束时若在手牌则消耗
  - 不能被打出（playable=False）：无法手动打出，但可被自动打出
  - 回合结束自动打出（auto_play_end_of_turn）：满足条件时自动打出
  - X 费（is_x_cost）：打出消耗所有能量，x_value 取实际消耗值

设计原则:
1. play() 签名含 x_value（X费牌取实际消耗能量数）与 battle 引用。
2. 词条独立设定，与类别无关。
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

from .entity import Entity

if TYPE_CHECKING:
    from ..controllers.battle import BattleController

logger = logging.getLogger(__name__)


class Card(ABC):
    """卡牌抽象基类。

    属性:
        name (str): 卡牌名称。
        cost (int): 费用（能量消耗），>=0。X费牌此处无意义，用 is_x_cost 标识。
        card_type (str): 卡牌类型，取值见类常量。
        description (str): 卡牌效果描述文本（供 UI 展示）。
        needs_target (bool): 是否为指向性牌（须选目标），与类别无关。
        exhausts (bool): 消耗词条，打出后进消耗堆。
        playable (bool): 是否可手动打出。状态牌为 False。
        ethereal (bool): 虚无词条，回合结束时若在手牌则消耗。
        is_x_cost (bool): X费词条，打出消耗所有能量。
        auto_play_end_of_turn (bool): 回合结束自动打出词条。
    """

    # 卡牌类型常量
    TYPE_ATTACK: str = "Attack"
    TYPE_SKILL: str = "Skill"
    TYPE_POWER: str = "Power"

    def __init__(
        self,
        name: str,
        cost: int,
        card_type: str,
        description: str = "",
        needs_target: bool = False,
        exhausts: bool = False,
        playable: bool = True,
        ethereal: bool = False,
        is_x_cost: bool = False,
        auto_play_end_of_turn: bool = False,
    ) -> None:
        """初始化一张卡牌。

        Args:
            name: 卡牌名称，非空字符串。
            cost: 费用，>=0。X费牌此值忽略。
            card_type: 卡牌类型，应为 TYPE_* 之一。
            description: 效果描述。
            needs_target: 是否为指向性牌，默认 False。
            exhausts: 消耗词条，默认 False。
            playable: 是否可手动打出，默认 True。
            ethereal: 虚无词条，默认 False。
            is_x_cost: X费词条，默认 False。
            auto_play_end_of_turn: 回合结束自动打出，默认 False。

        Raises:
            AssertionError: 当 name 为空、cost 为负、card_type 非法时触发。
        """
        assert isinstance(name, str) and name, "[Card] 卡牌名称不能为空"
        assert cost >= 0, f"[Card] 卡牌费用必须 >= 0，收到 {cost}"
        valid_types = {self.TYPE_ATTACK, self.TYPE_SKILL, self.TYPE_POWER}
        assert card_type in valid_types, (
            f"[Card] 卡牌类型必须为 {valid_types} 之一，收到 {card_type}"
        )

        self.name: str = name
        self.cost: int = cost
        self.card_type: str = card_type
        self.description: str = description
        self.needs_target: bool = needs_target
        self.exhausts: bool = exhausts
        self.playable: bool = playable
        self.ethereal: bool = ethereal
        self.is_x_cost: bool = is_x_cost
        self.auto_play_end_of_turn: bool = auto_play_end_of_turn

        logger.debug(
            "[Card] 创建卡牌: %s (cost=%d, type=%s, needs_target=%s, "
            "exhausts=%s, ethereal=%s, x_cost=%s, auto=%s)",
            self.name, self.cost, self.card_type, self.needs_target,
            self.exhausts, self.ethereal, self.is_x_cost, self.auto_play_end_of_turn,
        )

    @abstractmethod
    def play(
        self,
        user: Entity,
        target: Optional[Entity] = None,
        battle: Optional["BattleController"] = None,
        x_value: int = 0,
    ) -> None:
        """打出卡牌的效果结算。

        注意: 费用扣除由控制器在打出前完成，play 内只做效果结算。
        挂起选择（如弃牌）由 play 内设置 battle.pending_action 实现。

        Args:
            user: 打出卡牌的实体（通常是 Player）。
            target: 目标实体（指向性牌必填；非指向性牌为 None）。
            battle: 战斗控制器引用（攻击牌需经其 buff_system 修正伤害，
                选择类效果需设置 battle.pending_action）。
            x_value: X费牌的实际消耗能量数；非X费牌为0。
        """
        raise NotImplementedError

    # ------------------------------------------------------------------ #
    # 便捷查询
    # ------------------------------------------------------------------ #
    @property
    def is_attack(self) -> bool:
        """是否为攻击牌。"""
        return self.card_type == self.TYPE_ATTACK

    @property
    def is_skill(self) -> bool:
        """是否为技能牌。"""
        return self.card_type == self.TYPE_SKILL

    @property
    def is_power(self) -> bool:
        """是否为能力牌。"""
        return self.card_type == self.TYPE_POWER

    def get_display_cost(self) -> str:
        """获取用于 UI 显示的费用字符串（X费牌显示为 'X'）。"""
        return "X" if self.is_x_cost else str(self.cost)

    # ------------------------------------------------------------------ #
    # 魔术方法
    # ------------------------------------------------------------------ #
    def __str__(self) -> str:
        """可读的卡牌信息字符串。"""
        tags: list[str] = []
        if self.exhausts:
            tags.append("消耗")
        if self.ethereal:
            tags.append("虚无")
        if not self.playable:
            tags.append("不能打出")
        if self.is_x_cost:
            tags.append("X费")
        if self.auto_play_end_of_turn:
            tags.append("自动打出")
        tag_str = f" [{','.join(tags)}]" if tags else ""
        return f"[{self.card_type}] {self.name} (费用:{self.get_display_cost()}){tag_str} - {self.description}"