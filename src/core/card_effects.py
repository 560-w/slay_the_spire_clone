"""card_effects.py: 卡牌效果工具类。"""

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
        """造成伤害（经 buff 修正：力量/虚弱/易伤）。"""
        assert amount >= 0
        outgoing = battle.buff_system.compute_outgoing_damage(source, amount)
        incoming = battle.buff_system.compute_incoming_damage(target, outgoing)
        return target.take_damage(incoming)

    @staticmethod
    def gain_block(user, amount):
        """获得格挡。"""
        return user.gain_block(amount)

    @staticmethod
    def lose_hp(user, amount):
        """失去生命（无视护甲，直接扣血）。"""
        assert amount >= 0
        hp_loss = min(amount, user.current_hp)
        user.current_hp -= hp_loss
        return hp_loss

    @staticmethod
    def heal(user, amount):
        """回复生命。"""
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
        """获得/给予 buff。"""
        return target.add_buff(buff_name, stacks)
