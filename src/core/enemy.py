"""enemy.py: Enemy 类。

继承自 Entity，作为敌人的基础结构。
Phase 1 仅提供：
- 意图（Intent）占位属性：标识敌人本回合打算进行的动作（攻击/防御/增益等）
- take_turn() 占位方法：未来由 AI 控制器实现具体行为

设计原则：
1. 敌人 AI 逻辑不在本类硬编码，保持扩展性（不同敌人可注入不同策略）。
2. 意图用字符串枚举式常量表示，避免魔法字符串，后续可升级为 Intent 类。
3. 继承 Entity 的全部防御性编程与日志能力。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from .entity import Entity

logger = logging.getLogger(__name__)


class Enemy(Entity):
    """敌人基类，继承自 Entity。

    额外属性:
        intent (Optional[str]): 当前意图，取值见类常量，None 表示无明确意图。
        intent_value (int): 意图关联的数值（如攻击伤害量、格挡量）。
        enemy_id (str): 敌人类型标识，便于数据驱动加载（如 "slime"）。
        is_elite (bool): 是否为精英怪（影响掉落，未来扩展）。
    """

    # 意图类型常量
    INTENT_ATTACK: str = "Attack"        # 攻击
    INTENT_DEFEND: str = "Defend"        # 防御（获得护甲）
    INTENT_BUFF: str = "Buff"            # 自我增益
    INTENT_DEBUFF: str = "Debuff"        # 对玩家减益
    INTENT_UNKNOWN: str = "Unknown"      # 未知/特殊

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
        self.intent: Optional[str] = None
        self.intent_value: int = 0

        logger.debug(
            "[Enemy] 创建敌人 %s (id=%s, max_hp=%d, elite=%s)",
            self.name, self.enemy_id, self.max_hp, self.is_elite,
        )

    # ------------------------------------------------------------------ #
    # 意图管理
    # ------------------------------------------------------------------ #
    def set_intent(self, intent: str, value: int = 0) -> None:
        """设置本回合意图。

        Args:
            intent: 意图类型，应为 INTENT_* 常量之一。
            value: 意图关联数值，必须 >= 0。

        Raises:
            AssertionError: 当 intent 非法或 value 为负时触发。
        """
        valid_intents = {
            self.INTENT_ATTACK, self.INTENT_DEFEND, self.INTENT_BUFF,
            self.INTENT_DEBUFF, self.INTENT_UNKNOWN,
        }
        assert intent in valid_intents, (
            f"[Enemy] 意图必须为 {valid_intents} 之一，收到 {intent}"
        )
        assert value >= 0, f"[Enemy] 意图数值不能为负，收到 {value}"

        self.intent = intent
        self.intent_value = value
        logger.info(
            "[Enemy] %s 设置意图: %s (数值=%d)", self.name, self.intent, self.intent_value
        )

    def clear_intent(self) -> None:
        """清除意图（回合结束后调用）。"""
        logger.debug("[Enemy] %s 清除意图", self.name)
        self.intent = None
        self.intent_value = 0

    # ------------------------------------------------------------------ #
    # AI 钩子（占位）
    # ------------------------------------------------------------------ #
    def take_turn(self, player: Any) -> None:
        """执行本回合行动的占位钩子。

        Phase 1 不实现具体 AI 逻辑。未来由具体的敌人 AI 策略类实现，
        或由控制器根据 intent 派发结算。

        Args:
            player: 玩家对象（用于攻击/减益目标）。
        """
        logger.info(
            "[Enemy] %s 执行回合（占位）: 意图=%s, 数值=%d",
            self.name, self.intent, self.intent_value,
        )
        # TODO: Phase 2+ 由 AI 策略实现具体行为

    def choose_intent(self) -> None:
        """选择下回合意图的占位钩子。

        Phase 1 不实现。未来由 AI 策略决定（随机/模式/血量阈值等）。
        """
        logger.debug("[Enemy] %s 选择意图（占位）", self.name)
        # TODO: Phase 2+ 实现意图选择逻辑

    # ------------------------------------------------------------------ #
    # 魔术方法
    # ------------------------------------------------------------------ #
    def __str__(self) -> str:
        """可读的敌人状态字符串。"""
        base = super().__str__()
        intent_str = f"{self.intent}({self.intent_value})" if self.intent else "无"
        elite_tag = " [精英]" if self.is_elite else ""
        return f"{base}{elite_tag} | 意图:{intent_str}"