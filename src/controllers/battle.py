"""battle.py: BattleController 战斗状态机。

需求9: 结构化日志条目（LogEntry），带颜色类型。
需求12: 卡牌结算后检查玩家死亡（修复祭品扣血不致死）。
"""

from __future__ import annotations

import logging
import random
from enum import Enum
from typing import List, Optional

from src.core.buff_system import BuffSystem
from src.core.card import Card
from src.core.enemy import Enemy
from src.core.entity import Entity
from src.core.intent import Intent
from src.core.pending_action import (
    PendingAction,
    PendingCardChoice,
    PendingCardSelection,
)
from src.core.player import Player

logger = logging.getLogger(__name__)

MAX_PLAY_DEPTH: int = 50


class LogEntry:
    """战斗日志条目（需求9，带颜色类型，支持富文本片段）。"""
    ENTITY: str = "entity"
    DAMAGE: str = "damage"
    BLOCK: str = "block"
    BUFF: str = "buff"
    CARD: str = "card"
    ENERGY: str = "energy"
    NORMAL: str = "normal"
    SEPARATOR: str = "separator"

    def __init__(self, text: str, color_type: str = "normal", segments=None) -> None:
        self.text: str = text
        self.color_type: str = color_type
        self.segments = segments

    def __str__(self) -> str:
        return self.text


class BattleState(Enum):
    """战斗状态枚举。"""
    PLAYER_TURN = "玩家回合"
    ENEMY_TURN = "敌人回合"
    VICTORY = "胜利"
    DEFEAT = "失败"


