"""relics.py: 具体遗物实现。

当前包含:
- 金刚杵 (Vajra): 战斗开始时获得 1 力量
- 赌徒筹码 (Gambler's Chip): 第1回合可选弃任意数量手牌，抽等量牌
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.core.relic import Relic, RelicRarity

if TYPE_CHECKING:
    from src.core.player import Player
    from src.controllers.battle import BattleController

logger = logging.getLogger(__name__)


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

        # 设置 pending_action：玩家可从手牌中选择任意数量弃置
        # 使用闭包捕获 player 和 battle 引用，在回调中直接操作
        from src.core.pending_action import PendingCardSelection

        def _on_discard_done(selected_cards: list) -> None:
            """玩家选择完成后：弃置选中牌，抽等量牌。"""
            discard_count = len(selected_cards)
            if discard_count == 0:
                logger.info("[赌徒筹码] 玩家选择不弃牌")
                return

            # 弃置选中的牌
            for card in selected_cards:
                if card in player.hand:
                    player.discard_card(card)

            # 抽等量牌
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
            count=hand_count,  # 最多弃全部手牌
            action="custom",
            cards=list(player.hand),
            callback=_on_discard_done,
        )

        logger.info(
            "[赌徒筹码] 第1回合，等待玩家选择弃牌（手牌共 %d 张）",
            hand_count,
        )