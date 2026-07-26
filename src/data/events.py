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
# 事件 3: 变牌
# ====================================================================== #
class TransformCardEvent(GameEvent):
    """变牌事件。

    描述: 一个神秘的炼金术士向你展示了他的变形术，
          可以把一张牌随机变成另一张牌。
    选项:
    - [变牌] 选择一张牌，随机变成另一张牌
    - [离开] 不变化任何牌
    """

    def __init__(self) -> None:
        super().__init__(
            name="炼金术士",
            description="一位戴着高帽的炼金术士从炼金釜中抬起头，"
                        "眼中闪烁着疯狂的光芒：'你的牌太普通了！让我帮你用炼金术转化它！'",
        )
        self.options = [
            EventOption(
                text="变牌（选择一张牌，随机变成另一张牌）",
                callback=self._transform_card,
                tooltip="选择一张牌，随机变成另一张牌",
            ),
            EventOption(
                text="离开（不变化任何牌）",
                callback=self._leave,
                tooltip="安全离开",
            ),
        ]

    def _transform_card(self, game: "GameController") -> None:
        """选择一张牌随机变成另一张牌。

        使用 pending_delete_card 机制让玩家选择要变的牌，
        然后在回调中替换为新牌。
        """
        import random
        from src.data.cards import ALL_REWARD_CARDS

        cards = list(game.player.deck_pile)
        if not cards:
            game.message = "你的牌组是空的，没有牌可以变。"
            logger.info("[变牌事件] 牌组为空")
            return

        game.pending_delete_card = True
        game.message = "选择一张要变形的牌（点击卡牌确认）"
        # 保存替换回调 - 在 confirm_event_card_action 中处理
        # 这里我们需要扩展删除逻辑以支持变牌
        def transform_callback(card_index):
            import random
            from src.data.cards import ALL_REWARD_CARDS
            if card_index >= 0 and card_index < len(game.player.deck_pile):
                old_card = game.player.deck_pile.pop(card_index)
                new_card_cls = random.choice(ALL_REWARD_CARDS)
                new_card = new_card_cls()
                game.player.deck_pile.append(new_card)
                game.message = f"{old_card.name} 变成了 {new_card.name}！"
                logger.info("[变牌事件] %s → %s", old_card.name, new_card.name)
            else:
                game.message = "你谢绝了炼金术士的提议，继续前行。"

        game._event_transform_callback = transform_callback
        logger.info("[变牌事件] 等待玩家选择要变的牌，牌组共 %d 张", len(cards))

    def _leave(self, game: "GameController") -> None:
        """安全离开。"""
        game.message = "你婉拒了炼金术士，继续前行。"
        logger.info("[变牌事件] 玩家选择离开")


# ====================================================================== #
# 事件 4: 血换金币
# ====================================================================== #
class BloodGoldEvent(GameEvent):
    """血换金币事件。

    描述: 一个阴暗的祭坛，上面刻着古老的符文。
          将你的鲜血滴在祭坛上，它会回馈你金币。
    选项:
    - [献祭] 失去 12% 最大 HP，获得 50~80 金币
    - [离开] 不献祭，安全离开
    """

    HP_COST_PCT: float = 0.12

    def __init__(self) -> None:
        super().__init__(
            name="血之祭坛",
            description="一个由黑色石头砌成的祭坛出现在你面前，"
                        "祭坛中央的石碗里还残留着暗红色的血迹。"
                        "一个低沉的声音在你耳边低语：'献上你的鲜血，获取财富。'",
        )
        self.options = [
            EventOption(
                text=f"献祭（失去 {int(self.HP_COST_PCT * 100)}% 生命，获得 50~80 金币）",
                callback=self._sacrifice,
                tooltip="失去生命换取金币",
            ),
            EventOption(
                text="离开（不献祭，安全离开）",
                callback=self._leave,
                tooltip="安全离开",
            ),
        ]

    def _sacrifice(self, game: "GameController") -> None:
        """失去生命，获得金币。"""
        import random

        hp_loss = int(game.player.max_hp * self.HP_COST_PCT)
        actual_loss = min(hp_loss, game.player.current_hp - 1)  # 至少留 1 HP
        if actual_loss <= 0:
            game.message = "你太虚弱了，无法承受献祭。"
            logger.info("[血之祭坛] 玩家 HP 不足，无法献祭")
            return

        game.player.current_hp -= actual_loss
        gold_gain = random.randint(50, 80)
        game.gold += gold_gain
        game.message = f"你献祭了 {actual_loss} 点生命，获得了 {gold_gain} 金币！"
        logger.info("[血之祭坛] 失去 %d HP，获得 %d 金币", actual_loss, gold_gain)

    def _leave(self, game: "GameController") -> None:
        """安全离开。"""
        game.message = "你无视了祭坛的低语，继续前行。"
        logger.info("[血之祭坛] 玩家选择离开")


# ====================================================================== #
# 事件 5: 诅咒之书
# ====================================================================== #
class CursedTomeEvent(GameEvent):
    """诅咒之书事件。

    描述: 一本被锁链缠绕的古书静静躺在石台上。
          阅读它会带来力量，但需要付出生命的代价。
    选项:
    - [阅读] 失去 20% 最大 HP，获得一张稀有牌
    - [离开] 不阅读，安全离开
    """

    HP_COST_PCT: float = 0.20

    def __init__(self) -> None:
        super().__init__(
            name="诅咒之书",
            description="一本厚重的古书被锈迹斑斑的铁链锁在石台上，"
                        "书页之间渗出微弱的紫色光芒。"
                        "你感到一股强烈的冲动，想要翻开它…",
        )
        self.options = [
            EventOption(
                text=f"阅读（失去 {int(self.HP_COST_PCT * 100)}% 生命，获得一张稀有牌）",
                callback=self._read,
                tooltip="失去生命，获得稀有卡牌",
            ),
            EventOption(
                text="离开（不阅读，安全离开）",
                callback=self._leave,
                tooltip="安全离开",
            ),
        ]

    def _read(self, game: "GameController") -> None:
        """失去生命，获得稀有牌。"""
        import random
        from src.data.cards import RARE_CARDS

        hp_loss = int(game.player.max_hp * self.HP_COST_PCT)
        actual_loss = min(hp_loss, game.player.current_hp - 1)  # 至少留 1 HP
        if actual_loss <= 0:
            game.message = "你太虚弱了，无法承受诅咒的力量。"
            logger.info("[诅咒之书] 玩家 HP 不足，无法阅读")
            return

        game.player.current_hp -= actual_loss
        new_card_cls = random.choice(RARE_CARDS)
        new_card = new_card_cls()
        game.player.deck_pile.append(new_card)
        game.message = f"你翻开古书，受到了魔法的诅咒（-{actual_loss} HP），但获得了 {new_card.name}！"
        logger.info("[诅咒之书] 失去 %d HP，获得 %s", actual_loss, new_card.name)

    def _leave(self, game: "GameController") -> None:
        """安全离开。"""
        game.message = "你压下了好奇心，从古书旁走过。"
        logger.info("[诅咒之书] 玩家选择离开")


# ====================================================================== #
# 事件池
# ====================================================================== #
EVENT_POOL = [DeleteCardEvent, UpgradeCardEvent, TransformCardEvent, BloodGoldEvent, CursedTomeEvent]
