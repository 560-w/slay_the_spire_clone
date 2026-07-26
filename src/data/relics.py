"""relics.py: 具体遗物实现。

当前包含:
- 金刚杵 (Vajra): 战斗开始时获得 1 力量
- 赌徒筹码 (Gambler's Chip): 第1回合可选弃任意数量手牌，抽等量牌
- 古茶具 (Ancient Tea Set): 第1回合开始时获得 2 能量
- 皇家枕头 (Royal Pillow): 篝火休息额外回复 15% 最大 HP
- 微笑面具 (Smiling Mask): 商店删牌费用减半
- 弹珠袋 (Bag of Marbles): 战斗开始时给所有敌人施加 1 层易伤
- 瓶中精灵 (Bottled Flame): 战斗开始时从抽牌堆抽 1 张牌到手牌
- 红石 (Red Stone): 战斗开始时获得 2 力量，所有敌人获得 1 力量
- 捕梦网 (Dream Catcher): 篝火休息时获得 1 张随机卡牌
- 鲜血圣杯 (BloodChalice): 战斗胜利后额外回复 10% 最大 HP
- 黑暗之球 (Dark Orb): 每回合开始获得 1 能量，宝箱房不再给遗物（Boss）
- 融合之锤 (Fusion Hammer): 获得 1 能量，不能再篝火升级（Boss）
- 诅咒钥匙 (Cursed Key): 每回合开始获得 1 能量，宝箱房金币减半（Boss）
"""

from __future__ import annotations

import logging
import random
from typing import TYPE_CHECKING

from src.core.relic import Relic, RelicRarity

if TYPE_CHECKING:
    from src.core.player import Player
    from src.controllers.battle import BattleController

logger = logging.getLogger(__name__)


# ====================================================================== #
# 普通遗物
# ====================================================================== #

class Vajra(Relic):
    """金刚杵（普通遗物）

    效果: 战斗开始时，获得 1 点力量。
    """

    def __init__(self) -> None:
        super().__init__(
            name="金刚杵",
            description="战斗开始时获得 1 点力量。",
            rarity=RelicRarity.COMMON,
        )

    def on_combat_start(self, player: "Player", battle: "BattleController") -> None:
        """战斗开始时: 获得 1 点力量。"""
        player.buffs["力量"] = player.buffs.get("力量", 0) + 1
        logger.info("[金刚杵] %s 获得 1 点力量", player.name)


class AncientTeaSet(Relic):
    """古茶具（普通遗物）

    效果: 每场战斗的第 1 回合开始时，获得 2 点能量。
    """

    def __init__(self) -> None:
        super().__init__(
            name="古茶具",
            description="第1回合开始时获得 2 点能量。",
            rarity=RelicRarity.COMMON,
        )

    def on_turn_start(self, player: "Player", battle: "BattleController") -> None:
        """仅第 1 回合: 获得 2 点能量。"""
        if battle.turn_number != 1:
            return
        player.current_energy += 2
        logger.info("[古茶具] %s 第1回合获得 2 点能量", player.name)


class RoyalPillow(Relic):
    """皇家枕头（普通遗物）

    效果: 篝火休息时额外回复 15% 最大 HP。
    此效果由 GameController.campfire_rest 检查并应用。
    """

    def __init__(self) -> None:
        super().__init__(
            name="皇家枕头",
            description="篝火休息额外回复 15% 最大 HP。",
            rarity=RelicRarity.COMMON,
        )


class SmilingMask(Relic):
    """微笑面具（普通遗物）

    效果: 商店删牌费用减半（向下取整）。
    此效果由 GameController 进入商店时检查并应用。
    """

    def __init__(self) -> None:
        super().__init__(
            name="微笑面具",
            description="商店删牌费用减半。",
            rarity=RelicRarity.COMMON,
        )


