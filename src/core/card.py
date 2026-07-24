"""card.py: Card 抽象基类。

定义卡牌的通用属性与抽象行为：
- 费用（Cost）
- 名字（Name）
- 类型（Type: Attack / Skill / Power）
- 抽象 play 方法（由具体卡牌子类实现效果）

设计原则：
1. 使用 abc.ABC 强制具体卡牌必须实现 play。
2. play 方法的 user/target 均为 Entity，体现多态与解耦。
3. 关键校验（cost>=0）与日志记录便于查错。
4. 卡牌本身不持有状态机的引用，效果结算通过操作传入的实体完成，
   保持「数据 + 行为」与「流程控制」分离。
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Optional

from .entity import Entity

logger = logging.getLogger(__name__)


class Card(ABC):
    """卡牌抽象基类。

    属性:
        name (str): 卡牌名称。
        cost (int): 费用（能量消耗），必须 >= 0。
        card_type (str): 卡牌类型，取值见类常量。
        description (str): 卡牌效果描述文本（供 UI 展示）。

    类常量:
        TYPE_ATTACK: 攻击牌
        TYPE_SKILL:  技能牌
        TYPE_POWER:  能力牌（打出后常驻增益）
    """

    # 卡牌类型常量，避免魔法字符串
    TYPE_ATTACK: str = "Attack"
    TYPE_SKILL: str = "Skill"
    TYPE_POWER: str = "Power"

    def __init__(
        self,
        name: str,
        cost: int,
        card_type: str,
        description: str = "",
    ) -> None:
        """初始化一张卡牌。

        Args:
            name: 卡牌名称，非空字符串。
            cost: 费用，必须 >= 0。
            card_type: 卡牌类型，应为 TYPE_ATTACK/TYPE_SKILL/TYPE_POWER 之一。
            description: 效果描述（可选）。

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

        logger.debug(
            "[Card] 创建卡牌: %s (cost=%d, type=%s)", self.name, self.cost, self.card_type
        )

    @abstractmethod
    def play(self, user: Entity, target: Optional[Entity] = None) -> None:
        """打出卡牌的效果结算。

        由具体卡牌子类实现。例如：
        - 攻击牌: target.take_damage(user 的伤害)
        - 技能牌: user.gain_block(...)
        - 能力牌: user.add_buff(...)

        注意: 费用的扣除不应在 play 内部完成，而应由 Player/控制器在
              决定打出时校验并扣除能量后，再调用本方法。这样保持卡牌
              效果与资源管理的职责分离。

        Args:
            user: 打出卡牌的实体（通常是 Player）。
            target: 目标实体（攻击牌通常需要敌人；技能/能力牌可为 None）。
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

    # ------------------------------------------------------------------ #
    # 魔术方法
    # ------------------------------------------------------------------ #
    def __str__(self) -> str:
        """可读的卡牌信息字符串。"""
        return f"[{self.card_type}] {self.name} (费用:{self.cost}) - {self.description}"