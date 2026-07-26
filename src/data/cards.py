"""cards.py: 具体卡牌定义。

包含:
- 普通：Strike 打击, Defend 防御, Wound 伤口, Dazed 晕眩, Burn 灼伤, IronWave 铁壁波, PommelStrike 剑柄打击
- 罕见：Bash 重击, Survivor 生存者, Hologram 全息影像, DarkShackles 黑暗镣铐, FlameBarrier 火焰屏障, ShrugItOff 耸肩无视
- 稀有：Offering 祭品, MachineLearning 机器学习, Whirlwind 倾斜, Domination 主宰, Impervious 不可侵犯, DemonForm 恶魔形态

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
from src.core.card import Card, CardRarity
from src.core.card_effects import CardEffects
from src.core.entity import Entity
from src.core.pending_action import PendingCardSelection

if TYPE_CHECKING:
    from src.controllers.battle import BattleController

logger = logging.getLogger(__name__)


# ====================================================================== #
# 普通攻击牌
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
        self.rarity = CardRarity.COMMON

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
        self.rarity = CardRarity.UNCOMMON

    def play(self, user, target=None, battle=None, x_value=0):
        assert target is not None
        assert battle is not None
        CardEffects.deal_damage(battle, user, target, self.DAMAGE)
        CardEffects.add_buff(target, BuffSystem.BUFF_VULNERABLE, self.VULNERABLE_STACKS)


class IronWave(Card):
    """铁壁波：1c，造成 5 伤害，获得 5 护甲。"""

    DAMAGE: int = 5
    BLOCK: int = 5

    def __init__(self) -> None:
        super().__init__(
            name="铁壁波",
            cost=1,
            card_type=Card.TYPE_ATTACK,
            description=f"造成 {self.DAMAGE} 伤害，获得 {self.BLOCK} 护甲。",
            needs_target=True,
        )
        self.rarity = CardRarity.COMMON

    def play(self, user, target=None, battle=None, x_value=0):
        assert target is not None
        assert battle is not None
        CardEffects.deal_damage(battle, user, target, self.DAMAGE)
        CardEffects.gain_block(battle, user, self.BLOCK)


class PommelStrike(Card):
    """剑柄打击：1c，造成 8 伤害，抽 1 张牌。"""

    DAMAGE: int = 8
    DRAW: int = 1

    def __init__(self) -> None:
        super().__init__(
            name="剑柄打击",
            cost=1,
            card_type=Card.TYPE_ATTACK,
            description=f"造成 {self.DAMAGE} 伤害，抽 {self.DRAW} 张牌。",
            needs_target=True,
        )
        self.rarity = CardRarity.COMMON

    def play(self, user, target=None, battle=None, x_value=0):
        assert target is not None
        assert battle is not None
        CardEffects.deal_damage(battle, user, target, self.DAMAGE)
        CardEffects.draw_cards(user, self.DRAW)


# ====================================================================== #
# 普通技能牌
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
        self.rarity = CardRarity.COMMON

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
        self.rarity = CardRarity.UNCOMMON

    def play(self, user, target=None, battle=None, x_value=0):
        assert battle is not None
        CardEffects.gain_block(battle, user, self.BLOCK)
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


class ShrugItOff(Card):
    """耸肩无视：1c，获得 8 护甲，抽 1 张牌。"""

    BLOCK: int = 8
    DRAW: int = 1

    def __init__(self) -> None:
        super().__init__(
            name="耸肩无视",
            cost=1,
            card_type=Card.TYPE_SKILL,
            description=f"获得 {self.BLOCK} 点护甲，抽 {self.DRAW} 张牌。",
        )
        self.rarity = CardRarity.UNCOMMON

    def play(self, user, target=None, battle=None, x_value=0):
        CardEffects.gain_block(battle, user, self.BLOCK)
        CardEffects.draw_cards(user, self.DRAW)


class FlameBarrier(Card):
    """火焰屏障：2c，获得 12 护甲，获得 3 层荆棘。"""

    BLOCK: int = 12
    THORNS: int = 3

    def __init__(self) -> None:
        super().__init__(
            name="火焰屏障",
            cost=2,
            card_type=Card.TYPE_SKILL,
            description=f"获得 {self.BLOCK} 点护甲，获得 {self.THORNS} 层荆棘。",
        )
        self.rarity = CardRarity.UNCOMMON

    def play(self, user, target=None, battle=None, x_value=0):
        CardEffects.gain_block(battle, user, self.BLOCK)
        CardEffects.add_buff(user, BuffSystem.BUFF_THORNS, self.THORNS)


# ====================================================================== #
# 稀有技能牌
# ====================================================================== #
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
        self.rarity = CardRarity.RARE

    def play(self, user, target=None, battle=None, x_value=0):
        CardEffects.lose_hp(user, self.HP_LOSS)
        CardEffects.draw_cards(user, self.DRAW_COUNT)
        CardEffects.gain_energy(user, self.ENERGY_GAIN)


class Impervious(Card):
    """不可侵犯：2c，获得 30 护甲。消耗。"""

    BLOCK: int = 30

    def __init__(self) -> None:
        super().__init__(
            name="不可侵犯",
            cost=2,
            card_type=Card.TYPE_SKILL,
            description=f"获得 {self.BLOCK} 点护甲。",
            exhausts=True,
        )
        self.rarity = CardRarity.RARE

    def play(self, user, target=None, battle=None, x_value=0):
        CardEffects.gain_block(battle, user, self.BLOCK)


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
        self.rarity = CardRarity.RARE

    def play(self, user, target=None, battle=None, x_value=0):
        CardEffects.add_buff(user, BuffSystem.BUFF_DRAW_NEXT, self.DRAW_BUFF_STACKS)


class DemonForm(Card):
    """恶魔形态：3c，回合结束时获得 2 层力量。"""

    POWER_GAIN: int = 2

    def __init__(self) -> None:
        super().__init__(
            name="恶魔形态",
            cost=3,
            card_type=Card.TYPE_POWER,
            description=f"每回合结束时获得 {self.POWER_GAIN} 层力量。",
        )
        self.rarity = CardRarity.RARE

    def play(self, user, target=None, battle=None, x_value=0):
        CardEffects.add_buff(user, BuffSystem.BUFF_GAIN_POWER_END, self.POWER_GAIN)


class Inflame(Card):
    """燃烧：1c，获得 2 层力量。"""

    POWER_GAIN: int = 2

    def __init__(self) -> None:
        super().__init__(
            name="燃烧",
            cost=1,
            card_type=Card.TYPE_POWER,
            description=f"获得 {self.POWER_GAIN} 层力量。",
        )
        self.rarity = CardRarity.UNCOMMON

    def play(self, user, target=None, battle=None, x_value=0):
        CardEffects.add_buff(user, BuffSystem.BUFF_POWER, self.POWER_GAIN)


class Footwork(Card):
    """步伐：1c，获得 3 层敏捷。"""

    DEX_GAIN: int = 3

    def __init__(self) -> None:
        super().__init__(
            name="步伐",
            cost=1,
            card_type=Card.TYPE_POWER,
            description=f"获得 {self.DEX_GAIN} 层敏捷。",
        )
        self.rarity = CardRarity.UNCOMMON

    def play(self, user, target=None, battle=None, x_value=0):
        CardEffects.add_buff(user, BuffSystem.BUFF_DEXTERITY, self.DEX_GAIN)


class Berserk(Card):
    """狂暴：0c，获得 2 层力量 + 1 层易伤，回合结束时获得 1 层力量。"""

    POWER_GAIN: int = 2
    POWER_PER_TURN: int = 1

    def __init__(self) -> None:
        super().__init__(
            name="狂暴",
            cost=0,
            card_type=Card.TYPE_POWER,
            description=f"获得 {self.POWER_GAIN} 层力量和 1 层易伤。每回合结束时获得 {self.POWER_PER_TURN} 层力量。",
        )
        self.rarity = CardRarity.RARE

    def play(self, user, target=None, battle=None, x_value=0):
        CardEffects.add_buff(user, BuffSystem.BUFF_POWER, self.POWER_GAIN)
        CardEffects.add_buff(user, BuffSystem.BUFF_VULNERABLE, 1)
        CardEffects.add_buff(user, BuffSystem.BUFF_GAIN_POWER_END, self.POWER_PER_TURN)


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
        self.rarity = CardRarity.COMMON

    def play(self, user, target=None, battle=None, x_value=0):
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
        self.rarity = CardRarity.COMMON

    def play(self, user, target=None, battle=None, x_value=0):
        logger.info("[Dazed] 晕眩被自动打出，无效果")


class Burn(Card):
    """灼伤：状态牌，不能被打出，回合结束时若在手牌中自动打出造成 3 点伤害。"""

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
        self.rarity = CardRarity.COMMON

    def play(self, user, target=None, battle=None, x_value=0):
        CardEffects.lose_hp(user, self.DAMAGE)


# ====================================================================== #
# X费牌
# ====================================================================== #
class Whirlwind(Card):
    """倾斜：X费，依次打出抽牌堆顶部的前 X 张牌。"""

    def __init__(self) -> None:
        super().__init__(
            name="倾斜",
            cost=0,
            card_type=Card.TYPE_SKILL,
            description="依次打出抽牌堆顶部的前 X 张牌（X 为本牌消耗的能量数）。",
            is_x_cost=True,
        )
        self.rarity = CardRarity.RARE

    def play(self, user, target=None, battle=None, x_value=0):
        assert battle is not None, "[Whirlwind] 需要 battle 引用"
        logger.info("[Whirlwind] 倾斜打出，x_value=%d", x_value)
        if x_value <= 0:
            logger.info("[Whirlwind] x_value=0，空效果")
            return
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
        self.rarity = CardRarity.UNCOMMON

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
        self.rarity = CardRarity.RARE

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
        self.rarity = CardRarity.UNCOMMON

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


# ====================================================================== #
# 按稀有度分组的卡牌池（供奖励/商店使用）
# ====================================================================== #
COMMON_CARDS = [Strike, Defend, IronWave, PommelStrike]
UNCOMMON_CARDS = [Bash, Survivor, Hologram, DarkShackles, ShrugItOff, FlameBarrier, Inflame, Footwork]
RARE_CARDS = [Offering, MachineLearning, Whirlwind, Domination, Impervious, DemonForm, Berserk]
ALL_REWARD_CARDS = COMMON_CARDS + UNCOMMON_CARDS + RARE_CARDS
