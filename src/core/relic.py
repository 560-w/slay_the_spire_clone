"""relic.py: 遗物系统基类。

设计原则:
1. Relic 基类提供生命周期钩子，具体遗物按需覆写。
2. 与战斗状态机解耦：遗物只接收 player/battle 引用，通过其公开接口操作。
3. 遗物跨战斗持久存在（保存在 Player.relics），战斗开始/回合开始等时点触发钩子。
4. 钩子默认空实现，子类按需覆写，避免空方法泛滥。

钩子时点（由 BattleController 调用）:
- on_combat_start: 战斗开始时（玩家抽牌前/后皆可，具体遗物自行决定）
- on_turn_start: 每个玩家回合开始时
- on_turn_end: 每个玩家回合结束时
- on_combat_end: 战斗结束时（胜利时）
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.player import Player
    from src.controllers.battle import BattleController

logger = logging.getLogger(__name__)


class RelicRarity(Enum):
    """遗物稀有度枚举。"""
    COMMON = "普通"
    UNCOMMON = "罕见"
    RARE = "稀有"
    BOSS = "Boss"


class Relic:
    """遗物抽象基类。

    属性:
        name (str): 遗物名称。
        description (str): 遗物效果描述。
        rarity (RelicRarity): 稀有度。

    钩子（子类按需覆写）:
        on_combat_start(player, battle): 战斗开始时触发
        on_turn_start(player, battle): 玩家回合开始时触发
        on_turn_end(player, battle): 玩家回合结束时触发
        on_combat_end(player, battle): 战斗结束时触发
    """

    def __init__(
        self,
        name: str,
        description: str,
        rarity: RelicRarity = RelicRarity.COMMON,
    ) -> None:
        """初始化遗物。

        Args:
            name: 遗物名称，不能为空。
            description: 效果描述，不能为空。
            rarity: 稀有度，默认普通。

        Raises:
            AssertionError: 当 name 或 description 为空时触发。
        """
        assert isinstance(name, str) and name, "[Relic] name 不能为空"
        assert isinstance(description, str) and description, "[Relic] description 不能为空"
        assert isinstance(rarity, RelicRarity), "[Relic] rarity 必须为 RelicRarity 枚举"

        self.name: str = name
        self.description: str = description
        self.rarity: RelicRarity = rarity

        logger.debug("[Relic] 创建遗物: %s (%s)", self.name, self.rarity.value)

    # ------------------------------------------------------------------ #
    # 生命周期钩子（默认空实现，子类按需覆写）
    # ------------------------------------------------------------------ #
    def on_combat_start(self, player: "Player", battle: "BattleController") -> None:
        """战斗开始时触发。"""
        pass

    def on_turn_start(self, player: "Player", battle: "BattleController") -> None:
        """玩家回合开始时触发。"""
        pass

    def on_turn_end(self, player: "Player", battle: "BattleController") -> None:
        """玩家回合结束时触发。"""
        pass

    def on_combat_end(self, player: "Player", battle: "BattleController") -> None:
        """战斗结束时触发（胜利时）。"""
        pass

    # ------------------------------------------------------------------ #
    # 魔术方法
    # ------------------------------------------------------------------ #
    def __repr__(self) -> str:
        """便于打印调试。"""
        return f"<Relic {self.name} [{self.rarity.value}]>"

    def __str__(self) -> str:
        """可读字符串。"""
        return f"{self.name}（{self.rarity.value}）：{self.description}"