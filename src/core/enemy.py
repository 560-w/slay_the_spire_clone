"""enemy.py: Enemy 类。

继承自 Entity，作为敌人的基础结构。
Phase 2 重构:
- 用 Intent 对象列表替代字符串意图（一回合可含多个或零个意图）
- choose_intents() 由具体敌人在 data/enemies.py 实现，设置本回合意图列表
- take_turn() 按意图列表顺序依次执行
- get_display_summary() 返回展示文字列表（攻击意图显示经 buff 修正的最终数值）

设计原则:
1. 意图逻辑与 Entity 数值管理分离，Intent 自带 execute 自结算。
2. buff 修正委托 BuffSystem，Enemy 仅提供查询接口。
3. 意图模式由子类/数据定义，本类只提供流程框架。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List

from .entity import Entity
from .intent import Intent

if TYPE_CHECKING:
    from .buff_system import BuffSystem
    from .player import Player
    from ..controllers.battle import BattleController

logger = logging.getLogger(__name__)


class Enemy(Entity):
    """敌人基类，继承自 Entity。

    属性:
        enemy_id (str): 敌人类型标识，便于数据驱动加载。
        is_elite (bool): 是否为精英怪（影响掉落，未来扩展）。
        current_intents (List[Intent]): 本回合意图列表（可能为空）。
        intent_pattern (List[List[Intent]]): 意图模式（多回合循环），由子类设置。
        intent_index (int): 意图模式当前索引。
    """

    def __init__(
        self,
        name: str,
        max_hp: int,
        enemy_id: str = "",
        is_elite: bool = False,
    ) -> None:
        """初始化敌人。

        Args:
            name: 敌人名称。
            max_hp: 最大生命值，必须为正整数。
            enemy_id: 敌人类型标识（用于数据驱动），默认空字符串。
            is_elite: 是否精英怪，默认 False。

        Raises:
            AssertionError: 当 max_hp 非正时触发（继承自 Entity）。
        """
        super().__init__(name=name, max_hp=max_hp)

        self.enemy_id: str = enemy_id or name
        self.is_elite: bool = is_elite
        self.current_intents: List[Intent] = []
        # 意图模式：每个元素是一回合的意图列表，按索引循环
        self.intent_pattern: List[List[Intent]] = []
        self.intent_index: int = 0

        logger.debug(
            "[Enemy] 创建敌人 %s (id=%s, max_hp=%d, elite=%s)",
            self.name, self.enemy_id, self.max_hp, self.is_elite,
        )

    # ------------------------------------------------------------------ #
    # 意图管理
    # ------------------------------------------------------------------ #
    def choose_intents(self) -> None:
        """选择本回合意图（按意图模式循环）。

        从 intent_pattern 按当前索引取一回合的意图列表，
        索引循环递增。具体敌人的 intent_pattern 由子类在 data/enemies.py 设置。
        若无意图模式，则本回合无意图（空列表）。
        """
        if not self.intent_pattern:
            logger.debug("[Enemy] %s 无意图模式，本回合无意图", self.name)
            self.current_intents = []
            return

        # 按索引取本回合意图（深拷贝避免共享对象）
        self.current_intents = list(self.intent_pattern[self.intent_index])
        self.intent_index = (self.intent_index + 1) % len(self.intent_pattern)
        logger.info(
            "[Enemy] %s 选择本回合意图: %s",
            self.name, [str(i) for i in self.current_intents],
        )

    def get_display_summary(self, buff_system: "BuffSystem") -> List[str]:
        """获取给玩家展示的意图文字列表。

        攻击意图: 显示经 buff 修正后的最终伤害值（如 "攻击 8"）。
        其余意图: 只显示类型名（如 "防御"、"强化"、"削弱"）。

        Args:
            buff_system: buff 结算系统（用于计算攻击最终伤害）。

        Returns:
            展示文字列表，每个元素对应一个意图。
        """
        return [intent.get_display_text(self, buff_system) for intent in self.current_intents]

    # ------------------------------------------------------------------ #
    # 回合执行
    # ------------------------------------------------------------------ #
    def take_turn(self, player: "Player", battle: "BattleController") -> None:
        """执行本回合所有意图。

        按 current_intents 顺序依次执行。每个意图由 Intent.execute 自结算。
        若中途死亡，剩余意图不再执行。

        Args:
            player: 玩家对象（攻击/debuff 目标）。
            battle: 战斗控制器（ADD_CARD 等需调用其接口）。
        """
        logger.info(
            "[Enemy] %s 执行回合: 意图数=%d",
            self.name, len(self.current_intents),
        )
        for intent in self.current_intents:
            # 敌人若死亡则停止（虽然敌人不会攻击自己，但预留安全检查）
            if not self.is_alive():
                logger.debug("[Enemy] %s 已死亡，停止执行剩余意图", self.name)
                break
            intent.execute(enemy=self, player=player, battle=battle)
        # 执行完毕清空本回合意图
        self.current_intents = []

    # ------------------------------------------------------------------ #
    # 魔术方法
    # ------------------------------------------------------------------ #
    def __str__(self) -> str:
        """可读的敌人状态字符串。"""
        base = super().__str__()
        intent_str = ", ".join(str(i) for i in self.current_intents) or "无"
        elite_tag = " [精英]" if self.is_elite else ""
        return f"{base}{elite_tag} | 意图:{intent_str}"