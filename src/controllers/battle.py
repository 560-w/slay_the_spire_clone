"""battle.py: BattleController 战斗状态机。

职责:
1. 管理战斗流程状态机（玩家回合 ↔ 敌人回合 ↔ 胜利/失败）。
2. 调度玩家打牌、回合切换、敌人行动。
3. 持有 BuffSystem，统一处理伤害修正与 buff tick。
4. 提供 get_state() 快照供 View 渲染，保持逻辑与表现分离。

设计原则:
1. 纯逻辑层，不导入任何 UI 库（pygame 等），保证可测试性与可移植。
2. 关键操作（打牌、回合切换）使用 assert + logging 防御性编程。
3. 与 Player/Enemy/Intent 交互通过其公开方法，不直接改私有状态。
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import List, Optional

from src.core.buff_system import BuffSystem
from src.core.card import Card
from src.core.enemy import Enemy
from src.core.entity import Entity
from src.core.player import Player

logger = logging.getLogger(__name__)


class BattleState(Enum):
    """战斗状态枚举。"""
    PLAYER_TURN = "玩家回合"
    ENEMY_TURN = "敌人回合"
    VICTORY = "胜利"
    DEFEAT = "失败"


class BattleController:
    """战斗状态机控制器。

    属性:
        player (Player): 玩家。
        enemies (List[Enemy]): 敌人列表（可能多个）。
        state (BattleState): 当前战斗状态。
        buff_system (BuffSystem): buff 结算系统。
        turn_number (int): 回合计数（从1开始）。
        selected_card_idx (Optional[int]): 当前选中的手牌索引（待选目标），None 表示无。
        message (str): 最近一次事件提示信息（供 UI 展示）。
    """

    def __init__(self, player: Player, enemies: List[Enemy]) -> None:
        """初始化战斗。

        Args:
            player: 玩家对象。
            enemies: 敌人列表，必须非空。

        Raises:
            AssertionError: 当 enemies 为空时触发。
        """
        assert enemies, "[Battle] 敌人列表不能为空"
        assert player is not None, "[Battle] 玩家不能为 None"

        self.player: Player = player
        self.enemies: List[Enemy] = enemies
        self.state: BattleState = BattleState.PLAYER_TURN
        self.buff_system: BuffSystem = BuffSystem()
        self.turn_number: int = 0
        self.selected_card_idx: Optional[int] = None
        self.message: str = ""

        # 敌人首次选择意图
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
        """开始战斗：进入第1回合（玩家回合）。"""
        self.start_player_turn()
        self.message = "战斗开始！"

    # ------------------------------------------------------------------ #
    # 玩家回合
    # ------------------------------------------------------------------ #
    def start_player_turn(self) -> None:
        """开始玩家回合。

        流程:
        1. 回合计数 +1，状态切到 PLAYER_TURN。
        2. 玩家清护甲 + buff start tick。
        3. 回复能量、抽 5 张牌。
        4. 敌人选择本回合意图（玩家回合内展示）。
        """
        self.turn_number += 1
        self.state = BattleState.PLAYER_TURN
        self.selected_card_idx = None

        # 玩家回合开始处理
        self.player.start_of_turn()
        self.buff_system.tick_start_of_turn(self.player)

        # 回复能量 + 抽牌
        self.player.current_energy = self.player.max_energy
        self.player.draw_cards(5)

        # 注意：敌人意图在上一回合结束时已选择，此处不再重复选择

        self.message = f"回合 {self.turn_number} - 玩家行动"
        logger.info(
            "[Battle] 玩家回合开始: 回合=%d, 能量=%d, 手牌=%d",
            self.turn_number, self.player.current_energy, self.player.hand_size(),
        )

    def select_card(self, hand_idx: int) -> bool:
        """选中一张手牌（待选目标或直接打出）。

        - 若该牌 needs_target=True：进入选目标模式（记录 selected_card_idx）。
        - 若该牌 needs_target=False：直接打出结算。

        Args:
            hand_idx: 手牌索引。

        Returns:
            True 表示已开始选目标模式；False 表示已直接打出或失败。

        Raises:
            AssertionError: 当索引越界时触发。
        """
        assert 0 <= hand_idx < self.player.hand_size(), (
            f"[Battle] 手牌索引越界: {hand_idx}（手牌数 {self.player.hand_size()}）"
        )

        card: Card = self.player.hand[hand_idx]

        # 不可打出的牌（状态牌）
        if not card.playable:
            self.message = f"{card.name} 无法打出！"
            logger.info("[Battle] 尝试打出不可打出的牌: %s", card.name)
            return False

        # 能量不足
        if not self.player.can_afford(card.cost):
            self.message = f"能量不足！需要 {card.cost}，当前 {self.player.current_energy}"
            logger.info("[Battle] 能量不足，无法打出 %s", card.name)
            return False

        # 指向性牌：进入选目标模式
        if card.needs_target:
            # 若只有一个存活敌人，自动选目标
            alive_enemies = [e for e in self.enemies if e.is_alive()]
            if len(alive_enemies) == 1:
                self.play_card(hand_idx, target_enemy=alive_enemies[0])
                return False
            # 多敌人：进入选目标模式
            self.selected_card_idx = hand_idx
            self.message = f"选择 {card.name} 的目标"
            logger.info("[Battle] 进入选目标模式: 卡牌=%s", card.name)
            return True

        # 非指向性牌：直接打出
        self.play_card(hand_idx, target_enemy=None)
        return False

    def select_target(self, enemy_idx: int) -> None:
        """在选目标模式下确认目标并打出卡牌。

        Args:
            enemy_idx: 敌人列表索引。

        Raises:
            AssertionError: 当未处于选目标模式或索引越界时触发。
        """
        assert self.selected_card_idx is not None, "[Battle] 当前未处于选目标模式"
        assert 0 <= enemy_idx < len(self.enemies), (
            f"[Battle] 敌人索引越界: {enemy_idx}（敌人数 {len(self.enemies)}）"
        )
        target_enemy: Enemy = self.enemies[enemy_idx]
        assert target_enemy.is_alive(), f"[Battle] 目标 {target_enemy.name} 已死亡"

        hand_idx: int = self.selected_card_idx
        self.selected_card_idx = None  # 清除选目标状态
        self.play_card(hand_idx, target_enemy=target_enemy)

    def play_card(self, hand_idx: int, target_enemy: Optional[Enemy]) -> None:
        """打出一张手牌并结算。

        流程:
        1. 校验：能量充足、目标有效、卡牌可打出。
        2. 扣能量。
        3. 调用卡牌 play 结算效果（伤害经 buff_system 修正）。
        4. 弃置或消耗卡牌。

        Args:
            hand_idx: 手牌索引。
            target_enemy: 目标敌人（指向性牌必填，非指向性牌为 None）。

        Raises:
            AssertionError: 多种校验失败时触发。
        """
        assert 0 <= hand_idx < self.player.hand_size(), "[Battle] 手牌索引越界"
        card: Card = self.player.hand[hand_idx]
        assert card.playable, f"[Battle] {card.name} 无法打出"
        assert self.player.can_afford(card.cost), "[Battle] 能量不足"

        # 指向性校验
        if card.needs_target:
            assert target_enemy is not None, f"[Battle] {card.name} 需要目标"
            assert target_enemy.is_alive(), "[Battle] 目标已死亡"
        else:
            assert target_enemy is None, f"[Battle] {card.name} 不需要目标"

        # 扣能量
        self.player.spend_energy(card.cost)

        # 结算卡牌效果
        logger.info(
            "[Battle] %s 打出 %s → %s",
            self.player.name, card.name,
            target_enemy.name if target_enemy else "自身",
        )
        card.play(user=self.player, target=target_enemy)

        # 弃置或消耗
        if card.exhausts:
            self.player.exhaust_card(card)
        else:
            self.player.discard_card(card)

        self.message = f"打出 {card.name}"

        # 检查是否触发胜利
        self.check_victory()

    def end_player_turn(self) -> None:
        """结束玩家回合，进入敌人回合。

        流程:
        1. 清除选中状态。
        2. 弃置所有手牌。
        3. 玩家 buff end tick。
        4. 切换到敌人回合。
        """
        if self.state != BattleState.PLAYER_TURN:
            return

        self.selected_card_idx = None
        # 弃置所有手牌
        self.player.end_turn()
        # 玩家回合结束 buff tick
        self.buff_system.tick_end_of_turn(self.player)

        # 检查玩家是否死亡（电击等可能致死）
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
        """执行敌人回合。

        遍历存活敌人，依次执行其本回合意图。
        每个敌人行动前先清护甲 + buff start tick。
        全部执行后检查玩家是否死亡。

        注意: 本方法一次性执行所有敌人行动；若需逐步动画展示，
              View 可调用 step_enemy_turn() 逐个执行。
        """
        if self.state != BattleState.ENEMY_TURN:
            return

        for enemy in self.enemies:
            if not enemy.is_alive():
                continue
            # 敌人回合开始：清护甲 + buff tick
            enemy.start_of_turn()
            self.buff_system.tick_start_of_turn(enemy)
            # 执行意图
            enemy.take_turn(player=self.player, battle=self)

            # 检查玩家是否死亡
            if self.player.is_dead():
                self.state = BattleState.DEFEAT
                self.message = "玩家阵亡..."
                logger.info("[Battle] 玩家阵亡，战斗失败")
                return

        # 敌人回合结束 buff tick（电击等）
        for enemy in self.enemies:
            if enemy.is_alive():
                self.buff_system.tick_end_of_turn(enemy)

        # 检查胜利（敌人在玩家回合可能死亡，这里二次确认）
        if self.check_victory():
            return

        # 敌人选择下回合意图（供下一玩家回合展示）
        for enemy in self.enemies:
            if enemy.is_alive():
                enemy.choose_intents()

        # 进入下一玩家回合
        self.start_player_turn()

    # ------------------------------------------------------------------ #
    # 胜负判定
    # ------------------------------------------------------------------ #
    def check_victory(self) -> bool:
        """检查是否所有敌人都已死亡。

        Returns:
            True 表示已胜利并切换状态。
        """
        if all(not e.is_alive() for e in self.enemies):
            self.state = BattleState.VICTORY
            self.message = "战斗胜利！"
            logger.info("[Battle] 所有敌人被消灭，战斗胜利")
            return True
        return False

    def is_over(self) -> bool:
        """战斗是否结束（胜利或失败）。"""
        return self.state in (BattleState.VICTORY, BattleState.DEFEAT)

    # ------------------------------------------------------------------ #
    # 状态牌塞入（供 Intent ADD_CARD 调用）
    # ------------------------------------------------------------------ #
    def add_status_card_to_player(self, card: Card) -> None:
        """向玩家抽牌堆塞入一张状态牌（敌人意图 ADD_CARD 调用）。

        Args:
            card: 要塞入的卡牌（通常为状态牌）。
        """
        self.player.add_card_to_draw(card)
        self.message = f"{card.name} 被塞入抽牌堆！"
        logger.info("[Battle] 状态牌 %s 塞入玩家抽牌堆", card.name)

    # ------------------------------------------------------------------ #
    # 状态快照（供 View 渲染）
    # ------------------------------------------------------------------ #
    def get_state(self) -> dict:
        """获取战斗状态快照，供 View 渲染。

        返回字典包含:
        - state: 战斗状态
        - turn_number: 回合数
        - message: 提示信息
        - player: 玩家对象
        - enemies: 敌人列表
        - enemy_summaries: 各敌人意图展示文字列表
        - selected_card_idx: 选目标模式下的手牌索引
        """
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
        }