"""card_effects.py: 卡牌效果工具类。

集中实现常见卡牌功能：
- deal_damage: 造成伤害（经 buff 修正）
- gain_block: 获得格挡（经敏捷修正）
- lose_hp: 失去生命（无视护甲）
- heal / draw_cards / gain_energy / add_buff

设计原则:
1. deal_damage 经 BuffSystem 修正（力量/虚弱/易伤）。
2. gain_block 经 BuffSystem.compute_block_gain 修正（敏捷）。
3. lose_hp 无视护甲，直接扣血。
4. 纯工具函数，无状态。

需求9: deal_damage/gain_block 记录结构化日志（通过 battle.log_* 方法）。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from .entity import Entity

if TYPE_CHECKING:
    from ..controllers.battle import BattleController
    from .player import Player

logger = logging.getLogger(__name__)


class CardEffects:
    """卡牌效果工具类（静态方法集合）。"""

    @staticmethod
    def deal_damage(battle, source, target, amount):
        """造成伤害（经 buff 修正：力量/虚弱/易伤）。需求9: 记录日志。"""
        assert amount >= 0
        outgoing = battle.buff_system.compute_outgoing_damage(source, amount)
        incoming = battle.buff_system.compute_incoming_damage(target, outgoing)
        logger.info("[CardEffects] %s -> %s 造成伤害 (基础%d -> 最终%d)", source.name, target.name, amount, incoming)
        hp_before = target.current_hp
        target.take_damage(incoming)
        actual = hp_before - target.current_hp
        # 需求9: 记录伤害日志
        if hasattr(battle, "log_damage"):
            battle.log_damage(source.name, target.name, actual)
        # 荆棘反伤（无视护甲，直接扣血）
        thorns = target.buffs.get("荆棘", 0)
        if thorns > 0 and source.current_hp > 0:
            recoil = min(thorns, source.current_hp)
            source.current_hp -= recoil
            logger.info("[CardEffects] %s 受到 %s 荆棘反伤 %d", source.name, target.name, recoil)
        return actual

    @staticmethod
    def gain_block(battle, user, amount):
        """获得格挡（经敏捷修正）。需求9: 记录日志。"""
        actual = battle.buff_system.compute_block_gain(user, amount)
        user.gain_block(actual)
        # 需求9: 记录格挡日志
        if hasattr(battle, "log_block"):
            battle.log_block(user.name, actual)
        return actual

    @staticmethod
    def lose_hp(user, amount):
        """失去生命（无视护甲，直接扣血）。

        注意: 此函数无 battle 参数，无法记录结构化日志。
        需求12: 扣血后死亡检查由 battle._execute_play 负责。
        """
        assert amount >= 0
        hp_loss = min(amount, user.current_hp)
        user.current_hp -= hp_loss
        logger.info("[CardEffects] %s 失去 %d 生命（无视护甲），剩余HP=%d/%d", user.name, hp_loss, user.current_hp, user.max_hp)
        return hp_loss

    @staticmethod
    def heal(user, amount):
        """回复生命（不超过 max_hp）。"""
        return user.heal(amount)

    @staticmethod
    def draw_cards(player, count):
        """抽牌。"""
        return len(player.draw_cards(count))

    @staticmethod
    def gain_energy(player, amount):
        """获得能量。"""
        return player.gain_energy(amount)

    @staticmethod
    def add_buff(target, buff_name, stacks):
        """获得/给予 buff（层数可负）。需求9: 不在此记录日志（由调用方 battle 记录）。"""
        return target.add_buff(buff_name, stacks)