class BloodChalice(Relic):
    """鲜血圣杯（普通遗物）

    效果: 战斗胜利后，额外回复 10% 最大生命值。
    此效果由 GameController.on_battle_end 检查并应用。
    """

    def __init__(self) -> None:
        super().__init__(
            name="鲜血圣杯",
            description="战斗胜利后额外回复 10% 最大 HP。",
            rarity=RelicRarity.COMMON,
        )

    def on_combat_end(self, player: "Player", battle: "BattleController") -> None:
        """战斗胜利后: 额外回复 10% 最大 HP。"""
        heal_amount = int(player.max_hp * 0.1)
        actual = player.heal(heal_amount)
        if actual > 0:
            logger.info("[鲜血圣杯] %s 战后额外回复 %d HP", player.name, actual)


# ====================================================================== #
# 罕见遗物
# ====================================================================== #

class BagOfMarbles(Relic):
    """弹珠袋（罕见遗物）

    效果: 战斗开始时，给所有敌人施加 1 层易伤。
    """

    def __init__(self) -> None:
        super().__init__(
            name="弹珠袋",
            description="战斗开始时给所有敌人施加 1 层易伤。",
            rarity=RelicRarity.UNCOMMON,
        )

    def on_combat_start(self, player: "Player", battle: "BattleController") -> None:
        """战斗开始时: 给所有敌人施加 1 层易伤。"""
        for enemy in battle.enemies:
            if enemy.is_alive():
                enemy.add_buff("易伤", 1)
        logger.info("[弹珠袋] 所有敌人获得 1 层易伤")


class BottledFlame(Relic):
    """瓶中精灵（罕见遗物）

    效果: 战斗开始时，从抽牌堆随机抽 1 张牌到手牌。
    """

    def __init__(self) -> None:
        super().__init__(
            name="瓶中精灵",
            description="战斗开始时从抽牌堆抽 1 张牌到手牌。",
            rarity=RelicRarity.UNCOMMON,
        )

    def on_combat_start(self, player: "Player", battle: "BattleController") -> None:
        """战斗开始时: 从抽牌堆抽 1 张到手牌。"""
        if player.draw_pile:
            card = player.draw_pile.pop()
            player.hand.append(card)
            logger.info("[瓶中精灵] %s 从抽牌堆抽到 %s", player.name, card.name)


class DreamCatcher(Relic):
    """捕梦网（罕见遗物）

    效果: 篝火休息时额外获得 1 张随机卡牌。
    此效果由 GameController.campfire_rest 检查并应用。
    """

    def __init__(self) -> None:
        super().__init__(
            name="捕梦网",
            description="篝火休息时获得 1 张随机卡牌。",
            rarity=RelicRarity.UNCOMMON,
        )


# ====================================================================== #
# 稀有遗物
# ====================================================================== #

class GamblersChip(Relic):
    """赌徒筹码（稀有遗物）

    效果: 每场战斗的第 1 回合开始时，玩家可选择弃置任意数量手牌，
          然后抽等量的牌。
    类似于《杀戮尖塔》中赌徒筹码遗物。
    """

    def __init__(self) -> None:
        super().__init__(
            name="赌徒筹码",
            description="第1回合开始时，可选弃置任意数量手牌，然后抽等量牌。",
            rarity=RelicRarity.RARE,
        )

    def on_turn_start(self, player: "Player", battle: "BattleController") -> None:
        """仅第 1 回合: 设置挂起动作，让玩家选择弃置任意数量手牌。"""
        if battle.turn_number != 1:
            return

        hand_count: int = len(player.hand)
        if hand_count == 0:
            return

        from src.core.pending_action import PendingCardSelection

        def _on_discard_done(selected_cards: list) -> None:
            """玩家选择完成后：弃置选中牌，抽等量牌。"""
            discard_count = len(selected_cards)
            if discard_count == 0:
                logger.info("[赌徒筹码] 玩家选择不弃牌")
                return

            for card in selected_cards:
                if card in player.hand:
                    player.discard_card(card)

            player.draw_cards(discard_count)

            battle._log_segments(
                (f"赌徒筹码：弃置 {discard_count} 张，抽 {discard_count} 张", (255, 200, 50)),
            )
            logger.info(
                "[赌徒筹码] %s 弃置了 %d 张手牌，抽 %d 张",
                player.name, discard_count, discard_count,
            )

        battle.pending_action = PendingCardSelection(
            prompt="赌徒筹码：选择要弃置的手牌（可多选，点击空白处确认）",
            count=hand_count,
            action="custom",
            cards=list(player.hand),
            callback=_on_discard_done,
        )

        logger.info(
            "[赌徒筹码] 第1回合，等待玩家选择弃牌（手牌共 %d 张）",
            hand_count,
        )