class BattleController:
    """战斗状态机控制器。"""

    def __init__(self, player: Player, enemies: List[Enemy]) -> None:
        assert enemies, "[Battle] 敌人列表不能为空"
        assert player is not None, "[Battle] 玩家不能为 None"

        self.player: Player = player
        self.enemies: List[Enemy] = enemies
        self.state: BattleState = BattleState.PLAYER_TURN
        self.buff_system: BuffSystem = BuffSystem()
        self.turn_number: int = 0
        self.selected_card_idx: Optional[int] = None
        self.message: str = ""
        self.pending_action: PendingAction = None
        self._play_depth: int = 0
        self.battle_log: list[LogEntry] = []  # 需求9: 结构化日志

        for enemy in self.enemies:
            enemy.choose_intents()

        logger.info(
            "[Battle] 战斗初始化: 玩家=%s, 敌人=%s",
            self.player.name, [e.name for e in self.enemies],
        )

    def start_battle(self) -> None:
        # 触发遗物 on_combat_start 钩子
        for relic in self.player.relics:
            try:
                relic.on_combat_start(self.player, self)
            except Exception as e:
                logger.warning("[Battle] 遗物 %s on_combat_start 异常: %s", relic.name, e)
        self.start_player_turn()
        self.message = "战斗开始！"

    def start_player_turn(self) -> None:
        self.turn_number += 1
        self.state = BattleState.PLAYER_TURN
        self.selected_card_idx = None
        self.pending_action = None
        self._log_entry(f"我方回合（{self.turn_number})", LogEntry.SEPARATOR,
                       [(f"我方回合（{self.turn_number}）", "separator")])
        self.player.start_of_turn()
        self.buff_system.tick_start_of_turn(self.player)
        # 触发遗物 on_turn_start 钩子
        for relic in self.player.relics:
            try:
                relic.on_turn_start(self.player, self)
            except Exception as e:
                logger.warning("[Battle] 遗物 %s on_turn_start 异常: %s", relic.name, e)
        self.player.current_energy = self.player.max_energy
        draw_count: int = 5 + self.buff_system.get_extra_draw(self.player)
        self.player.draw_cards(draw_count)
        self.message = f"回合 {self.turn_number} - 玩家行动"

    def select_card(self, hand_idx: int) -> bool:
        assert 0 <= hand_idx < self.player.hand_size()
        if self.pending_action is not None:
            return False
        card: Card = self.player.hand[hand_idx]
        if not card.playable:
            self.message = f"{card.name} 无法手动打出！"
            return False
        if not card.is_x_cost and not self.player.can_afford(card.cost):
            self.message = f"能量不足！需要 {card.cost}，当前 {self.player.current_energy}"
            return False
        if card.needs_target:
            alive_enemies = [e for e in self.enemies if e.is_alive()]
            if len(alive_enemies) == 1:
                self.play_card_manual(hand_idx, alive_enemies[0])
                return False
            self.selected_card_idx = hand_idx
            self.message = f"选择 {card.name} 的目标"
            return True
        self.play_card_manual(hand_idx, None)
        return False

    def select_target(self, enemy_idx: int) -> None:
        assert self.selected_card_idx is not None
        assert 0 <= enemy_idx < len(self.enemies)
        target_enemy: Enemy = self.enemies[enemy_idx]
        assert target_enemy.is_alive()
        hand_idx: int = self.selected_card_idx
        self.selected_card_idx = None
        self.play_card_manual(hand_idx, target_enemy)

    def play_card_manual(self, hand_idx: int, target_enemy: Optional[Enemy]) -> None:
        assert 0 <= hand_idx < self.player.hand_size()
        card: Card = self.player.hand[hand_idx]
        assert card.playable
        if card.is_x_cost:
            x_value: int = self.player.current_energy
            self.player.spend_energy(x_value)
        else:
            x_value = 0
            self.player.spend_energy(card.cost)
        self._execute_play(card, target_enemy, x_value, from_hand=True)

    def play_card_auto(self, card: Card, x_value: int = 0, from_draw: bool = False) -> None:
        if self._play_depth >= MAX_PLAY_DEPTH:
            return
        self._play_depth += 1
        try:
            target_enemy: Optional[Enemy] = None
            if card.needs_target:
                alive = [e for e in self.enemies if e.is_alive()]
                if alive:
                    target_enemy = random.choice(alive)
            self._execute_play(card, target_enemy, x_value, from_hand=False, from_draw=from_draw)
        finally:
            self._play_depth -= 1

    def _execute_play(self, card, target_enemy, x_value, from_hand, from_draw=False):
        if from_hand:
            self.player.hand.remove(card)
        elif from_draw:
            if card in self.player.draw_pile:
                self.player.draw_pile.remove(card)
        self.player.push_to_processing(card)
        target_name = target_enemy.name if target_enemy else ""
        ctext = f"打出 {card.name}" + (f" → {target_name}" if target_name else "")
        csegs = [("打出 ", "normal"), (card.name, "card")]
        if target_name:
            csegs += [(" → ", "normal"), (target_name, "entity")]
        self._log_entry(ctext, LogEntry.CARD, csegs)
        card.play(user=self.player, target=target_enemy, battle=self, x_value=x_value)
        # 需求12: 检查玩家死亡
        if self.player.is_dead():
            self.state = BattleState.DEFEAT
            self.message = "玩家阵亡..."
            return
        if self.pending_action is not None:
            self.message = self.pending_action.prompt
            return
        self._finalize_card(card)
        if self.player.is_dead():
            self.state = BattleState.DEFEAT
            self.message = "玩家阵亡..."
            return
        self.check_victory()

    def _log(self, msg, color_type="normal", segments=None):
        self.battle_log.append(LogEntry(msg, color_type, segments))
        if len(self.battle_log) > 30:
            self.battle_log.pop(0)

    def _log_entry(self, msg, color_type="normal", segments=None):
        self._log(msg, color_type, segments)

    def _finalize_card(self, card):
        popped = self.player.pop_from_processing()
        assert popped is card
        if card.exhausts or card.is_power:
            self.player.exhaust_pile.append(card)
        else:
            self.player.discard_pile.append(card)

    def log_damage(self, source_name, target_name, amount):
        text = f"{source_name} 对 {target_name} 造成 {amount} 点伤害"
        segs = [(source_name, "entity"), (" 对 ", "normal"), (target_name, "entity"),
                (" 造成 ", "normal"), (str(amount), "damage"), (" 点伤害", "normal")]
        self._log_entry(text, LogEntry.DAMAGE, segs)

    def log_kill(self, enemy_name):
        text = f"{enemy_name} 被击杀了！"
        segs = [(enemy_name, "entity"), (" 被击杀了！", "damage")]
        self._log_entry(text, LogEntry.DAMAGE, segs)

    def log_block(self, entity_name, amount):
        text = f"{entity_name} 获得了 {amount} 点格挡"
        segs = [(entity_name, "entity"), (" 获得了 ", "normal"),
                (str(amount), "block"), (" 点格挡", "normal")]
        self._log_entry(text, LogEntry.BLOCK, segs)

    def log_buff(self, entity_name, buff_name, stacks):
        text = f"{entity_name} 获得了 {stacks} 层 {buff_name}"
        segs = [(entity_name, "entity"), (" 获得了 ", "normal"),
                (str(stacks), "buff"), (" 层 ", "normal"), (buff_name, "buff")]
        self._log_entry(text, LogEntry.BUFF, segs)

    def log_add_card(self, source_name, pile, card_name):
        text = f"{source_name} 向你的{pile}中加入了 {card_name}"
        segs = [(source_name, "entity"), (" 向你的", "normal"), (pile, "normal"),
                ("中加入了 ", "normal"), (card_name, "card")]
        self._log_entry(text, LogEntry.CARD, segs)

    def log_energy(self, entity_name, amount):
        text = f"{entity_name} 获得 {amount} 点能量"
        segs = [(entity_name, "entity"), (" 获得 ", "normal"),
                (str(amount), "energy"), (" 点能量", "normal")]
        self._log_entry(text, LogEntry.ENERGY, segs)

    def resolve_pending_selection(self, selected_cards):
        assert self.pending_action is not None
        assert isinstance(self.pending_action, PendingCardSelection)
        action = self.pending_action
        self.pending_action = None
        if action.action == "discard":
            for c in selected_cards:
                self.player.discard_card(c)
        elif action.action == "exhaust":
            for c in selected_cards:
                if c in self.player.hand:
                    self.player.hand.remove(c)
                self.player.exhaust_pile.append(c)
        action.callback(selected_cards)
        if self.player.is_dead():
            self.state = BattleState.DEFEAT
            self.message = "玩家阵亡..."
            return
        if self.pending_action is None:
            if self.player.processing_pile:
                top_card = self.player.processing_pile[-1]
                self._finalize_card(top_card)
                if self.player.is_dead():
                    self.state = BattleState.DEFEAT
                    self.message = "玩家阵亡..."
                    return
                self.check_victory()

    def resolve_pending_choice(self, chosen):
        assert self.pending_action is not None
        assert isinstance(self.pending_action, PendingCardChoice)
        action = self.pending_action
        self.pending_action = None
        action.callback(chosen)
        if self.player.is_dead():
            self.state = BattleState.DEFEAT
            self.message = "玩家阵亡..."
            return
        if self.pending_action is None:
            if self.player.processing_pile:
                top_card = self.player.processing_pile[-1]
                self._finalize_card(top_card)
                if self.player.is_dead():
                    self.state = BattleState.DEFEAT
                    self.message = "玩家阵亡..."
                    return
                self.check_victory()

    def end_player_turn(self):
        if self.state != BattleState.PLAYER_TURN:
            return
        if self.pending_action is not None:
            return
        self.selected_card_idx = None
        auto_cards = [c for c in self.player.hand if c.auto_play_end_of_turn]
        for c in auto_cards:
            self.player.hand.remove(c)
            self.player.push_to_processing(c)
            c.play(user=self.player, target=None, battle=self, x_value=0)
            if self.pending_action is not None:
                return
            self._finalize_card(c)
            if self.player.is_dead():
                self.state = BattleState.DEFEAT
                self.message = "玩家阵亡..."
                return
        ethereal_cards = [c for c in self.player.hand if c.ethereal]
        for c in ethereal_cards:
            self.player.hand.remove(c)
            self.player.exhaust_pile.append(c)
        self.player.end_turn()
        self.buff_system.tick_end_of_turn(self.player)
        # 触发遗物 on_turn_end 钩子
        for relic in self.player.relics:
            try:
                relic.on_turn_end(self.player, self)
            except Exception as e:
                logger.warning("[Battle] 遗物 %s on_turn_end 异常: %s", relic.name, e)
        if self.player.is_dead():
            self.state = BattleState.DEFEAT
            self.message = "玩家阵亡..."
            return
        self.state = BattleState.ENEMY_TURN
        self.message = "敌人行动中..."
        self._log_entry(f"敌方回合（{self.turn_number}）-----", LogEntry.SEPARATOR,
                       [(f"敌方回合（{self.turn_number}）-----", "separator")])

    def run_enemy_turn(self):
        if self.state != BattleState.ENEMY_TURN:
            return
        for enemy in self.enemies:
            if not enemy.is_alive():
                continue
            enemy.start_of_turn()
            self.buff_system.tick_start_of_turn(enemy)
            self._execute_enemy_intents(enemy)
            if self.player.is_dead():
                self.state = BattleState.DEFEAT
                self.message = "玩家阵亡..."
                return
        for enemy in self.enemies:
            if enemy.is_alive():
                self.buff_system.tick_end_of_turn(enemy)
        if self.check_victory():
            return
        for enemy in self.enemies:
            if enemy.is_alive():
                enemy.choose_intents()
        self.start_player_turn()

    def _execute_enemy_intents(self, enemy):
        for intent in enemy.current_intents:
            if not enemy.is_alive():
                break
            self._execute_single_intent(enemy, intent)
        enemy.current_intents = []

    def _execute_single_intent(self, enemy, intent):
        if intent.intent_type == Intent.TYPE_ATTACK:
            final_damage = self.buff_system.compute_outgoing_damage(enemy, intent.base_value)
            incoming = self.buff_system.compute_incoming_damage(self.player, final_damage)
            hp_before = self.player.current_hp
            self.player.take_damage(incoming)
            actual = hp_before - self.player.current_hp
            self.log_damage(enemy.name, self.player.name, actual)
        elif intent.intent_type == Intent.TYPE_DEFEND:
            enemy.gain_block(intent.base_value)
            self.log_block(enemy.name, intent.base_value)
        elif intent.intent_type == Intent.TYPE_BUFF:
            assert intent.buff_name is not None
            enemy.add_buff(intent.buff_name, intent.base_value)
            self.log_buff(enemy.name, intent.buff_name, intent.base_value)
        elif intent.intent_type == Intent.TYPE_DEBUFF:
            assert intent.buff_name is not None
            self.player.add_buff(intent.buff_name, intent.base_value)
            self.log_buff(enemy.name, intent.buff_name, intent.base_value)
        elif intent.intent_type == Intent.TYPE_ADD_CARD:
            assert intent.status_card is not None
            self.add_status_card_to_player(intent.status_card)
            self.log_add_card(enemy.name, "抽牌堆", intent.status_card.name)

    def check_victory(self):
        if all(not e.is_alive() for e in self.enemies):
            self.state = BattleState.VICTORY
            self.message = "战斗胜利！"
            for e in self.enemies:
                if not e.is_alive():
                    self.log_kill(e.name)
            # 触发遗物 on_combat_end 钩子（胜利时）
            for relic in self.player.relics:
                try:
                    relic.on_combat_end(self.player, self)
                except Exception as e:
                    logger.warning("[Battle] 遗物 %s on_combat_end 异常: %s", relic.name, e)
            return True
        return False

    def is_over(self):
        return self.state in (BattleState.VICTORY, BattleState.DEFEAT)

    def add_status_card_to_player(self, card):
        self.player.add_card_to_draw(card)
        self.message = f"{card.name} 被塞入抽牌堆！"

    def auto_play_from_draw_top(self, count):
        actual = 0
        for _ in range(count):
            if not self.player.draw_pile:
                self.player._shuffle_discard_into_draw()
            if not self.player.draw_pile:
                break
            card = self.player.draw_pile.pop()
            xv = self.player.current_energy if card.is_x_cost else 0
            self.play_card_auto(card, x_value=xv, from_draw=True)
            actual += 1

    def get_state(self):
        enemy_summaries = [e.get_display_summary(self.buff_system) for e in self.enemies]
        return {
            "state": self.state,
            "turn_number": self.turn_number,
            "message": self.message,
            "player": self.player,
            "enemies": self.enemies,
            "enemy_summaries": enemy_summaries,
            "selected_card_idx": self.selected_card_idx,
            "pending_action": self.pending_action,
            "battle_log": self.battle_log,
        }