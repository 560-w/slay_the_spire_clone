"""card.py: Card 抽象基类。

定义卡牌的通用属性与抽象行为：
- 费用（Cost）
- 名字（Name）
- 类型（Type: Attack / Skill / Power）
- 指向性（needs_target）：是否须选目标，与类别无关
- 消耗（exhausts）：打出后是否进消耗堆
- 可打出（playable）：状态牌为 False
- 抽象 play 方法（由具体卡牌子类实现效果）

设计原则：
1. 使用 abc.ABC 强制具体卡牌必须实现 play。
2. play 方法的 user/target 均为 Entity，battle 为控制器引用（攻击牌需经其
   buff_system 修正伤害），体现多态与解耦。
3. 关键校验与日志记录便于查错。
4. 卡牌效果通过操作传入的实体完成，保持「数据 + 行为」与「流程控制」分离。
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
        cost (int): 费用（能量消耗），必须 >= 0。
        card_type (str): 卡牌类型，取值见类常量。
        description (str): 卡牌效果描述文本（供 UI 展示）。
        needs_target (bool): 是否为指向性牌（须选一个目标），与类别无关。
            - True: 指向性牌（单目标攻击、单体减益技能），打出前须选目标。
            - False: 非指向性牌（自身护甲、全体攻击、能力牌），直接打出结算。
        exhausts (bool): 打出后是否被消耗（进消耗堆，不参与抽-弃循环）。
        playable (bool): 是否可被打出。状态牌（伤口/晕眩）为 False，
            控制器 play_card 会断言拒绝打出。

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
        needs_target: bool = False,
        exhausts: bool = False,
        playable: bool = True,
    ) -> None:
        """初始化一张卡牌。

        Args:
            name: 卡牌名称，非空字符串。
            cost: 费用，必须 >= 0。
            card_type: 卡牌类型，应为 TYPE_ATTACK/TYPE_SKILL/TYPE_POWER 之一。
            description: 效果描述（可选）。
            needs_target: 是否为指向性牌（须选目标），默认 False。与类别无关。
            exhausts: 打出后是否被消耗（进消耗堆），默认 False。
            playable: 是否可被打出，默认 True。状态牌设为 False。

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

        logger.debug(
            "[Card] 创建卡牌: %s (cost=%d, type=%s, needs_target=%s, exhausts=%s)",
            self.name, self.cost, self.card_type, self.needs_target, self.exhausts,
        )

    @abstractmethod
    def play(
        self,
        user: Entity,
        target: Optional[Entity] = None,
        battle: Optional["BattleController"] = None,
    ) -> None:
        """打出卡牌的效果结算。

        由具体卡牌子类实现。例如：
        - 攻击牌: 经 battle.buff_system 修正后 target.take_damage(最终伤害)
        - 技能牌: user.gain_block(...)
        - 能力牌: user.add_buff(...)

        注意: 费用的扣除不应在 play 内部完成，而应由 Player/控制器在
              决定打出时校验并扣除能量后，再调用本方法。这样保持卡牌
              效果与资源管理的职责分离。

        Args:
            user: 打出卡牌的实体（通常是 Player）。
            target: 目标实体（指向性牌必填；非指向性牌为 None）。
            battle: 战斗控制器引用（攻击牌需经其 buff_system 修正伤害）。
                非攻击牌可不使用。为保持向后兼容设为可选。
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