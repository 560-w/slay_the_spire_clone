"""battle.py: BattleController 战斗状态机。

职责:
1. 管理战斗流程状态机（玩家回合 ↔ 敌人回合 ↔ 胜利/失败）。
2. 调度打牌（手动/自动）、回合切换、敌人行动。
3. 处理区栈结构管理卡牌结算（支持嵌套，如倾斜打出倾斜）。
4. 持有 BuffSystem，统一处理伤害修正与 buff tick。
5. 管理 PendingAction（弃牌选择/三选一）。
6. 提供 get_state() 快照供 View 渲染。

打出方式:
- 手动打出 play_card_manual: 扣能量（X费=全部），指向性须选目标，不可打出的牌拒绝。
- 自动打出 play_card_auto: 不扣能量，指向性随机选目标，可打出不可打出的牌。
  X费牌自动打出时 x_value=当前能量（不扣）。

处理区流程:
1. 卡牌从来源移除 → push_to_processing
2. card.play() 执行（可能嵌套 auto_play，新卡牌也推入栈）
3. 若 play 设置 pending_action，挂起等待 resolve_pending
4. 结算完成 → pop_from_processing → 弃置/消耗
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
from src.core.pending_action import (
    PendingAction,
    PendingCardChoice,
    PendingCardSelection,
)
from src.core.player import Player

logger = logging.getLogger(__name__)

# 嵌套打出软上限（防御极端死循环）
MAX_PLAY_DEPTH: int = 50


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
        self._play_depth: int = 0  # 嵌套深度计数

        for enemy in self.enemies:
            enemy.choose_intents()

        logger.info(
            "[Battle] 战斗初始化: 玩家=%s, 敌人=%s",
            self.player.name, [e.name for e in self.enemies],
        )

    # ------------------------------------------------------------------ #
    # 战斗开始
    # ------------------------------------------------------------------ #
    def start_battle(self) -> None:
        self.start_player_turn()
        self.message = "战斗开始！"

    # ------------------------------------------------------------------ #
    # 玩家回合
    # ------------------------------------------------------------------ #
    def start_player_turn(self) -> None:
        self.turn_number += 1
        self.state = BattleState.PLAYER_TURN
        self.selected_card_idx = None
        self.pending_action = None

        self.player.start_of_turn()
        self.buff_system.tick_start_of_turn(self.player)

        self.player.current_energy = self.player.max_energy
        # 基础抽5张 + 回合多抽 buff 加成
        draw_count: int = 5 + self.player.get_buff_stacks(BuffSystem.BUFF_DRAW_NEXT)
        self.player.draw_cards(draw_count)

        self.message = f"回合 {self.turn_number} - 玩家行动"
        logger.info(
            "[Battle] 玩家回合开始: 回合=%d, 能量=%d, 手牌=%d",
            self.turn_number, self.player.current_energy, self.player.hand_size(),
        )

    def select_card(self, hand_idx: int) -> bool:
        """玩家点击手牌：选中或直接打出。"""
        assert 0 <= hand_idx < self.player.hand_size(), (
            f"[Battle] 手牌索引越界: {hand_idx}"
        )
        # 有挂起动作时不响应
        if self.pending_action is not None:
            return False

        card: Card = self.player.hand[hand_idx]

        if not card.playable:
            self.message = f"{card.name} 无法手动打出！"
            return False

        # X费牌与普通牌都需校验能量（X费需至少... 实际0能量也可打出，x=0）
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
        """选目标模式下确认目标。"""
        assert self.selected_card_idx is not None, "[Battle] 当前未处于选目标模式"
        assert 0 <= enemy_idx < len(self.enemies), "[Battle] 敌人索引越界"
        target_enemy: Enemy = self.enemies[enemy_idx]
        assert target_enemy.is_alive(), "[Battle] 目标已死亡"
        hand_idx: int = self.selected_card_idx
        self.selected_card_idx = None
        self.play_card_manual(hand_idx, target_enemy)

    def play_card_manual(self, hand_idx: int, target_enemy: Optional[Enemy]) -> None:
        """手动打出：扣能量，执行 play，移入处理区。"""
        assert 0 <= hand_idx < self.player.hand_size(), "[Battle] 手牌索引越界"
        card: Card = self.player.hand[hand_idx]
        assert card.playable, f"[Battle] {card.name} 无法手动打出"

        # 计算费用与 x_value
        if card.is_x_cost:
            x_value: int = self.player.current_energy
            self.player.spend_energy(x_value)
        else:
            x_value = 0
            self.player.spend_energy(card.cost)

        self._execute_play(card, target_enemy, x_value, from_hand=True)

    def play_card_auto(
        self, card: Card, x_value: int = 0, from_draw: bool = False
    ) -> None:
        """自动打出：不扣能量，指向性随机选目标，可打出不可打出的牌。"""
        # 嵌套深度保护
        if self._play_depth >= MAX_PLAY_DEPTH:
            logger.warning("[Battle] 达到嵌套打出上限 %d，跳过 %s", MAX_PLAY_DEPTH, card.name)
            return
        self._play_depth += 1
        try:
            # 指向性随机选目标
            target_enemy: Optional[Enemy] = None
            if card.needs_target:
                alive = [e for e in self.enemies if e.is_alive()]
                if alive:
                    target_enemy = random.choice(alive)
                else:
                    target_enemy = None  # 无目标则空打
            self._execute_play(card, target_enemy, x_value, from_hand=False, from_draw=from_draw)
        finally:
            self._play_depth -= 1

    def _execute_play(
        self,
        card: Card,
        target_enemy: Optional[Enemy],
        x_value: int,
        from_hand: bool,
        from_draw: bool = False,
    ) -> None:
        """统一执行打牌流程（手动/自动共用）。"""
        # 从来源移除并推入处理区
        if from_hand:
            self.player.hand.remove(card)
        elif from_draw:
            if card in self.player.draw_pile:
                self.player.draw_pile.remove(card)
        # 否则卡牌已在处理区或外部，无需移除

        self.player.push_to_processing(card)

        logger.info(
            "[Battle] %s 打出 %s → %s (x=%d, auto=%s)",
            self.player.name, card.name,
            target_enemy.name if target_enemy else "自身/无",
            x_value, not from_hand,
        )

        # 执行 play
        card.play(
            user=self.player, target=target_enemy, battle=self, x_value=x_value
        )

        # 若 play 设置了 pending_action，挂起等待 resolve_pending
        if self.pending_action is not None:
            self.message = self.pending_action.prompt
            return

        # 结算完成：弹出处理区 → 弃置/消耗
        self._finalize_card(card)

        # 检查胜负
        self.check_victory()

    def _finalize_card(self, card: Card) -> None:
        """结算完成：从处理区弹出，进入弃牌堆/消耗堆。"""
        popped: Card = self.player.pop_from_processing()
        assert popped is card, f"[Battle] 处理区栈顶不一致: {popped.name} != {card.name}"
        if card.exhausts:
            self.player.exhaust_pile.append(card)
            logger.info("[Battle] %s 消耗: %s", self.player.name, card.name)
        else:
            self.player.discard_pile.append(card)
            logger.info("[Battle] %s 弃置: %s", self.player.name, card.name)

    # ------------------------------------------------------------------ #
    # PendingAction 处理
    # ------------------------------------------------------------------ #
    def resolve_pending_selection(self, selected_cards: List[Card]) -> None:
        """玩家完成手牌选择后调用。"""
        assert self.pending_action is not None, "[Battle] 无挂起动作"
        assert isinstance(self.pending_action, PendingCardSelection), "[Battle] 挂起动作非选择类型"
        action: PendingCardSelection = self.pending_action
        self.pending_action = None

        # 执行选择动作（弃置/消耗）
        for c in selected_cards:
            if action.action == "discard":
                self.player.discard_card(c)
            elif action.action == "exhaust":
                self.player.hand.remove(c)
                self.player.exhaust_pile.append(c)
            # transform 等留待后续

        # 回调
        action.callback(selected_cards)

        # 回调可能触发了 pending_action（嵌套），若无则完成当前卡牌结算
        if self.pending_action is None:
            # 处理区栈顶的卡牌结算完成
            if self.player.processing_pile:
                top_card: Card = self.player.processing_pile[-1]
                self._finalize_card(top_card)
                self.check_victory()

    def resolve_pending_choice(self, chosen: Optional[Card]) -> None:
        """玩家完成三选一后调用。"""
        assert self.pending_action is not None, "[Battle] 无挂起动作"
        assert isinstance(self.pending_action, PendingCardChoice), "[Battle] 挂起动作非三选一"
        action: PendingCardChoice = self.pending_action
        self.pending_action = None
        action.callback(chosen)
        if self.pending_action is None:
            if self.player.processing_pile:
                top_card: Card = self.player.processing_pile[-1]
                self._finalize_card(top_card)
                self.check_victory()

    # ------------------------------------------------------------------ #
    # 回合结束
    # ------------------------------------------------------------------ #
    def end_player_turn(self) -> None:
        if self.state != BattleState.PLAYER_TURN:
            return
        if self.pending_action is not None:
            return  # 有挂起动作时不结束

        self.selected_card_idx = None

        # 1. 回合结束自动打出的牌（灼伤）
        auto_cards: List[Card] = [c for c in self.player.hand if c.auto_play_end_of_turn]
        for c in auto_cards:
            self.player.hand.remove(c)
            self.player.push_to_processing(c)
            c.play(user=self.player, target=None, battle=self, x_value=0)
            if self.pending_action is not None:
                return  # 挂起，等待解决后继续
            self._finalize_card(c)
            if self.player.is_dead():
                self.state = BattleState.DEFEAT
                self.message = "玩家阵亡..."
                return

        # 2. 虚无卡消耗
        ethereal_cards: List[Card] = [c for c in self.player.hand if c.ethereal]
        for c in ethereal_cards:
            self.player.hand.remove(c)
            self.player.exhaust_pile.append(c)
            logger.info("[Battle] %s 虚无消耗: %s", self.player.name, c.name)

        # 3. 弃置剩余手牌
        self.player.end_turn()
        # 4. buff end tick
        self.buff_system.tick_end_of_turn(self.player)

        if self.player.is_dead():
            self.state = BattleState.DEFEAT
            self.message = "玩家阵亡..."
            return

        self.state = BattleState.ENEMY_TURN
        self.message = "敌人行动中..."
        logger.info("[Battle] 玩家回合结束，进入敌人回合")

    # ------------------------------------------------------------------ #
    # 敌人回合
    # ------------------------------------------------------------------ #
    def run_enemy_turn(self) -> None:
        if self.state != BattleState.ENEMY_TURN:
            return

        for enemy in self.enemies:
            if not enemy.is_alive():
                continue
            enemy.start_of_turn()
            self.buff_system.tick_start_of_turn(enemy)
            enemy.take_turn(player=self.player, battle=self)
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

    # ------------------------------------------------------------------ #
    # 胜负判定
    # ------------------------------------------------------------------ #
    def check_victory(self) -> bool:
        if all(not e.is_alive() for e in self.enemies):
            self.state = BattleState.VICTORY
            self.message = "战斗胜利！"
            return True
        return False

    def is_over(self) -> bool:
        return self.state in (BattleState.VICTORY, BattleState.DEFEAT)

    # ------------------------------------------------------------------ #
    # 状态牌塞入
    # ------------------------------------------------------------------ #
    def add_status_card_to_player(self, card: Card) -> None:
        self.player.add_card_to_draw(card)
        self.message = f"{card.name} 被塞入抽牌堆！"

    # ------------------------------------------------------------------ #
    # 自动打牌接口（供卡牌效果调用，如倾斜）
    # ------------------------------------------------------------------ #
    def auto_play_from_draw_top(self, count: int) -> None:
        """从抽牌堆顶自动打出 count 张牌（倾斜效果用）。"""
        actual: int = 0
        for _ in range(count):
            # 抽牌堆不足则洗回弃牌堆
            if not self.player.draw_pile:
                self.player._shuffle_discard_into_draw()
            if not self.player.draw_pile:
                break
            card: Card = self.player.draw_pile.pop()
            # X费牌自动打出：x_value=当前能量（不扣）
            xv: int = self.player.current_energy if card.is_x_cost else 0
            self.play_card_auto(card, x_value=xv, from_draw=True)
            actual += 1
        logger.info("[Battle] 倾斜打出 %d 张牌", actual)

    # ------------------------------------------------------------------ #
    # 状态快照
    # ------------------------------------------------------------------ #
    def get_state(self) -> dict:
        enemy_summaries: list[list[str]] = [
            e.get_display_summary(self.buff_system) for e in self.enemies
        ]
        return {
            "state": self.state,
            "turn_number": self.turn_number,
            "message": self.message,
            "player": self.player,
            "enemies": self.enemies,
            "enemy_summaries": enemy_summaries,
            "selected_card_idx": self.selected_card_idx,
            "pending_action": self.pending_action,
        }