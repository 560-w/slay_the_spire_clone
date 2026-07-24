"""cards.py: 具体卡牌定义。

包含:
- Strike 打击：单目标攻击牌，6 伤害，费用 1，needs_target=True
- Defend 防御：非指向性技能牌，5 护甲，费用 1
- Bash 重击：单目标攻击牌，8 伤害+2 易伤，费用 2，needs_target=True
- 状态牌:
  - Wound 伤口：不可打出（playable=False）
  - Dazed 晕眩：不可打出（playable=False），费用 0 占手牌

设计原则:
1. 攻击牌 play 内部经 battle.buff_system 修正伤害后再 take_damage。
2. 状态牌 playable=False，控制器会拒绝打出。
3. 每张卡牌的 needs_target 独立设定，与类别无关。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from src.core.buff_system import BuffSystem
from src.core.card import Card
from src.core.entity import Entity

if TYPE_CHECKING:
    from src.controllers.battle import BattleController

logger = logging.getLogger(__name__)


# ====================================================================== #
# 攻击牌
# ====================================================================== #
class Strike(Card):
    """打击：单目标攻击牌，造成 6 点伤害，费用 1。"""

    DAMAGE: int = 6

    def __init__(self) -> None:
        super().__init__(
            name="打击",
            cost=1,
            card_type=Card.TYPE_ATTACK,
            description=f"造成 {self.DAMAGE} 点伤害。",
            needs_target=True,
        )

    def play(
        self,
        user: Entity,
        target: Optional[Entity] = None,
        battle: Optional["BattleController"] = None,
    ) -> None:
        """对目标造成伤害（经 buff 修正）。

        Args:
            user: 打出者。
            target: 目标敌人，必须非 None。
            battle: 战斗控制器（提供 buff_system）。

        Raises:
            AssertionError: 当 target 或 battle 为 None 时触发。
        """
        assert target is not None, "[Strike] 攻击牌必须指定目标"
        assert battle is not None, "[Strike] 需要 battle 引用以修正伤害"

        # 经攻击方 buff 修正（力量/虚弱）
        outgoing: int = battle.buff_system.compute_outgoing_damage(user, self.DAMAGE)
        # 经受击方 buff 修正（易伤）
        incoming: int = battle.buff_system.compute_incoming_damage(target, outgoing)

        logger.info("[Card] %s 打出 %s → %s (基础%d → 最终%d)",
                    user.name, self.name, target.name, self.DAMAGE, incoming)
        target.take_damage(incoming)


class Bash(Card):
    """重击：单目标攻击牌，造成 8 伤害并施加 2 层易伤，费用 2。"""

    DAMAGE: int = 8
    VULNERABLE_STACKS: int = 2

    def __init__(self) -> None:
        super().__init__(
            name="重击",
            cost=2,
            card_type=Card.TYPE_ATTACK,
            description=f"造成 {self.DAMAGE} 伤害，施加 {self.VULNERABLE_STACKS} 层易伤。",
            needs_target=True,
        )

    def play(
        self,
        user: Entity,
        target: Optional[Entity] = None,
        battle: Optional["BattleController"] = None,
    ) -> None:
        """对目标造成伤害并施加易伤。

        Args:
            user: 打出者。
            target: 目标敌人，必须非 None。
            battle: 战斗控制器。
        """
        assert target is not None, "[Bash] 攻击牌必须指定目标"
        assert battle is not None, "[Bash] 需要 battle 引用"

        # 伤害修正
        outgoing: int = battle.buff_system.compute_outgoing_damage(user, self.DAMAGE)
        incoming: int = battle.buff_system.compute_incoming_damage(target, outgoing)
        logger.info("[Card] %s 打出 %s → %s (基础%d → 最终%d)",
                    user.name, self.name, target.name, self.DAMAGE, incoming)
        target.take_damage(incoming)

        # 施加易伤
        target.add_buff(BuffSystem.BUFF_VULNERABLE, self.VULNERABLE_STACKS)


# ====================================================================== #
# 技能牌
# ====================================================================== #
class Defend(Card):
    """防御：非指向性技能牌，获得 5 护甲，费用 1。"""

    BLOCK: int = 5

    def __init__(self) -> None:
        super().__init__(
            name="防御",
            cost=1,
            card_type=Card.TYPE_SKILL,
            description=f"获得 {self.BLOCK} 点护甲。",
            needs_target=False,
        )

    def play(
        self,
        user: Entity,
        target: Optional[Entity] = None,
        battle: Optional["BattleController"] = None,
    ) -> None:
        """使用者获得护甲。"""
        logger.info("[Card] %s 打出 %s", user.name, self.name)
        user.gain_block(self.BLOCK)


# ====================================================================== #
# 状态牌（不可打出）
# ====================================================================== #
class Wound(Card):
    """伤口：状态牌，不可打出。回合结束时造成 2 点伤害（由状态效果模拟）。

    Phase 2 简化实现：仅作为占位状态牌塞入手牌占位，不实际造成伤害
    （完整状态效果系统留待后续 Phase）。
    """

    def __init__(self) -> None:
        super().__init__(
            name="伤口",
            cost=1,
            card_type=Card.TYPE_SKILL,
            description="不可打出。回合结束时受到 2 点伤害（暂未实现）。",
            needs_target=False,
            playable=False,
        )

    def play(
        self,
        user: Entity,
        target: Optional[Entity] = None,
        battle: Optional["BattleController"] = None,
    ) -> None:
        """状态牌无法打出，此方法不应被调用。"""
        raise RuntimeError("[Wound] 状态牌无法打出")


class Dazed(Card):
    """晕眩：状态牌，不可打出，费用 0，占用手牌位。"""

    def __init__(self) -> None:
        super().__init__(
            name="晕眩",
            cost=0,
            card_type=Card.TYPE_SKILL,
            description="不可打出。占据手牌位。",
            needs_target=False,
            playable=False,
        )

    def play(
        self,
        user: Entity,
        target: Optional[Entity] = None,
        battle: Optional["BattleController"] = None,
    ) -> None:
        """状态牌无法打出，此方法不应被调用。"""
        raise RuntimeError("[Dazed] 状态牌无法打出")


# ====================================================================== #
# 卡牌工厂函数（供敌人 ADD_CARD 意图创建状态牌，及初始牌组构建）
# ====================================================================== #
def create_wound() -> Card:
    """创建一张「伤口」状态牌。"""
    return Wound()


def create_dazed() -> Card:
    """创建一张「晕眩」状态牌。"""
    return Dazed()


def create_starter_deck() -> list[Card]:
    """创建初始牌组：5 打击 + 4 防御 + 1 重击。"""
    return ([Strike() for _ in range(5)]
            + [Defend() for _ in range(4)]
            + [Bash()])