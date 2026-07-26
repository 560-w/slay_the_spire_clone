"""intent.py: Intent 类（敌人意图）。

封装敌人本回合打算进行的动作。一个敌人单回合可能有多个意图（也可能没有）。
意图类型:
- ATTACK:    对玩家造成伤害（数值经 buff 修正，展示最终值）
- DEFEND:    敌人获得护甲
- BUFF:      敌人给自己增益
- DEBUFF:    给玩家施加 debuff
- ADD_CARD:  向玩家牌堆塞入状态牌

设计原则:
1. Intent 自带 execute() 自结算，但 buff 修正委托 BuffSystem，保持职责分离。
2. 攻击意图数值展示须为经 buff 修正后的最终值，由 get_display_text() 提供。
3. 敌人 take_turn() 按意图列表顺序依次执行。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from .card import Card

# 仅用于类型提示，避免运行时循环导入
if TYPE_CHECKING:
    from .buff_system import BuffSystem
    from .enemy import Enemy
    from .player import Player
    from ..controllers.battle import BattleController

logger = logging.getLogger(__name__)


class Intent:
    """敌人意图。

    属性:
        intent_type (str): 意图类型，取值见类常量。
        base_value (int): 基础数值（攻击伤害/护甲/buff 层数），>=0。
        buff_name (Optional[str]): BUFF/DEBUFF 时的 buff 名称。
        status_card (Optional[Card]): ADD_CARD 时塞入玩家牌堆的卡牌。

    类常量:
        TYPE_ATTACK / TYPE_DEFEND / TYPE_BUFF / TYPE_DEBUFF / TYPE_ADD_CARD
    """

    # 意图类型常量
    TYPE_ATTACK: str = "Attack"
    TYPE_DEFEND: str = "Defend"
    TYPE_BUFF: str = "Buff"
    TYPE_DEBUFF: str = "Debuff"
    TYPE_ADD_CARD: str = "AddCard"

    def __init__(
        self,
        intent_type: str,
        base_value: int = 0,
        buff_name: Optional[str] = None,
        status_card: Optional[Card] = None,
    ) -> None:
        """初始化意图。

        Args:
            intent_type: 意图类型，应为 TYPE_* 常量之一。
            base_value: 基础数值，必须 >= 0。
            buff_name: BUFF/DEBUFF 时必填，其余类型忽略。
            status_card: ADD_CARD 时必填，其余类型忽略。

        Raises:
            AssertionError: 当类型非法、base_value 为负、或必需参数缺失时触发。
        """
        valid_types = {
            self.TYPE_ATTACK, self.TYPE_DEFEND, self.TYPE_BUFF,
            self.TYPE_DEBUFF, self.TYPE_ADD_CARD,
        }
        assert intent_type in valid_types, (
            f"[Intent] 意图类型必须为 {valid_types} 之一，收到 {intent_type}"
        )
        assert base_value >= 0, f"[Intent] base_value 不能为负，收到 {base_value}"

        self.intent_type: str = intent_type
        self.base_value: int = base_value
        # 按类型校验附属参数
        if intent_type in (self.TYPE_BUFF, self.TYPE_DEBUFF):
            assert buff_name, f"[Intent] {intent_type} 意图必须提供 buff_name"
        if intent_type == self.TYPE_ADD_CARD:
            assert status_card is not None, "[Intent] ADD_CARD 意图必须提供 status_card"

        self.buff_name: Optional[str] = buff_name
        self.status_card: Optional[Card] = status_card

        logger.debug(
            "[Intent] 创建意图: %s (base=%d, buff=%s, card=%s)",
            intent_type, base_value, buff_name,
            status_card.name if status_card else None,
        )

    # ------------------------------------------------------------------ #
    # 展示
    # ------------------------------------------------------------------ #
    def get_display_text(self, enemy: "Enemy", buff_system: "BuffSystem") -> str:
        """获取给玩家展示的意图文字。

        攻击意图: 显示经 buff 修正后的最终伤害值（如 "攻击 8"）。
        其余意图: 只显示类型名（如 "防御"、"强化"、"削弱"）。

        Args:
            enemy: 持有该意图的敌人（用于查其 buff 计算最终伤害）。
            buff_system: buff 结算系统。

        Returns:
            展示文字字符串。
        """
        if self.intent_type == self.TYPE_ATTACK:
            # 攻击意图：经 buff 修正后的最终数值
            final_damage: int = buff_system.compute_outgoing_damage(
                attacker=enemy, base_damage=self.base_value
            )
            return f"攻击 {final_damage}"
        if self.intent_type == self.TYPE_DEFEND:
            return "防御"
        if self.intent_type == self.TYPE_BUFF:
            return "强化"
        if self.intent_type == self.TYPE_DEBUFF:
            return "削弱"
        # ADD_CARD
        return "塞牌"

    # ------------------------------------------------------------------ #
    # 执行
    # ------------------------------------------------------------------ #
    def execute(
        self,
        enemy: "Enemy",
        player: "Player",
        battle: "BattleController",
    ) -> None:
        """执行本意图的结算。

        Args:
            enemy: 执行意图的敌人。
            player: 玩家对象（受击/debuff/塞牌目标）。
            battle: 战斗控制器（用于 ADD_CARD 调用塞牌接口）。
        """
        logger.info(
            "[Intent] %s 执行意图: %s (base=%d)",
            enemy.name, self.intent_type, self.base_value,
        )

        if self.intent_type == self.TYPE_ATTACK:
            # 攻击：经 buff 修正后对玩家造成伤害
            final_damage: int = battle.buff_system.compute_outgoing_damage(
                attacker=enemy, base_damage=self.base_value
            )
            # 易伤由 take_damage 前的 incoming 修正处理
            incoming: int = battle.buff_system.compute_incoming_damage(
                target=player, damage=final_damage
            )
            player.take_damage(incoming)

        elif self.intent_type == self.TYPE_DEFEND:
            # 防御：敌人获得护甲
            enemy.gain_block(self.base_value)

        elif self.intent_type == self.TYPE_BUFF:
            # 强化：敌人给自己增益 buff
            assert self.buff_name is not None
            enemy.add_buff(self.buff_name, self.base_value)

        elif self.intent_type == self.TYPE_DEBUFF:
            # 削弱：给玩家施加 debuff
            assert self.buff_name is not None
            player.add_buff(self.buff_name, self.base_value)

        elif self.intent_type == self.TYPE_ADD_CARD:
            # 塞牌：向玩家牌堆加入状态牌
            assert self.status_card is not None
            battle.add_status_card_to_player(self.status_card)

    # ------------------------------------------------------------------ #
    # 魔术方法
    # ------------------------------------------------------------------ #
    def __str__(self) -> str:
        """简略字符串（不含 buff 修正，仅基础信息）。"""
        if self.intent_type == self.TYPE_ATTACK:
            return f"攻击({self.base_value})"
        if self.intent_type == self.TYPE_DEFEND:
            return f"防御({self.base_value})"
        if self.intent_type in (self.TYPE_BUFF, self.TYPE_DEBUFF):
            return f"{self.intent_type}({self.buff_name}×{self.base_value})"
        return f"塞牌({self.status_card.name if self.status_card else '?'})"