class RedStone(Relic):
    """红石（稀有遗物）

    效果: 战斗开始时获得 2 点力量，但所有敌人也获得 1 点力量。
    """

    def __init__(self) -> None:
        super().__init__(
            name="红石",
            description="战斗开始时获得 2 点力量，所有敌人获得 1 点力量。",
            rarity=RelicRarity.RARE,
        )

    def on_combat_start(self, player: "Player", battle: "BattleController") -> None:
        """战斗开始时: 获得 2 力量，所有敌人获得 1 力量。"""
        player.buffs["力量"] = player.buffs.get("力量", 0) + 2
        for enemy in battle.enemies:
            if enemy.is_alive():
                enemy.add_buff("力量", 1)
        logger.info("[红石] %s 获得 2 力量，所有敌人获得 1 力量", player.name)


# ====================================================================== #
# Boss 遗物
# ====================================================================== #

class DarkOrb(Relic):
    """黑暗之球（Boss 遗物）

    效果: 每回合开始时获得 1 点能量，但宝箱房不再给遗物（仅给金币）。
    副作用由 GameController._enter_treasure 检查。
    """

    def __init__(self) -> None:
        super().__init__(
            name="黑暗之球",
            description="每回合开始时获得 1 能量。宝箱房不再给遗物。",
            rarity=RelicRarity.BOSS,
        )

    def on_turn_start(self, player: "Player", battle: "BattleController") -> None:
        """每回合开始时: 获得 1 点能量。"""
        player.current_energy += 1
        logger.info("[黑暗之球] %s 获得 1 点能量", player.name)


class FusionHammer(Relic):
    """融合之锤（Boss 遗物）

    效果: 获得 1 点能量，但不能再在篝火升级卡牌。
    副作用由 GameController.campfire_upgrade 检查。
    """

    def __init__(self) -> None:
        super().__init__(
            name="融合之锤",
            description="获得 1 能量。不能再在篝火升级卡牌。",
            rarity=RelicRarity.BOSS,
        )

    def on_turn_start(self, player: "Player", battle: "BattleController") -> None:
        """每回合开始时: 获得 1 点能量。"""
        player.current_energy += 1
        logger.info("[融合之锤] %s 获得 1 点能量", player.name)


class CursedKey(Relic):
    """诅咒钥匙（Boss 遗物）

    效果: 每回合开始时获得 1 点能量，但宝箱房金币减半。
    副作用由 GameController._enter_treasure 检查。
    """

    def __init__(self) -> None:
        super().__init__(
            name="诅咒钥匙",
            description="每回合开始时获得 1 能量。宝箱房金币减半。",
            rarity=RelicRarity.BOSS,
        )

    def on_turn_start(self, player: "Player", battle: "BattleController") -> None:
        """每回合开始时: 获得 1 点能量。"""
        player.current_energy += 1
        logger.info("[诅咒钥匙] %s 获得 1 点能量", player.name)


# ====================================================================== #
# 注册表（供 GameController / Shop 等引用）
# ====================================================================== #

# 非 Boss 遗物（用于商店、宝箱房、普通掉落）
NON_BOSS_RELICS = [
    Vajra,
    AncientTeaSet,
    RoyalPillow,
    SmilingMask,
    BloodChalice,
    BagOfMarbles,
    BottledFlame,
    DreamCatcher,
    GamblersChip,
    RedStone,
]

# Boss 遗物（仅 Boss 战斗奖励掉落）
BOSS_RELICS = [
    DarkOrb,
    FusionHammer,
    CursedKey,
]