"""pygame_view.py: pygame 简易界面（表现层）。

职责:
1. 渲染战斗状态（玩家/敌人/手牌/意图/消息）。
2. 采集鼠标点击输入，调用 BattleController 对应方法。
3. 敌人回合逐步展示（~0.5s 延迟）便于观察。

设计原则:
1. 仅依赖 BattleController 的 get_state() 快照，不持有可变逻辑状态。
2. 不修改核心逻辑，只渲染与采集输入。
3. 无图像美术，纯几何图形 + 文字渲染。
4. 尝试加载微软雅黑中文字体，失败回退默认字体。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pygame

from src.controllers.battle import BattleState

if TYPE_CHECKING:
    from src.controllers.battle import BattleController

logger = logging.getLogger(__name__)

# 窗口尺寸
WINDOW_WIDTH: int = 1280
WINDOW_HEIGHT: int = 800
FPS: int = 30
ENEMY_TURN_STEP_DELAY: int = 500  # 敌人逐步行动间隔（毫秒）

# 配色（RGB）
COLOR_BG = (30, 30, 40)
COLOR_PLAYER = (60, 120, 200)
COLOR_ENEMY = (200, 80, 80)
COLOR_CARD = (220, 200, 140)
COLOR_TEXT = (240, 240, 240)
COLOR_TEXT_DIM = (160, 160, 160)
COLOR_BUTTON = (80, 160, 80)
COLOR_TARGET_HIGHLIGHT = (255, 255, 0)
COLOR_DEAD = (80, 80, 80)


class PygameView:
    """pygame 简易界面。

    属性:
        screen: 主显示表面。
        clock: 帧率时钟。
        font / font_small / font_big: 主/小/大字体。
        card_rects: 当前手牌矩形列表（点击命中检测）。
        enemy_rects: 当前敌人矩形列表（点击命中检测）。
        end_turn_rect: 「结束回合」按钮矩形。
    """

    def __init__(self) -> None:
        """初始化 pygame 窗口与字体。"""
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("杀戮尖塔克隆版 - Phase 2")
        self.clock = pygame.time.Clock()

        # 直接按路径加载中文字体（绕过 match_font 的系统字体枚举崩溃 bug）
        import os
        candidate_fonts = [
            "C:/Windows/Fonts/msyh.ttc",
            "C:/Windows/Fonts/simhei.ttf",
            "C:/Windows/Fonts/simsun.ttc",
        ]
        font_name = None
        for path in candidate_fonts:
            if os.path.isfile(path):
                font_name = path
                break
        if font_name is None:
            logger.warning("[View] 未找到中文字体，使用默认字体")
            font_name = pygame.font.get_default_font()
        self.font = pygame.font.Font(font_name, 20)
        self.font_small = pygame.font.Font(font_name, 16)
        self.font_big = pygame.font.Font(font_name, 32)

        self.card_rects: list[pygame.Rect] = []
        self.enemy_rects: list[pygame.Rect] = []
        self.end_turn_rect: pygame.Rect = pygame.Rect(0, 0, 0, 0)

    # ------------------------------------------------------------------ #
    # 渲染
    # ------------------------------------------------------------------ #
    def render(self, battle: "BattleController") -> None:
        """渲染当前战斗状态。"""
        state: dict = battle.get_state()
        self.screen.fill(COLOR_BG)

        self._render_player_info(state["player"])
        self._render_enemies(state["enemies"], state["enemy_summaries"])
        self._render_hand(state["player"])

        if state["selected_card_idx"] is not None:
            self._render_target_hint(state["enemies"])

        self._render_end_turn_button(state["state"])
        self._render_message(state["message"])

        if battle.is_over():
            self._render_end_screen(battle)

        pygame.display.flip()

    def _render_player_info(self, player) -> None:
        """渲染玩家信息栏（顶部）。"""
        y = 20
        title = self.font_big.render(player.name, True, COLOR_TEXT)
        self.screen.blit(title, (20, y))
        y += 45
        hp_text = self.font.render(
            f"HP: {player.current_hp}/{player.max_hp}  护甲: {player.block}  "
            f"能量: {player.current_energy}/{player.max_energy}",
            True, COLOR_TEXT,
        )
        self.screen.blit(hp_text, (20, y))
        y += 30
        buff_str = ", ".join(f"{k}×{v}" for k, v in player.buffs.items()) or "无 buff"
        buff_text = self.font_small.render(f"Buff: {buff_str}", True, COLOR_TEXT_DIM)
        self.screen.blit(buff_text, (20, y))

    def _render_enemies(self, enemies, summaries) -> None:
        """渲染敌人方块与信息（中部）。"""
        self.enemy_rects = []
        n = len(enemies)
        slot_w = 220
        total_w = n * slot_w
        start_x = (WINDOW_WIDTH - total_w) // 2
        y = 180

        for i, enemy in enumerate(enemies):
            x = start_x + i * slot_w
            rect = pygame.Rect(x, y, slot_w - 20, 200)
            self.enemy_rects.append(rect)

            color = COLOR_DEAD if not enemy.is_alive() else COLOR_ENEMY
            pygame.draw.rect(self.screen, color, rect, border_radius=10)

            name_surf = self.font.render(enemy.name, True, COLOR_TEXT)
            self.screen.blit(name_surf, (rect.x + 10, rect.y + 10))
            hp_surf = self.font.render(
                f"HP: {enemy.current_hp}/{enemy.max_hp}", True, COLOR_TEXT
            )
            self.screen.blit(hp_surf, (rect.x + 10, rect.y + 40))
            block_surf = self.font_small.render(
                f"护甲: {enemy.block}", True, COLOR_TEXT
            )
            self.screen.blit(block_surf, (rect.x + 10, rect.y + 70))
            buff_str = ", ".join(f"{k}×{v}" for k, v in enemy.buffs.items()) or "无"
            buff_surf = self.font_small.render(
                f"Buff: {buff_str}", True, COLOR_TEXT_DIM
            )
            self.screen.blit(buff_surf, (rect.x + 10, rect.y + 95))

            if enemy.is_alive() and summaries[i]:
                intent_text = " | ".join(summaries[i])
                intent_surf = self.font.render(
                    f"意图: {intent_text}", True, COLOR_TEXT
                )
                self.screen.blit(intent_surf, (rect.x + 10, rect.y + 140))

    def _render_hand(self, player) -> None:
        """渲染手牌（底部）。"""
        self.card_rects = []
        n = len(player.hand)
        if n == 0:
            return
        card_w = 140
        card_h = 180
        gap = 10
        total_w = n * card_w + (n - 1) * gap
        start_x = (WINDOW_WIDTH - total_w) // 2
        y = WINDOW_HEIGHT - card_h - 40

        for i, card in enumerate(player.hand):
            x = start_x + i * (card_w + gap)
            rect = pygame.Rect(x, y, card_w, card_h)
            self.card_rects.append(rect)

            color = COLOR_DEAD if not card.playable else COLOR_CARD
            pygame.draw.rect(self.screen, color, rect, border_radius=8)

            name_surf = self.font.render(card.name, True, (40, 30, 20))
            self.screen.blit(name_surf, (rect.x + 8, rect.y + 8))
            cost_surf = self.font_big.render(str(card.cost), True, (40, 30, 20))
            self.screen.blit(cost_surf, (rect.x + 8, rect.y + 35))
            type_surf = self.font_small.render(card.card_type, True, (80, 60, 40))
            self.screen.blit(type_surf, (rect.x + 8, rect.y + 80))
            # 描述按 8 字换行
            desc = card.description
            lines = [desc[j:j+8] for j in range(0, len(desc), 8)]
            for li, line in enumerate(lines[:4]):
                dsurf = self.font_small.render(line, True, (80, 60, 40))
                self.screen.blit(dsurf, (rect.x + 8, rect.y + 110 + li * 18))

    def _render_target_hint(self, enemies) -> None:
        """选目标模式下高亮可选敌人。"""
        for i, rect in enumerate(self.enemy_rects):
            if enemies[i].is_alive():
                pygame.draw.rect(
                    self.screen, COLOR_TARGET_HIGHLIGHT, rect, 4, border_radius=10
                )

    def _render_end_turn_button(self, state) -> None:
        """渲染「结束回合」按钮（右下）。"""
        w, h = 160, 50
        x = WINDOW_WIDTH - w - 20
        y = WINDOW_HEIGHT - h - 20
        self.end_turn_rect = pygame.Rect(x, y, w, h)
        color = COLOR_BUTTON if state == BattleState.PLAYER_TURN else COLOR_DEAD
        pygame.draw.rect(self.screen, color, self.end_turn_rect, border_radius=8)
        text = self.font.render("结束回合", True, COLOR_TEXT)
        self.screen.blit(text, (x + 30, y + 12))

    def _render_message(self, message: str) -> None:
        """渲染提示消息（底部中央上方）。"""
        if not message:
            return
        surf = self.font.render(message, True, COLOR_TEXT)
        x = (WINDOW_WIDTH - surf.get_width()) // 2
        y = WINDOW_HEIGHT - 250
        self.screen.blit(surf, (x, y))

    def _render_end_screen(self, battle: "BattleController") -> None:
        """渲染胜利/失败覆盖层。"""
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        if battle.state == BattleState.VICTORY:
            text, color = "战斗胜利！", (100, 255, 100)
        else:
            text, color = "战斗失败...", (255, 100, 100)
        surf = self.font_big.render(text, True, color)
        x = (WINDOW_WIDTH - surf.get_width()) // 2
        y = (WINDOW_HEIGHT - surf.get_height()) // 2
        self.screen.blit(surf, (x, y))
        hint = self.font.render("点击任意处退出", True, COLOR_TEXT)
        self.screen.blit(hint, ((WINDOW_WIDTH - hint.get_width()) // 2, y + 50))

    # ------------------------------------------------------------------ #
    # 输入处理
    # ------------------------------------------------------------------ #
    def handle_click(self, battle: "BattleController", pos: tuple[int, int]) -> None:
        """处理鼠标点击事件。

        Args:
            battle: 战斗控制器。
            pos: 点击坐标 (x, y)。
        """
        # 战斗结束：退出由 main 循环处理
        if battle.is_over():
            return
        # 仅玩家回合响应
        if battle.state != BattleState.PLAYER_TURN:
            return

        # 结束回合按钮
        if self.end_turn_rect.collidepoint(pos):
            battle.end_player_turn()
            return

        # 选目标模式：点击敌人确认目标
        if battle.selected_card_idx is not None:
            for i, rect in enumerate(self.enemy_rects):
                if rect.collidepoint(pos) and battle.enemies[i].is_alive():
                    battle.select_target(i)
                    return
            return  # 选目标模式下不响应卡牌点击

        # 点击手牌
        for i, rect in enumerate(self.card_rects):
            if rect.collidepoint(pos):
                battle.select_card(i)
                return

    def run_enemy_turn_with_delay(self, battle: "BattleController") -> None:
        """执行敌人回合并逐步展示（带延迟）。

        由于 BattleController.run_enemy_turn 一次性执行全部敌人行动，
        此方法在执行前渲染一次"敌人行动中"状态，执行后再渲染结果。
        完整的逐步动画需重构控制器为步进式，此处做简单延迟展示。

        Args:
            battle: 战斗控制器。
        """
        # 渲染"敌人行动中"状态
        battle.message = "敌人行动中..."
        self.render(battle)
        pygame.time.delay(ENEMY_TURN_STEP_DELAY)
        # 一次性执行敌人回合
        battle.run_enemy_turn()
        # 渲染结果
        self.render(battle)
        pygame.time.delay(ENEMY_TURN_STEP_DELAY)