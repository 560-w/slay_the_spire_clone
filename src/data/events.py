"""events.py: 具体事件实现。

当前包含 2 个事件，每个事件 2 个选项：
1. 删除事件 (DeleteCardEvent): 删除牌组中一张牌 / 离开
2. 升级事件 (UpgradeCardEvent): 升级牌组中一张牌 / 离开
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.core.event import EventOption, GameEvent

if TYPE_CHECKING:
    from src.controllers.game import GameController

logger = logging.getLogger(__name__)


# ====================================================================== #
# 事件 1: 删除牌
# ====================================================================== #
class DeleteCardEvent(GameEvent):
    """删除卡牌事件。

    描述: 你遇到一个神秘的铁匠，他说可以帮你熔炼一张不再需要的牌。
    选项:
    - [删除一张牌] 从牌组中选择一张牌永久删除
    - [离开] 不删除任何牌
    """

    def __init__(self) -> None:
        super().__init__(
            name="神秘铁匠",
            description="一位戴着铁面具的铁匠在火炉旁忙碌着，"
                        "他抬起头说：'你的牌组中有些累赘，我可以帮你熔炼掉一张。'",
        )
        self.options = [
            EventOption(
                text="删除一张牌（从牌组中永久移除一张牌）",
                callback=self._delete_card,
                tooltip="选择并删除牌组中的一张牌",
            ),
            EventOption(
                text="离开（不删除任何牌）",
                callback=self._leave,
                tooltip="安全离开",
            ),
        ]

    def _delete_card(self, game: "GameController") -> None:
        """删除一张牌。

        注意: 由于事件系统需要交互式选择卡牌，这里通过游戏控制器
        设置 pending_action 来让 View 层渲染卡牌选择界面。
        实际删除操作由 GameController 在收到选择结果后完成。
        """
        cards = list(game.player.deck_pile)
        if not cards:
            game.message = "你的牌组是空的，没有牌可以删除。"
            logger.info("[删除事件] 牌组为空，无法删除")
            return

        # 设置待删除状态，由 View 渲染卡牌选择界面
        game.pending_delete_card = True
        game.message = "选择一张要删除的牌（点击卡牌确认）"
        logger.info("[删除事件] 等待玩家选择要删除的牌，牌组共 %d 张", len(cards))

    def _leave(self, game: "GameController") -> None:
        """安全离开。"""
        game.message = "你谢绝了铁匠的提议，继续前行。"
        logger.info("[删除事件] 玩家选择离开")


# ====================================================================== #
# 事件 2: 升级牌
# ====================================================================== #
class UpgradeCardEvent(GameEvent):
    """升级卡牌事件。

    描述: 你发现一面古老的魔法镜，它能映照出卡牌的本质并强化它。
    选项:
    - [升级一张牌] 从牌组中选择一张牌升级
    - [离开] 不升级任何牌
    """

    def __init__(self) -> None:
        super().__init__(
            name="魔法镜",
            description="一面古老的银镜立在墙边，镜面如水波般荡漾。"
                        "一个声音在你心中响起：'看向镜中的自己，你最强的力量将被唤醒。'",
        )
        self.options = [
            EventOption(
                text="升级一张牌（从牌组中选择一张牌升级）",
                callback=self._upgrade_card,
                tooltip="选择并升级牌组中的一张牌",
            ),
            EventOption(
                text="离开（不升级任何牌）",
                callback=self._leave,
                tooltip="安全离开",
            ),
        ]

    def _upgrade_card(self, game: "GameController") -> None:
        """升级一张牌。

        设置 pending_upgrade_card 让 View 渲染卡牌选择界面。
        实际升级由 GameController 在收到选择结果后完成。
        """
        cards = list(game.player.deck_pile)
        if not cards:
            game.message = "你的牌组是空的，没有牌可以升级。"
            logger.info("[升级事件] 牌组为空，无法升级")
            return

        upgradable = [c for c in cards if not c.upgraded]
        if not upgradable:
            game.message = "你的所有卡牌都已升级过了。"
            logger.info("[升级事件] 所有卡牌已升级")
            return

        game.pending_upgrade_card = True
        game.message = "选择一张要升级的牌（点击卡牌确认）"
        logger.info(
            "[升级事件] 等待玩家选择要升级的牌，可升级 %d/%d 张",
            len(upgradable), len(cards),
        )

    def _leave(self, game: "GameController") -> None:
        """安全离开。"""
        game.message = "你离开了镜子，继续前行。"
        logger.info("[升级事件] 玩家选择离开")


# ====================================================================== #
# 事件池
# ====================================================================== #
EVENT_POOL = [DeleteCardEvent, UpgradeCardEvent]