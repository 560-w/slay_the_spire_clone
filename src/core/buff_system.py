"""buff_system.py: Buff 效果集中结算系统。

职责:
1. 伤害数值修正（攻击方/受击方 buff）:
   - 力量: 攻击方持有，每层 +1 攻击伤害
   - 虚弱: 攻击方持有，伤害 ×0.75（向下取整，最少 0）
   - 易伤: 受击方持有，受到的伤害 ×1.5（向下取整）
2. 回合 tick（层数递减/到期清理）:
   - 虚弱/易伤/脆弱等"临时" buff 每回合开始时层数 -1，归零清除
   - 电击(Lightning): 回合结束时每层造成 1 点伤害（无视护甲）
   - 力量等"持久" buff 不递减

设计原则:
1. Entity 保持纯粹的数值容器，buff 修正逻辑全部集中于此，职责分离。
2. 提供纯函数式接口 compute_*，便于测试与复用。
3. 临时 buff 集合用类常量定义，新增 buff 时在此维护清单。
"""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .entity import Entity

logger = logging.getLogger(__name__)


class BuffSystem:
    """Buff 结算系统。

    类常量:
        BUFF_POWER:      力量（持久，+攻击伤害）
        BUFF_WEAK:       虚弱（临时，攻击伤害×0.75）
        BUFF_VULNERABLE: 易伤（临时，受击伤害×1.5）
        BUFF_LIGHTNING:  电击（持久，回合结束每层1伤害）
        TEMPORARY_BUFFS: 临时 buff 集合（每回合开始层数-1）
    """

    # buff 名称常量
    BUFF_POWER: str = "力量"
    BUFF_WEAK: str = "虚弱"
    BUFF_VULNERABLE: str = "易伤"
    BUFF_LIGHTNING: str = "电击"
    BUFF_DRAW_NEXT: str = "回合多抽"  # 持久，每回合开始多抽该层数的牌

    # 临时 buff：每回合开始时层数 -1
    TEMPORARY_BUFFS: set[str] = {BUFF_WEAK, BUFF_VULNERABLE}

    # ------------------------------------------------------------------ #
    # 伤害修正
    # ------------------------------------------------------------------ #
    def compute_outgoing_damage(
        self, attacker: "Entity", base_damage: int
    ) -> int:
        """计算攻击方最终造成的伤害（不含受击方的易伤修正）。

        修正顺序:
        1. 力量: +力量层数
        2. 虚弱: 结果 ×0.75（向下取整，最少 0）

        Args:
            attacker: 攻击方实体。
            base_damage: 卡牌/意图的基础伤害，>=0。

        Returns:
            经攻击方 buff 修正后的伤害（>=0）。
        """
        assert base_damage >= 0, f"[BuffSystem] base_damage 不能为负，收到 {base_damage}"

        # 力量：每层 +1
        power_stacks: int = attacker.get_buff_stacks(self.BUFF_POWER)
        damage: int = base_damage + power_stacks

        # 虚弱：×0.75
        if attacker.has_buff(self.BUFF_WEAK):
            damage = math.floor(damage * 0.75)
            logger.debug(
                "[BuffSystem] %s 虚弱修正: %d → %d", attacker.name, base_damage, damage
            )

        # 不低于 0
        damage = max(damage, 0)
        return damage

    def compute_incoming_damage(
        self, target: "Entity", damage: int
    ) -> int:
        """计算受击方最终承受的伤害（在 outgoing 之后的第二步修正）。

        修正:
        - 易伤: 受到的伤害 ×1.5（向下取整）

        Args:
            target: 受击方实体。
            damage: 经 outgoing 修正后的伤害，>=0。

        Returns:
            经受击方 buff 修正后的最终伤害（>=0）。
        """
        assert damage >= 0, f"[BuffSystem] incoming damage 不能为负，收到 {damage}"

        if target.has_buff(self.BUFF_VULNERABLE):
            damage = math.floor(damage * 1.5)
            logger.debug(
                "[BuffSystem] %s 易伤修正: → %d", target.name, damage
            )

        return max(damage, 0)

    # ------------------------------------------------------------------ #
    # 回合 tick
    # ------------------------------------------------------------------ #
    def tick_start_of_turn(self, entity: "Entity") -> None:
        """回合开始时的 buff 结算。

        处理:
        - 临时 buff（虚弱/易伤）层数 -1，归零清除。

        Args:
            entity: 进入回合的实体。
        """
        # 收集需要递减的 buff（避免修改字典时遍历）
        to_decrement: list[str] = [
            name for name in self.TEMPORARY_BUFFS if entity.has_buff(name)
        ]
        for name in to_decrement:
            # 层数 -1，remove_buff 处理归零清除
            entity.remove_buff(name, 1)

        logger.debug("[BuffSystem] %s 回合开始 buff tick 完成: %s", entity.name, entity.buffs)

    def tick_end_of_turn(self, entity: "Entity") -> None:
        """回合结束时的 buff 结算。

        处理:
        - 电击: 每层造成 1 点伤害（无视护甲，直接扣血）。

        Args:
            entity: 结束回合的实体。
        """
        lightning_stacks: int = entity.get_buff_stacks(self.BUFF_LIGHTNING)
        if lightning_stacks > 0:
            # 电击无视护甲：直接扣血（绕过 take_damage 的护甲抵扣）
            hp_loss: int = min(lightning_stacks, entity.current_hp)
            entity.current_hp -= hp_loss
            logger.info(
                "[BuffSystem] %s 电击 ×%d 结算，扣血 %d，剩余HP=%d/%d",
                entity.name, lightning_stacks, hp_loss,
                entity.current_hp, entity.max_hp,
            )