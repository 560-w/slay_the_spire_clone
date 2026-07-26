"""buff_system.py: Buff 结算系统（改用 StatusEffect 注册表）。

职责:
1. 伤害/格挡修正：遍历 entity buffs，查询注册表调用各效果 modify_* 钩子。
2. 回合 tick：调用各效果 on_turn_start/end，效果自行决定层数变化。
3. 不再统一分类"临时/永久"，由效果钩子自行控制。

注意：保留 BUFF_* 名称常量供外部引用，但逻辑委托 StatusEffectRegistry。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .status_effect import StatusEffectRegistry

if TYPE_CHECKING:
    from .entity import Entity

logger = logging.getLogger(__name__)


class BuffSystem:
    """Buff 结算系统。"""

    # buff 名称常量（供外部引用，保持兼容）
    BUFF_POWER: str = "力量"
    BUFF_DEXTERITY: str = "敏捷"
    BUFF_WEAK: str = "虚弱"
    BUFF_VULNERABLE: str = "易伤"
    BUFF_LIGHTNING: str = "电击"
    BUFF_DRAW_NEXT: str = "回合多抽"
    BUFF_GAIN_POWER_END: str = "回合结束获得力量"
    BUFF_THORNS: str = "荆棘"

    # ------------------------------------------------------------------ #
    # 伤害修正
    # ------------------------------------------------------------------ #
    def compute_outgoing_damage(self, attacker, base_damage: int) -> int:
        """计算攻击方最终造成的伤害（遍历所有 buff 修正）。"""
        assert base_damage >= 0, f"[BuffSystem] base_damage 不能为负，收到 {base_damage}"
        damage: int = base_damage
        for name, stacks in list(attacker.buffs.items()):
            eff = StatusEffectRegistry.get(name)
            damage = eff.modify_outgoing_damage(attacker, damage, stacks)
        return max(damage, 0)

    def compute_incoming_damage(self, target, damage: int) -> int:
        """计算受击方最终承受的伤害。"""
        assert damage >= 0, f"[BuffSystem] incoming damage 不能为负，收到 {damage}"
        for name, stacks in list(target.buffs.items()):
            eff = StatusEffectRegistry.get(name)
            damage = eff.modify_incoming_damage(target, damage, stacks)
        return max(damage, 0)

    def compute_block_gain(self, entity, base_block: int) -> int:
        """计算最终获得的格挡（敏捷修正）。"""
        block: int = base_block
        for name, stacks in list(entity.buffs.items()):
            eff = StatusEffectRegistry.get(name)
            block = eff.modify_block_gain(entity, block, stacks)
        return max(block, 0)

    # ------------------------------------------------------------------ #
    # 回合 tick
    # ------------------------------------------------------------------ #
    def tick_start_of_turn(self, entity) -> None:
        """回合开始：遍历各效果调用 on_turn_start（效果自行决定层数变化）。"""
        for name, stacks in list(entity.buffs.items()):
            eff = StatusEffectRegistry.get(name)
            eff.on_turn_start(entity, stacks)
        logger.debug("[BuffSystem] %s 回合开始 tick 完成: %s", entity.name, entity.buffs)

    def tick_end_of_turn(self, entity) -> None:
        """回合结束：遍历各效果调用 on_turn_end。"""
        for name, stacks in list(entity.buffs.items()):
            eff = StatusEffectRegistry.get(name)
            eff.on_turn_end(entity, stacks)
        logger.debug("[BuffSystem] %s 回合结束 tick 完成: %s", entity.name, entity.buffs)

    def get_extra_draw(self, entity) -> int:
        """获取回合开始额外抽牌数（回合多抽等效果）。"""
        extra: int = 0
        for name, stacks in entity.buffs.items():
            eff = StatusEffectRegistry.get(name)
            extra += eff.get_extra_draw(stacks)
        return extra