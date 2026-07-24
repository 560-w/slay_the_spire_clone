"""status_effect.py: 状态效果系统。

设计原则:
1. StatusEffect 基类提供钩子，具体效果自行决定层数变化与结算逻辑。
2. 不统一分类"临时/永久"，由效果的 on_turn_start/end 钩子自行调用 add/remove_buff。
3. 注册表管理 name → StatusEffect，BuffSystem 查询注册表调用钩子。
4. 力量/敏捷层数可负（降低伤害/格挡）。
"""

from __future__ import annotations

import logging
import math
from typing import Dict

logger = logging.getLogger(__name__)


class StatusEffect:
    """状态效果基类。

    属性:
        name (str): 显示名（与 Entity.buffs 的键一致）
        has_stacks (bool): 是否有层数（False=无层数标记效果）

    钩子（子类按需覆写）:
        on_turn_start(entity, stacks): 回合开始结算
        on_turn_end(entity, stacks): 回合结束结算
        modify_outgoing_damage(entity, base, stacks) -> int: 攻击伤害修正
        modify_incoming_damage(entity, base, stacks) -> int: 受击伤害修正
        modify_block_gain(entity, base, stacks) -> int: 获得格挡修正
        get_extra_draw(stacks) -> int: 回合开始额外抽牌数
    """

    def __init__(self, name: str, has_stacks: bool = True) -> None:
        self.name: str = name
        self.has_stacks: bool = has_stacks

    def on_turn_start(self, entity, stacks: int) -> None:
        """回合开始结算（效果自行决定是否递减层数）。"""
        pass

    def on_turn_end(self, entity, stacks: int) -> None:
        """回合结束结算。"""
        pass

    def modify_outgoing_damage(self, entity, base: int, stacks: int) -> int:
        """攻击伤害修正，返回修正后的值（>=0）。"""
        return base

    def modify_incoming_damage(self, entity, base: int, stacks: int) -> int:
        """受击伤害修正。"""
        return base

    def modify_block_gain(self, entity, base: int, stacks: int) -> int:
        """获得格挡修正。"""
        return base

    def get_extra_draw(self, stacks: int) -> int:
        """回合开始额外抽牌数。"""
        return 0


# ====================================================================== #
# 具体状态效果
# ====================================================================== #
class PowerEffect(StatusEffect):
    """力量：每层 +1 攻击伤害（可负）。持久，不递减。"""

    def __init__(self) -> None:
        super().__init__(name="力量", has_stacks=True)

    def modify_outgoing_damage(self, entity, base: int, stacks: int) -> int:
        return max(base + stacks, 0)


class DexterityEffect(StatusEffect):
    """敏捷：每层 +1 获得格挡（可负）。持久。"""

    def __init__(self) -> None:
        super().__init__(name="敏捷", has_stacks=True)

    def modify_block_gain(self, entity, base: int, stacks: int) -> int:
        return max(base + stacks, 0)


class WeakEffect(StatusEffect):
    """虚弱：攻击伤害 ×0.75。回合开始失去1层。"""

    def __init__(self) -> None:
        super().__init__(name="虚弱", has_stacks=True)

    def on_turn_start(self, entity, stacks: int) -> None:
        if stacks > 0:
            entity.remove_buff(self.name, 1)

    def modify_outgoing_damage(self, entity, base: int, stacks: int) -> int:
        return max(math.floor(base * 0.75), 0)


class VulnerableEffect(StatusEffect):
    """易伤：受到的伤害 ×1.5。回合开始失去1层。"""

    def __init__(self) -> None:
        super().__init__(name="易伤", has_stacks=True)

    def on_turn_start(self, entity, stacks: int) -> None:
        if stacks > 0:
            entity.remove_buff(self.name, 1)

    def modify_incoming_damage(self, entity, base: int, stacks: int) -> int:
        return max(math.floor(base * 1.5), 0)


class LightningEffect(StatusEffect):
    """电击：回合结束每层扣1血（无视护甲）。持久。"""

    def __init__(self) -> None:
        super().__init__(name="电击", has_stacks=True)

    def on_turn_end(self, entity, stacks: int) -> None:
        if stacks > 0:
            hp_loss = min(stacks, entity.current_hp)
            entity.current_hp -= hp_loss
            logger.info("[Effect] %s 电击×%d 结算，扣血%d，剩余HP=%d/%d",
                        entity.name, stacks, hp_loss, entity.current_hp, entity.max_hp)


class DrawNextEffect(StatusEffect):
    """回合多抽：每层回合开始多抽1张。持久。"""

    def __init__(self) -> None:
        super().__init__(name="回合多抽", has_stacks=True)

    def get_extra_draw(self, stacks: int) -> int:
        return stacks


class GainPowerAtTurnEndEffect(StatusEffect):
    """回合结束获得力量：回合结束时获得X层力量，然后失去此buff所有层数。

    黑暗镣铐等效果用：本回合力量降低，回合结束恢复。
    """

    def __init__(self) -> None:
        super().__init__(name="回合结束获得力量", has_stacks=True)

    def on_turn_end(self, entity, stacks: int) -> None:
        if stacks <= 0:
            return
        # 获得等量力量
        entity.add_buff("力量", stacks)
        # 全部清空自身
        entity.remove_buff(self.name, stacks)
        logger.info("[Effect] %s 回合结束获得力量×%d，已恢复并清空", entity.name, stacks)


# ====================================================================== #
# 注册表
# ====================================================================== #
class StatusEffectRegistry:
    """状态效果注册表（单例）。"""

    _instance = None
    _effects: Dict[str, StatusEffect] = {}

    @classmethod
    def instance(cls) -> "StatusEffectRegistry":
        if cls._instance is None:
            cls._instance = cls()
            cls._register_defaults()
        return cls._instance

    @classmethod
    def _register_defaults(cls) -> None:
        """注册默认效果。"""
        defaults = [
            PowerEffect(), DexterityEffect(), WeakEffect(), VulnerableEffect(),
            LightningEffect(), DrawNextEffect(), GainPowerAtTurnEndEffect(),
        ]
        for eff in defaults:
            cls._effects[eff.name] = eff

    @classmethod
    def get(cls, name: str) -> StatusEffect:
        """获取效果实例（无则返回默认空效果）。"""
        if name not in cls._effects:
            logger.warning("[Registry] 未注册的效果: %s，返回空效果", name)
            return StatusEffect(name=name, has_stacks=True)
        return cls._effects[name]

    @classmethod
    def register(cls, effect: StatusEffect) -> None:
        """注册自定义效果。"""
        cls._effects[effect.name] = effect


# 初始化注册表（导入时自动注册默认效果）
StatusEffectRegistry.instance()