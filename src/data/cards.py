"""cards.py: 具体卡牌定义。

包含:
- Strike 打击：单目标攻击牌，6 伤害
- Defend 防御：获得 5 护甲
- Bash 重击：8 伤害 + 2 易伤
- 生存者：7 护甲 + 弃1张手牌（PendingCardSelection）
- 祭品：失去6生命 + 抽3张 + 获得3能量
- 机器学习：能力牌，每回合多抽1张（回合多抽 buff）
- 灼伤：状态牌，不可打出，回合结束自动打出造成3伤害
- 倾斜：X费，打出抽牌堆顶 X 张牌
- 状态牌: Wound 伤口, Dazed 晕眩

设计原则:
1. 攻击牌经 CardEffects.deal_damage 修正伤害。
2. 选择类效果设置 battle.pending_action，由玩家完成选择后 resolve。
3. X费牌用 x_value 参数接收实际消耗能量。
4. 处理区机制保证嵌套结算安全（倾斜打出倾斜）。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from src.core.buff_system import BuffSystem
from src.core.card import Card
from src.core.card_effects import CardEffects
from src.core.entity import Entity
from src.core.pending_action import PendingCardSelection

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

    def play(self, user, target=None, battle=None, x_value=0):
        assert target is not None, "[Strike] 攻击牌必须指定目标"
        assert battle is not None, "[Strike] 需要 battle 引用"
        CardEffects.deal_damage(battle, user, target, self.DAMAGE)


class Bash(Card):
    """重击：8 伤害 + 2 易伤，费用 2。"""

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

    def play(self, user, target=None, battle=None, x_value=0):
        assert target is not None
        assert battle is not None
        CardEffects.deal_damage(battle, user, target, self.DAMAGE)
        CardEffects.add_buff(target, BuffSystem.BUFF_VULNERABLE, self.VULNERABLE_STACKS)


# ====================================================================== #
# 技能牌
# ====================================================================== #
class Defend(Card):
    """防御：获得 5 护甲，费用 1。"""

    BLOCK: int = 5

    def __init__(self) -> None:
        super().__init__(
            name="防御",
            cost=1,
            card_type=Card.TYPE_SKILL,
            description=f"获得 {self.BLOCK} 点护甲。",
        )

    def play(self, user, target=None, battle=None, x_value=0):
        CardEffects.gain_block(battle, user, self.BLOCK)


class Survivor(Card):
    """生存者：获得 7 护甲，选择一张手牌丢弃，费用 1。"""

    BLOCK: int = 7

    def __init__(self) -> None:
        super().__init__(
            name="生存者",
            cost=1,
            card_type=Card.TYPE_SKILL,
            description=f"获得 {self.BLOCK} 点护挡。选择一张手牌丢弃。",
        )

    def play(self, user, target=None, battle=None, x_value=0):
        assert battle is not None
        CardEffects.gain_block(battle, user, self.BLOCK)
        # 设置弃牌选择挂起动作
        # 可选手牌 = 当前手牌（生存者已在处理区，不在手牌中）
        selectable = list(user.hand)
        if not selectable:
            logger.info("[Survivor] 无手牌可弃，跳过选择")
            return
        battle.pending_action = PendingCardSelection(
            prompt="选择一张手牌丢弃",
            count=1,
            action="discard",
            cards=list(user.hand),
            callback=lambda cards: None,
        )


class Offering(Card):
    """祭品：失去 6 生命，抽 3 张牌，获得 3 能量，费用 0。"""

    HP_LOSS: int = 6
    DRAW_COUNT: int = 3
    ENERGY_GAIN: int = 3

    def __init__(self) -> None:
        super().__init__(
            name="祭品",
            cost=0,
            card_type=Card.TYPE_SKILL,
            description=f"失去 {self.HP_LOSS} 生命，抽 {self.DRAW_COUNT} 张牌，获得 {self.ENERGY_GAIN} 点能量。",
        )

    def play(self, user, target=None, battle=None, x_value=0):
        CardEffects.lose_hp(user, self.HP_LOSS)
        CardEffects.draw_cards(user, self.DRAW_COUNT)
        CardEffects.gain_energy(user, self.ENERGY_GAIN)


# ====================================================================== #
# 能力牌
# ====================================================================== #
class MachineLearning(Card):
    """机器学习：每回合开始时多抽 1 张牌，费用 1。"""

    DRAW_BUFF_STACKS: int = 1

    def __init__(self) -> None:
        super().__init__(
            name="机器学习",
            cost=1,
            card_type=Card.TYPE_POWER,
            description="每回合开始时多抽 1 张牌。",
        )

    def play(self, user, target=None, battle=None, x_value=0):
        # 获得持久 buff「回合多抽」
        CardEffects.add_buff(user, BuffSystem.BUFF_DRAW_NEXT, self.DRAW_BUFF_STACKS)


# ====================================================================== #
# 状态牌
# ====================================================================== #
class Wound(Card):
    """伤口：状态牌，不可打出。"""

    def __init__(self) -> None:
        super().__init__(
            name="伤口",
            cost=1,
            card_type=Card.TYPE_SKILL,
            description="不可打出。",
            playable=False,
        )

    def play(self, user, target=None, battle=None, x_value=0):
        # 不可手动打出，但被自动打出（如倾斜）时无效果通过
        logger.info("[Wound] 伤口被自动打出，无效果")


class Dazed(Card):
    """晕眩：状态牌，不可打出，费用 0。"""

    def __init__(self) -> None:
        super().__init__(
            name="晕眩",
            cost=0,
            card_type=Card.TYPE_SKILL,
            description="不可打出。占据手牌位。",
            playable=False,
        )

    def play(self, user, target=None, battle=None, x_value=0):
        # 不可手动打出，但被自动打出（如倾斜）时无效果通过
        logger.info("[Dazed] 晕眩被自动打出，无效果")


class Burn(Card):
    """灼伤：状态牌，不能被打出，回合结束时若在手牌中自动打出造成 3 点伤害。

    实现: playable=False + auto_play_end_of_turn=True
    play() 效果: 对自己造成 3 点伤害（无视护甲）
    """

    DAMAGE: int = 3

    def __init__(self) -> None:
        super().__init__(
            name="灼伤",
            cost=1,
            card_type=Card.TYPE_SKILL,
            description="不能被打出。回合结束时若在手牌中，受到 3 点伤害。",
            playable=False,
            auto_play_end_of_turn=True,
        )

    def play(self, user, target=None, battle=None, x_value=0):
        # 对自己造成伤害（无视护甲）
        CardEffects.lose_hp(user, self.DAMAGE)


# ====================================================================== #
# X费牌
# ====================================================================== #
class Whirlwind(Card):
    """倾斜：X费，依次打出抽牌堆顶部的前 X 张牌。

    X = 打出时消耗的所有能量。
    自动打出时 X = 当前能量（不扣）。
    """

    def __init__(self) -> None:
        super().__init__(
            name="倾斜",
            cost=0,
            card_type=Card.TYPE_SKILL,
            description="依次打出抽牌堆顶部的前 X 张牌（X 为本牌消耗的能量数）。",
            is_x_cost=True,
        )

    def play(self, user, target=None, battle=None, x_value=0):
        assert battle is not None, "[Whirlwind] 需要 battle 引用"
        logger.info("[Whirlwind] 倾斜打出，x_value=%d", x_value)
        if x_value <= 0:
            logger.info("[Whirlwind] x_value=0，空效果")
            return
        # 调用控制器的自动打牌接口（处理抽牌堆不足/嵌套）
        battle.auto_play_from_draw_top(x_value)


# ====================================================================== #
# 技能牌（消耗类）
# ====================================================================== #
class Hologram(Card):
    """全息影像：1c，获得4点格挡，选择弃牌堆中一张牌加入手牌。消耗。"""

    BLOCK: int = 4

    def __init__(self) -> None:
        super().__init__(
            name="全息影像",
            cost=1,
            card_type=Card.TYPE_SKILL,
            description=f"获得 {self.BLOCK} 点格挡。选择弃牌堆中的一张牌加入手牌。",
            exhausts=True,
        )

    def play(self, user, target=None, battle=None, x_value=0):
        assert battle is not None
        CardEffects.gain_block(battle, user, self.BLOCK)
        selectable = list(user.discard_pile)
        if not selectable:
            logger.info("[Hologram] 弃牌堆为空，跳过选择")
            return
        def on_select(cards):
            if cards:
                card = cards[0]
                if card in user.discard_pile:
                    user.discard_pile.remove(card)
                    user.hand.append(card)
                    if battle:
                        battle._log(f"{card.name} 从弃牌堆加入手牌")
        battle.pending_action = PendingCardSelection(
            prompt="从弃牌堆选择一张牌加入手牌",
            count=1,
            action="custom",
            cards=selectable,
            callback=on_select,
        )


# ====================================================================== #
# 指向性技能牌（状态效果类）
# ====================================================================== #
class Domination(Card):
    """主宰：1c 技能牌，使一名敌人获得1层易伤，然后你获得等同于其易伤层数的力量。"""

    def __init__(self):
        super().__init__(name="主宰",cost=1,card_type=Card.TYPE_SKILL,description="使一名敌人获得1层易伤，然后你获得等同于其易伤层数的力量。",needs_target=True)

    def play(self, user, target=None, battle=None, x_value=0):
        assert target is not None
        CardEffects.add_buff(target, BuffSystem.BUFF_VULNERABLE, 1)
        vuln_stacks = target.get_buff_stacks(BuffSystem.BUFF_VULNERABLE)
        CardEffects.add_buff(user, BuffSystem.BUFF_POWER, vuln_stacks)
        if battle: battle._log(f"{user.name} 获得{vuln_stacks}层力量")


class DarkShackles(Card):
    """黑暗镣铐：0c 技能牌，使一名敌人本回合失去8点力量。"""

    POWER_LOSS = 8

    def __init__(self):
        super().__init__(name="黑暗镣铐",cost=0,card_type=Card.TYPE_SKILL,description=f"使一名敌人在本回合失去{self.POWER_LOSS}点力量。",needs_target=True)

    def play(self, user, target=None, battle=None, x_value=0):
        assert target is not None
        CardEffects.add_buff(target, BuffSystem.BUFF_POWER, -self.POWER_LOSS)
        CardEffects.add_buff(target, BuffSystem.BUFF_GAIN_POWER_END, self.POWER_LOSS)
        if battle: battle._log(f"{target.name} 本回合失去{self.POWER_LOSS}力量")


# ====================================================================== #
# 卡牌工厂函数
# ====================================================================== #
def create_wound() -> Card:
    return Wound()


def create_dazed() -> Card:
    return Dazed()


def create_burn() -> Card:
    return Burn()


def create_starter_deck() -> list[Card]:
    """创建初始牌组：5 打击 + 4 防御 + 1 重击。"""
    return ([Strike() for _ in range(5)]
            + [Defend() for _ in range(4)]
            + [Bash()])


def create_test_deck_with_new_cards() -> list[Card]:
    """创建包含 Phase 3 新卡的测试牌组。"""
    return [
        Strike(), Strike(), Strike(),
        Defend(), Defend(),
        Survivor(), Offering(), MachineLearning(), Whirlwind(),
        Hologram(),
    ]