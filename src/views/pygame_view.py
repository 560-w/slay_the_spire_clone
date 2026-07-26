"""pygame_view.py: pygame 简易界面（表现层）。

支持所有游戏状态渲染：地图、战斗、奖励、篝火、商店、游戏结束。
"""

from __future__ import annotations
import logging, os
from typing import TYPE_CHECKING, Optional, List
import pygame
from src.controllers.battle import BattleState
from src.controllers.game import GameState
from src.core.map import MapNode, RoomType
from src.core.intent import Intent
from src.core.pending_action import PendingCardChoice, PendingCardSelection
from src.views.card_browser import CardBrowser

if TYPE_CHECKING:
    from src.controllers.game import GameController
    from src.controllers.battle import BattleController

logger = logging.getLogger(__name__)
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 800
TOP_BAR_HEIGHT = 50
ENEMY_TURN_STEP_DELAY = 500
COLOR_BG = (30, 30, 40)
COLOR_ENEMY = (200, 80, 80)
COLOR_CARD = (220, 200, 140)
COLOR_TEXT = (240, 240, 240)
COLOR_TEXT_DIM = (160, 160, 160)
COLOR_BUTTON = (80, 160, 80)
COLOR_BUTTON_DIM = (60, 100, 60)
COLOR_TARGET_HIGHLIGHT = (255, 255, 0)
COLOR_DEAD = (80, 80, 80)
COLOR_PILE_BUTTON = (100, 100, 140)
COLOR_LOG_BG = (20, 20, 30)
COLOR_MAP_NODE = (100, 140, 200)
COLOR_MAP_NODE_ACCESSIBLE = (80, 200, 80)
COLOR_MAP_LINE = (100, 100, 120)
COLOR_GOLD = (255, 215, 0)
COLOR_SHOP_CARD = (100, 140, 200)
COLOR_SHOP_PRICE = (220, 180, 80)
COLOR_TOP_BAR = (20, 20, 35)
COLOR_CARD_DISABLED = (100, 95, 85)
COLOR_HOVER_HIGHLIGHT = (255, 255, 100)
COLOR_TOOLTIP_BG = (0, 0, 0, 200)
COLOR_LOG_ENTITY = (255, 220, 80)
COLOR_LOG_DAMAGE = (255, 80, 80)
COLOR_LOG_BLOCK = (80, 180, 255)
COLOR_LOG_BUFF = (200, 100, 255)
COLOR_LOG_CARD = (255, 160, 60)
COLOR_LOG_ENERGY = (255, 220, 80)
COLOR_LOG_SEPARATOR = (120, 120, 120)

# ── 图标映射（真 Emoji）──
CARD_TYPE_EMOJI = {"Attack": "⚔️", "Skill": "🛡️", "Power": "✨"}
ENEMY_EMOJI = {"酸液史莱姆": "🟢", "尖刺史莱姆": "🔴", "酸液史莱姆(L)": "🟢", "尖刺史莱姆(M)": "🔴", "史莱姆Boss": "👑"}
BUFF_EMOJI = {"力量": "💪", "敏捷": "🏃", "易伤": "🎯", "虚弱": "😵", "电击": "⚡", "仪式": "🕯️", "再生": "💚", "无实体": "👻", "壁垒": "🧱", "双重施放": "🔁", "荆棘": "🌵", "残影": "🌫️", "火焰吐息": "🔥", "进化": "🧬", "黑暗": "🌑", "狂暴": "😠", "愤怒": "😡", "伤口": "🩹", "中毒": "☠️", "诅咒": "📿", "回合多抽": "📚", "回合结束获得力量": "🔁💪", "无": "-"}
BUFF_TOOLTIPS = {"力量": lambda s: f"力量：造成的攻击伤害增加{s}" if s > 0 else f"力量：造成的攻击伤害减少{-s}", "敏捷": lambda s: f"敏捷：获得的格挡增加{s}" if s > 0 else f"敏捷：获得的格挡减少{-s}", "易伤": lambda s: f"易伤：在{s}回合内，收到的伤害增加50%。", "虚弱": lambda s: f"虚弱：在{s}回合内，造成的攻击伤害减少25%。", "电击": lambda s: f"电击：每回合结束时受到{s}点伤害（无视护甲）。", "回合多抽": lambda s: f"回合多抽：每回合开始时多抽{s}张牌。", "回合结束获得力量": lambda s: f"回合结束时获得{s}层力量。"}

def _is_emoji_char(ch):
    cp = ord(ch)
    return (0x2600 <= cp <= 0x27BF) or (0x1F000 <= cp <= 0x1FFFF) or (0x2300 <= cp <= 0x23FF) or (0x2B00 <= cp <= 0x2BFF) or (0xFE00 <= cp <= 0xFE0F)


class PygameView:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("杀戮尖塔克隆版 - Phase 5")
        self.clock = pygame.time.Clock()
        fonts = [
            "C:/Windows/Fonts/msyh.ttc",
            "C:/Windows/Fonts/simhei.ttf",
            "C:/Windows/Fonts/simsun.ttc",
        ]
        fn = None
        for f in fonts:
            if os.path.isfile(f):
                fn = f
                break
        if fn is None:
            fn = pygame.font.get_default_font()
        self.font = pygame.font.Font(fn, 20)
        self.font_small = pygame.font.Font(fn, 16)
        self.font_big = pygame.font.Font(fn, 32)
        self.emoji_font = None
        ep = "C:/Windows/Fonts/seguiemj.ttf"
        if os.path.isfile(ep):
            try: self.emoji_font = pygame.font.Font(ep, 18)
            except: pass
        self.card_rects: list = []
        self.enemy_rects: list = []
        self.choice_rects: list = []
        self.end_turn_rect = pygame.Rect(0, 0, 0, 0)
        self.draw_pile_rect = pygame.Rect(0, 0, 0, 0)
        self.discard_pile_rect = pygame.Rect(0, 0, 0, 0)
        self.exhaust_pile_rect = pygame.Rect(0, 0, 0, 0)
        self.browser = None
        self.hovered_card_idx = None
        self.deck_button_rect = pygame.Rect(0,0,0,0)
        self.hovered_buff_tooltip = None
        self.tooltip_rect = pygame.Rect(0,0,0,0)
        self.buff_rects: list = []  # [(name, stacks, rect), ...] 每帧重建，供悬停检测
        self.intent_rects: list = []  # [(summary, rect), ...] 敌人意图区域，供悬停检测
        # 地图相关
        self.map_node_rects: list = []
        self.map_skip_rect = pygame.Rect(0, 0, 0, 0)
        # 奖励相关
        self.reward_rects: list = []
        self.reward_skip_rect = pygame.Rect(0, 0, 0, 0)
        # 篝火相关
        self.campfire_rest_rect = pygame.Rect(0, 0, 0, 0)
        self.campfire_upgrade_rect = pygame.Rect(0, 0, 0, 0)
        self.campfire_upgrading = False
        # 商店相关
        self.shop_rects: list = []
        self.shop_leave_rect = pygame.Rect(0, 0, 0, 0)

    # ================================================================== #
    # 主渲染入口
    # ================================================================== #
    def blit_emoji_text(self, surface, text, pos, font, color):
        if self.emoji_font is None:
            surface.blit(font.render(text, True, color), pos)
            return
        x, y = pos
        for ch in text:
            try:
                if _is_emoji_char(ch):
                    surf = self.emoji_font.render(ch, True, color)
                else:
                    surf = font.render(ch, True, color)
                if surf.get_width() > 0:
                    surface.blit(surf, (x, y))
                    x += surf.get_width()
            except:
                pass

    def _render_top_bar(self, game):
        pygame.draw.rect(self.screen, COLOR_TOP_BAR, (0, 0, WINDOW_WIDTH, TOP_BAR_HEIGHT))
        p = game.player
        # HP 进度条：左侧保留心形图标，进度条正中间居中显示 75/75
        bar_x, bar_y, bar_w, bar_h = 50, 10, 220, 30
        # 心形图标
        self.blit_emoji_text(self.screen, "❤️", (15, 12), self.font, COLOR_TEXT)
        # 进度条背景
        pygame.draw.rect(self.screen, (60, 20, 20), (bar_x, bar_y, bar_w, bar_h), border_radius=6)
        # 进度条前景（按 HP 比例）
        ratio = p.current_hp / p.max_hp if p.max_hp > 0 else 0
        fill_w = int(bar_w * ratio)
        if fill_w > 0:
            pygame.draw.rect(self.screen, (200, 50, 50), (bar_x, bar_y, fill_w, bar_h), border_radius=6)
        # 进度条边框
        pygame.draw.rect(self.screen, (100, 30, 30), (bar_x, bar_y, bar_w, bar_h), 2, border_radius=6)
        # 进度条正中间居中显示 75/75
        hp_text = f"{p.current_hp}/{p.max_hp}"
        hp_surf = self.font.render(hp_text, True, COLOR_TEXT)
        self.screen.blit(hp_surf, (bar_x + (bar_w - hp_surf.get_width()) // 2,
                                   bar_y + (bar_h - hp_surf.get_height()) // 2))
        # 金币：💰 99（去掉"金币:"）
        gold_text = f"💰 {game.gold}"
        self.blit_emoji_text(self.screen, gold_text, (290, 15), self.font, COLOR_GOLD)
        # 卡组按钮移至右上角
        dt = f"📇卡组({p.deck_pile_size()})"
        ds = self.font.render(dt, True, COLOR_TEXT)
        deck_btn_w = ds.get_width() + 20
        deck_btn_x = WINDOW_WIDTH - deck_btn_w - 15
        self.deck_button_rect = pygame.Rect(deck_btn_x, 10, deck_btn_w, 30)
        pygame.draw.rect(self.screen, COLOR_PILE_BUTTON, self.deck_button_rect, border_radius=6)
        self.blit_emoji_text(self.screen, dt, (deck_btn_x + 10, 15), self.font, COLOR_TEXT)

    def handle_mousemotion(self, game, pos):
        self.hovered_buff_tooltip = None
        # 优先检测 buff 悬停（buff 区域可能高于卡牌，避免误触）
        for name, stacks, rect in self.buff_rects:
            if rect.collidepoint(pos):
                tip_gen = BUFF_TOOLTIPS.get(name)
                if tip_gen is not None:
                    self.hovered_buff_tooltip = tip_gen(stacks)
                else:
                    self.hovered_buff_tooltip = f"{name}：{stacks} 层"
                return
        # 检测敌人意图悬停
        for summary, rect in self.intent_rects:
            if rect.collidepoint(pos):
                self.hovered_buff_tooltip = self._intent_tooltip(summary)
                return
        if game.state == GameState.BATTLE and game.battle:
            for item in reversed(self.card_rects):
                idx, rect = item
                if rect.collidepoint(pos):
                    self.hovered_card_idx = idx
                    return
            self.hovered_card_idx = None

    def _intent_tooltip(self, summary):
        """根据意图 summary 文本生成悬停提示。"""
        if "攻击" in summary:
            import re
            m = re.search(r"\d+", summary)
            num = m.group(0) if m else "?"
            return f"攻击：下回合造成 {num} 点伤害"
        if "防御" in summary:
            return "防御：下回合获得格挡"
        if "强化" in summary:
            return "强化：增益自身（如获得力量等）"
        if "削弱" in summary:
            return "削弱：对你施加负面状态（如易伤、虚弱等）"
        if "塞牌" in summary:
            return "塞牌：向你的抽牌堆塞入状态牌"
        return summary

    def _render_tooltip(self, text):
        surf = self.font_small.render(text, True, COLOR_TEXT)
        w, h = surf.get_width() + 16, surf.get_height() + 10
        mx, my = pygame.mouse.get_pos()
        x, y = min(mx + 15, WINDOW_WIDTH - w), min(my + 15, WINDOW_HEIGHT - h)
        ov = pygame.Surface((w, h), pygame.SRCALPHA)
        ov.fill(COLOR_TOOLTIP_BG)
        pygame.draw.rect(ov, (200,200,200), (0,0,w,h), 1, border_radius=4)
        self.screen.blit(ov, (x, y))
        self.screen.blit(surf, (x + 8, y + 5))

    def render(self, game: "GameController") -> None:
        """根据游戏状态分发渲染（不调用 flip，由 main.py 统一 flip）。"""
        self.screen.fill(COLOR_BG)
        self._render_top_bar(game)
        if game.state == GameState.MAP:
            self._render_map(game)
        elif game.state == GameState.BATTLE:
            self._render_battle(game)
        elif game.state == GameState.REWARD:
            self._render_reward(game)
        elif game.state == GameState.CAMPFIRE:
            self._render_campfire(game)
        elif game.state == GameState.SHOP:
            self._render_shop(game)
        elif game.state == GameState.TREASURE:
            self._render_treasure(game)
        elif game.state == GameState.EVENT:
            self._render_event(game)
        elif game.state == GameState.GAME_OVER:
            self._render_game_over(game)
        self._render_message(game.message)
        if self.hovered_buff_tooltip:
            self._render_tooltip(self.hovered_buff_tooltip)
        if self.browser is not None:
            self.browser.render(self.screen, self.font, self.font_small, self.font_big)

    # ================================================================== #
    # 点击处理入口
    # ================================================================== #

    def handle_click(self, game: "GameController", pos) -> bool:
        """根据游戏状态分发点击处理。返回 True 表示需要退出。"""
        if self.browser is not None:
            self._handle_browser_click(game, pos)
            return False
        # 牌组按钮（全局可见，优先检测）
        if self.deck_button_rect.collidepoint(pos):
            self.browser = CardBrowser(list(game.player.deck_pile), "牌组（查看）", selectable=False)
            return False
        if game.state == GameState.MAP:
            self._handle_map_click(game, pos)
        elif game.state == GameState.BATTLE:
            self._handle_battle_click(game, pos)
        elif game.state == GameState.REWARD:
            self._handle_reward_click(game, pos)
        elif game.state == GameState.CAMPFIRE:
            self._handle_campfire_click(game, pos)
        elif game.state == GameState.SHOP:
            self._handle_shop_click(game, pos)
        elif game.state == GameState.TREASURE:
            game.confirm_treasure()
        elif game.state == GameState.EVENT:
            self._handle_event_click(game, pos)
        elif game.state == GameState.GAME_OVER:
            return True
        return False

    # ================================================================== #
    # 地图渲染
    # ================================================================== #
    def _render_map(self, game: "GameController") -> None:
        self.map_node_rects = []
        map_state = game.game_map.get_state()
        nodes = map_state["nodes"]
        num_layers = map_state["num_layers"]
        current_id = map_state["current_node_id"]
        accessible_ids = {n.node_id for n in map_state["accessible_nodes"]}

        layer_height = 100
        margin_top = 80
        margin_left = 80
        margin_right = 80

        # 按层分组
        layers: dict[int, list] = {}
        for n in nodes:
            layers.setdefault(n.layer, []).append(n)
        for layer_idx in sorted(layers.keys()):
            layers[layer_idx].sort(key=lambda n: n.position)

        # 预计算每层节点位置
        node_positions: dict[str, tuple[int, int]] = {}
        for layer_idx in range(num_layers):
            layer_nodes = layers.get(layer_idx, [])
            count = len(layer_nodes)
            if count == 0:
                continue
            usable_w = WINDOW_WIDTH - margin_left - margin_right
            for i, node in enumerate(layer_nodes):
                x = margin_left + usable_w * (i + 0.5) / count
                y = margin_top + layer_idx * layer_height
                node_positions[node.node_id] = (int(x), y)

        # 绘制连线
        for n in nodes:
            if n.node_id in node_positions:
                x1, y1 = node_positions[n.node_id]
                for conn_id in n.connections:
                    if conn_id in node_positions:
                        x2, y2 = node_positions[conn_id]
                        pygame.draw.line(self.screen, COLOR_MAP_LINE, (x1, y1 + 25), (x2, y2 - 25), 2)

        # 绘制节点
        for n in nodes:
            if n.node_id not in node_positions:
                continue
            x, y = node_positions[n.node_id]
            rect = pygame.Rect(x - 35, y - 25, 70, 50)
            self.map_node_rects.append((n.node_id, rect))

            if n.visited:
                color = COLOR_DEAD
            elif n.node_id in accessible_ids:
                color = COLOR_MAP_NODE_ACCESSIBLE
            else:
                color = COLOR_MAP_NODE
            pygame.draw.rect(self.screen, color, rect, border_radius=8)

            # 图标
            icon = n.display_icon
            self.blit_emoji_text(self.screen, icon, (x - 15, y - 12), self.font, COLOR_TEXT)

        # 图例
        self.blit_emoji_text(self.screen, "⚔️战斗  👑精英  🔥篝火  🏪商店  📦宝箱  ❓事件  🐉Boss", (20, WINDOW_HEIGHT - 30), self.font_small, COLOR_TEXT_DIM)

    def _handle_map_click(self, game: "GameController", pos) -> None:
        for node_id, rect in self.map_node_rects:
            if rect.collidepoint(pos):
                game.select_map_node(node_id)
                return

    # ================================================================== #
    # 战斗渲染
    # ================================================================== #
    def _render_battle(self, game: "GameController") -> None:
        battle = game.battle
        if battle is None:
            return
        self.buff_rects = []  # 每帧重建，供 handle_mousemotion 悬停检测
        self.intent_rects = []  # 每帧重建，供敌人意图悬停检测
        state = battle.get_state()
        self._render_player_info(state["player"])
        self._render_enemies(state["enemies"], state["enemy_summaries"])
        self._render_hand(state["player"], battle)
        self._render_pile_buttons(state["player"])
        self._render_battle_log(state.get("battle_log", []))
        if state["selected_card_idx"] is not None:
            self._render_target_hint(state["enemies"])
        self._render_end_turn_button(state["state"])
        pending = state.get("pending_action")
        if pending is not None and self.browser is None:
            self._create_browser_for_pending(pending, state["player"])
        if battle.is_over():
            self._render_battle_end_screen(battle)

    def _handle_battle_click(self, game: "GameController", pos) -> None:
        battle = game.battle
        if battle is None:
            return
        if battle.is_over():
            game.on_battle_end()
            return
        if battle.state != BattleState.PLAYER_TURN:
            return
        if self.draw_pile_rect.collidepoint(pos):
            self.browser = CardBrowser(list(battle.player.draw_pile), "抽牌堆（查看）", selectable=False)
            return
        if self.discard_pile_rect.collidepoint(pos):
            self.browser = CardBrowser(list(battle.player.discard_pile), "弃牌堆（查看）", selectable=False)
            return
        if self.exhaust_pile_rect.collidepoint(pos):
            self.browser = CardBrowser(list(battle.player.exhaust_pile), "消耗堆（查看）", selectable=False)
            return
        if battle.pending_action is not None:
            return
        if self.end_turn_rect.collidepoint(pos):
            battle.end_player_turn()
            return
        if battle.selected_card_idx is not None:
            for hand_idx, rect in self.card_rects:
                if rect.collidepoint(pos) and hand_idx == battle.selected_card_idx:
                    battle.selected_card_idx = None
                    battle.message = ""
                    return
            for i, rect in enumerate(self.enemy_rects):
                if rect.collidepoint(pos) and battle.enemies[i].is_alive():
                    battle.select_target(i)
                    return
            return
        for hand_idx, rect in self.card_rects:
            if rect.collidepoint(pos):
                battle.select_card(hand_idx)
                return

    def run_enemy_turn_with_delay(self, game: "GameController") -> None:
        """执行敌人回合（带延迟动画）。"""
        battle = game.battle
        if battle is None:
            return
        battle.message = "敌人行动中..."
        self.render(game)
        pygame.display.flip()
        pygame.time.delay(ENEMY_TURN_STEP_DELAY)
        battle.run_enemy_turn()
        self.render(game)
        pygame.display.flip()
        pygame.time.delay(ENEMY_TURN_STEP_DELAY)

    # ================================================================== #
    # 奖励渲染
    # ================================================================== #
    def _render_reward(self, game: "GameController") -> None:
        self.reward_rects = []
        title = self.font_big.render("✅ 战斗胜利！选择奖励", True, COLOR_TEXT)
        self.screen.blit(title, ((WINDOW_WIDTH - title.get_width()) // 2, 30))
        gold_text = self.font.render(f"💰 获得金币: +{game.reward_gold} (总计: {game.gold})", True, COLOR_GOLD)
        self.screen.blit(gold_text, ((WINDOW_WIDTH - gold_text.get_width()) // 2, 80))

        cards = game.reward_cards
        n = len(cards)
        card_w, card_h = 160, 220
        gap = 20
        total_w = n * card_w + (n - 1) * gap
        start_x = (WINDOW_WIDTH - total_w) // 2
        y = 140

        for i, card in enumerate(cards):
            x = start_x + i * (card_w + gap)
            rect = pygame.Rect(x, y, card_w, card_h)
            self.reward_rects.append(rect)
            pygame.draw.rect(self.screen, COLOR_CARD, rect, border_radius=8)
            self.blit_emoji_text(self.screen, card.name, (rect.x + 8, rect.y + 8), self.font, (40, 30, 20))
            self.blit_emoji_text(self.screen, card.get_display_cost(), (rect.x + 8, rect.y + 40), self.font_big, (40, 30, 20))
            type_emoji = CARD_TYPE_EMOJI.get(card.card_type, "")
            self.blit_emoji_text(self.screen, f"{type_emoji} {card.card_type}", (rect.x + 8, rect.y + 90), self.font_small, (80, 60, 40))
            desc = card.description
            lines = [desc[j:j + 8] for j in range(0, len(desc), 8)]
            for li, line in enumerate(lines[:4]):
                self.blit_emoji_text(self.screen, line, (rect.x + 8, rect.y + 130 + li * 18), self.font_small, (80, 60, 40))

        btn_w, btn_h = 120, 40
        self.reward_skip_rect = pygame.Rect((WINDOW_WIDTH - btn_w) // 2, y + card_h + 30, btn_w, btn_h)
        pygame.draw.rect(self.screen, COLOR_BUTTON_DIM, self.reward_skip_rect, border_radius=6)
        skip_text = self.font.render("跳过", True, COLOR_TEXT)
        self.screen.blit(skip_text, (self.reward_skip_rect.x + (btn_w - skip_text.get_width()) // 2, self.reward_skip_rect.y + 8))

    def _handle_reward_click(self, game: "GameController", pos) -> None:
        if self.reward_skip_rect.collidepoint(pos):
            game.select_reward_card(-1)
            return
        for i, rect in enumerate(self.reward_rects):
            if rect.collidepoint(pos):
                game.select_reward_card(i)
                return

    # ================================================================== #
    # 篝火渲染
    # ================================================================== #
    def _render_campfire(self, game: "GameController") -> None:
        if self.campfire_upgrading:
            self._render_campfire_upgrade(game)
            return

        title = self.font_big.render("🔥 篝火", True, COLOR_TEXT)
        self.screen.blit(title, ((WINDOW_WIDTH - title.get_width()) // 2, 60))
        hp_text = self.font.render(
            f"[HP] 当前 HP: {game.player.current_hp}/{game.player.max_hp}",
            True, COLOR_TEXT,
        )
        self.screen.blit(hp_text, ((WINDOW_WIDTH - hp_text.get_width()) // 2, 120))

        btn_w, btn_h = 220, 60
        self.campfire_rest_rect = pygame.Rect(
            (WINDOW_WIDTH - btn_w) // 2, 200, btn_w, btn_h
        )
        pygame.draw.rect(self.screen, COLOR_BUTTON, self.campfire_rest_rect, border_radius=8)
        rest_text = self.font.render(f"🛏️ 休息 (回复 {int(game.player.max_hp * 0.3)} HP)", True, COLOR_TEXT)
        self.screen.blit(rest_text, (self.campfire_rest_rect.x + (btn_w - rest_text.get_width()) // 2, self.campfire_rest_rect.y + 18))

        self.campfire_upgrade_rect = pygame.Rect(
            (WINDOW_WIDTH - btn_w) // 2, 290, btn_w, btn_h
        )
        pygame.draw.rect(self.screen, COLOR_BUTTON, self.campfire_upgrade_rect, border_radius=8)
        upgrade_text = self.font.render("⬆️ 升级一张牌", True, COLOR_TEXT)
        self.screen.blit(upgrade_text, (self.campfire_upgrade_rect.x + (btn_w - upgrade_text.get_width()) // 2, self.campfire_upgrade_rect.y + 18))

    def _render_campfire_upgrade(self, game: "GameController") -> None:
        title = self.font_big.render("⬆️ 选择要升级的牌", True, COLOR_TEXT)
        self.screen.blit(title, ((WINDOW_WIDTH - title.get_width()) // 2, 30))
        back_text = self.font_small.render("点击空白处返回", True, COLOR_TEXT_DIM)
        self.screen.blit(back_text, ((WINDOW_WIDTH - back_text.get_width()) // 2, 65))

        all_cards = list(game.player.deck_pile)
        self.choice_rects = []
        card_w, card_h = 140, 180
        gap = 10
        cols = 6
        start_x = (WINDOW_WIDTH - cols * card_w - (cols - 1) * gap) // 2
        y = 100

        for i, card in enumerate(all_cards):
            col = i % cols
            row = i // cols
            x = start_x + col * (card_w + gap)
            cy = y + row * (card_h + gap + 10)
            rect = pygame.Rect(x, cy, card_w, card_h)
            self.choice_rects.append(rect)
            color = COLOR_DEAD if card.upgraded else COLOR_CARD
            pygame.draw.rect(self.screen, color, rect, border_radius=8)
            self.blit_emoji_text(self.screen, card.name, (rect.x + 8, rect.y + 8), self.font, (40, 30, 20))
            self.blit_emoji_text(self.screen, card.get_display_cost(), (rect.x + 8, rect.y + 35), self.font_big, (40, 30, 20))
            type_emoji = CARD_TYPE_EMOJI.get(card.card_type, "")
            self.blit_emoji_text(self.screen, f"{type_emoji} {card.card_type}", (rect.x + 8, rect.y + 80), self.font_small, (80, 60, 40))
            if card.upgraded:
                self.blit_emoji_text(self.screen, "已升级", (rect.x + 8, rect.y + 100), self.font_small, (200, 50, 50))

    def _handle_campfire_click(self, game: "GameController", pos) -> None:
        if self.campfire_upgrading:
            for i, rect in enumerate(self.choice_rects):
                if rect.collidepoint(pos):
                    self.campfire_upgrading = False
                    game.campfire_upgrade(i)
                    return
            self.campfire_upgrading = False
            return
        if self.campfire_rest_rect.collidepoint(pos):
            game.campfire_rest()
        elif self.campfire_upgrade_rect.collidepoint(pos):
            self.campfire_upgrading = True

    # ================================================================== #
    # 商店渲染
    # ================================================================== #
    def _render_shop(self, game: "GameController") -> None:
        self.shop_rects = []
        self.shop_relic_rect = pygame.Rect(0, 0, 0, 0)
        self.shop_remove_rect = pygame.Rect(0, 0, 0, 0)
        title = self.font_big.render("商店", True, COLOR_TEXT)
        self.screen.blit(title, ((WINDOW_WIDTH - title.get_width()) // 2, 30))
        gold_text = self.font.render(f"金币: {game.gold}", True, COLOR_GOLD)
        self.screen.blit(gold_text, ((WINDOW_WIDTH - gold_text.get_width()) // 2, 80))

        # ── 卡牌商品 ──
        shop_cards = game.shop_cards
        n = len(shop_cards)
        card_w, card_h = 160, 240
        gap = 20
        total_w = n * card_w + (n - 1) * gap
        start_x = (WINDOW_WIDTH - total_w) // 2
        y = 130

        for i, (card, price) in enumerate(shop_cards):
            x = start_x + i * (card_w + gap)
            rect = pygame.Rect(x, y, card_w, card_h)
            self.shop_rects.append(rect)
            can_afford = game.gold >= price
            color = COLOR_SHOP_CARD if can_afford else COLOR_DEAD
            pygame.draw.rect(self.screen, color, rect, border_radius=8)
            self.blit_emoji_text(self.screen, card.name, (rect.x + 8, rect.y + 8), self.font, COLOR_TEXT)
            self.blit_emoji_text(self.screen, card.get_display_cost(), (rect.x + 8, rect.y + 40), self.font_big, COLOR_TEXT)
            type_emoji = CARD_TYPE_EMOJI.get(card.card_type, "")
            self.blit_emoji_text(self.screen, f"{type_emoji} {card.card_type}", (rect.x + 8, rect.y + 90), self.font_small, COLOR_TEXT_DIM)
            desc = card.description
            lines = [desc[j:j + 8] for j in range(0, len(desc), 8)]
            for li, line in enumerate(lines[:3]):
                self.blit_emoji_text(self.screen, line, (rect.x + 8, rect.y + 120 + li * 18), self.font_small, COLOR_TEXT_DIM)
            price_text = self.font.render(f"{price} 金币", True, COLOR_GOLD)
            self.screen.blit(price_text, (rect.x + 8, rect.y + 190))

        # ── 遗物商品 ──
        relic_y = y + card_h + 20
        if game.shop_relic is not None:
            relic = game.shop_relic
            relic_w, relic_h = 400, 70
            self.shop_relic_rect = pygame.Rect((WINDOW_WIDTH - relic_w) // 2, relic_y, relic_w, relic_h)
            can_afford = game.gold >= game.shop_relic_price
            color = COLOR_SHOP_CARD if can_afford else COLOR_DEAD
            pygame.draw.rect(self.screen, color, self.shop_relic_rect, border_radius=8)
            relic_text = self.font.render(f"遗物: {relic.name} - {relic.description}", True, COLOR_TEXT)
            self.screen.blit(relic_text, (self.shop_relic_rect.x + 12, self.shop_relic_rect.y + 8))
            price_text = self.font.render(f"{game.shop_relic_price} 金币", True, COLOR_GOLD)
            self.screen.blit(price_text, (self.shop_relic_rect.x + 12, self.shop_relic_rect.y + 38))
            relic_y += relic_h + 15

        # ── 删牌服务 ──
        self.shop_remove_rect = pygame.Rect((WINDOW_WIDTH - 400) // 2, relic_y, 400, 50)
        can_afford = game.gold >= game.shop_remove_price
        color = COLOR_BUTTON if can_afford else COLOR_DEAD
        pygame.draw.rect(self.screen, color, self.shop_remove_rect, border_radius=8)
        remove_text = self.font.render(f"删除一张牌 ({game.shop_remove_price} 金币)", True, COLOR_TEXT)
        self.screen.blit(remove_text, (self.shop_remove_rect.x + (400 - remove_text.get_width()) // 2, self.shop_remove_rect.y + 12))

        # ── 离开 ──
        btn_w, btn_h = 120, 40
        self.shop_leave_rect = pygame.Rect((WINDOW_WIDTH - btn_w) // 2, relic_y + 70, btn_w, btn_h)
        pygame.draw.rect(self.screen, COLOR_BUTTON_DIM, self.shop_leave_rect, border_radius=6)
        leave_text = self.font.render("离开", True, COLOR_TEXT)
        self.screen.blit(leave_text, (self.shop_leave_rect.x + (btn_w - leave_text.get_width()) // 2, self.shop_leave_rect.y + 8))

    def _handle_shop_click(self, game: "GameController", pos) -> None:
        if self.shop_leave_rect.collidepoint(pos):
            game.shop_leave()
            return
        if self.shop_relic_rect.collidepoint(pos) and game.shop_relic is not None:
            game.shop_buy_relic()
            return
        if self.shop_remove_rect.collidepoint(pos):
            self._handle_shop_remove(game)
            return
        for i, rect in enumerate(self.shop_rects):
            if rect.collidepoint(pos):
                game.shop_buy_card(i)
                return

    def _handle_shop_remove(self, game: "GameController") -> None:
        """打开删牌选择界面。"""
        if game.gold < game.shop_remove_price:
            return

        def _on_remove_done(card) -> None:
            idx = None
            for i, c in enumerate(game.player.deck_pile):
                if c is card:
                    idx = i
                    break
            if idx is not None:
                game.shop_remove_card(idx)

        self.browser = CardBrowser(
            list(game.player.deck_pile),
            f"选择要删除的牌 ({game.shop_remove_price} 金币)",
            selectable=True,
            on_select=_on_remove_done,
        )

    # ================================================================== #
    # 宝箱房渲染
    # ================================================================== #
    def _render_treasure(self, game: "GameController") -> None:
        title = self.font_big.render("📦 宝箱房！", True, COLOR_GOLD)
        self.screen.blit(title, ((WINDOW_WIDTH - title.get_width()) // 2, 150))

        y = 230
        gold_text = self.font.render(f"💰 获得 {game.treasure_gold} 金币！（总计: {game.gold}）", True, COLOR_GOLD)
        self.screen.blit(gold_text, ((WINDOW_WIDTH - gold_text.get_width()) // 2, y))
        y += 50

        relic = game.treasure_relic
        if relic is not None:
            relic_title = self.font_big.render(f"✨ 获得遗物：{relic.name}", True, COLOR_TEXT)
            self.screen.blit(relic_title, ((WINDOW_WIDTH - relic_title.get_width()) // 2, y))
            y += 50
            desc_lines = [relic.description[i:i+20] for i in range(0, len(relic.description), 20)]
            for li, line in enumerate(desc_lines[:4]):
                desc_surf = self.font.render(line, True, COLOR_TEXT_DIM)
                self.screen.blit(desc_surf, ((WINDOW_WIDTH - desc_surf.get_width()) // 2, y + li * 25))
        else:
            no_relic = self.font.render("（你已拥有所有遗物，获得额外金币）", True, COLOR_TEXT_DIM)
            self.screen.blit(no_relic, ((WINDOW_WIDTH - no_relic.get_width()) // 2, y))

        hint = self.font.render("点击任意处继续", True, COLOR_TEXT_DIM)
        self.screen.blit(hint, ((WINDOW_WIDTH - hint.get_width()) // 2, WINDOW_HEIGHT - 100))

    # ================================================================== #
    # 事件房渲染
    # ================================================================== #
    def _render_event(self, game: "GameController") -> None:
        # 处理事件中的卡牌选择状态
        if game.pending_delete_card or game.pending_upgrade_card:
            self._render_event_card_selection(game)
            return

        event = game.current_event
        if event is None:
            return

        title = self.font_big.render(f"❓ {event.name}", True, COLOR_TEXT)
        self.screen.blit(title, ((WINDOW_WIDTH - title.get_width()) // 2, 80))

        # 事件描述
        desc = event.description
        desc_lines = [desc[i:i+30] for i in range(0, len(desc), 30)]
        for li, line in enumerate(desc_lines[:5]):
            desc_surf = self.font.render(line, True, COLOR_TEXT_DIM)
            self.screen.blit(desc_surf, ((WINDOW_WIDTH - desc_surf.get_width()) // 2, 150 + li * 28))

        # 选项按钮
        available_options = event.get_available_options(game)
        self.event_option_rects = []
        btn_w, btn_h = 400, 50
        start_y = 350
        gap = 15
        for i, opt in enumerate(available_options):
            y = start_y + i * (btn_h + gap)
            rect = pygame.Rect((WINDOW_WIDTH - btn_w) // 2, y, btn_w, btn_h)
            self.event_option_rects.append(rect)
            pygame.draw.rect(self.screen, COLOR_BUTTON, rect, border_radius=8)
            opt_text = self.font.render(opt.text, True, COLOR_TEXT)
            self.screen.blit(opt_text, (rect.x + (btn_w - opt_text.get_width()) // 2, rect.y + 12))

    def _render_event_card_selection(self, game: "GameController") -> None:
        """事件中的卡牌选择界面（删除/升级）。"""
        if game.pending_delete_card:
            title = self.font_big.render("🗑️ 选择要删除的牌", True, COLOR_TEXT)
        else:
            title = self.font_big.render("⬆️ 选择要升级的牌", True, COLOR_TEXT)
        self.screen.blit(title, ((WINDOW_WIDTH - title.get_width()) // 2, 30))
        back_text = self.font_small.render("点击空白处取消", True, COLOR_TEXT_DIM)
        self.screen.blit(back_text, ((WINDOW_WIDTH - back_text.get_width()) // 2, 65))

        all_cards = list(game.player.deck_pile)
        self.choice_rects = []
        card_w, card_h = 140, 180
        gap = 10
        cols = 6
        start_x = (WINDOW_WIDTH - cols * card_w - (cols - 1) * gap) // 2
        y = 100
        for i, card in enumerate(all_cards):
            col = i % cols
            row = i // cols
            x = start_x + col * (card_w + gap)
            cy = y + row * (card_h + gap + 10)
            rect = pygame.Rect(x, cy, card_w, card_h)
            self.choice_rects.append(rect)
            color = COLOR_DEAD if (game.pending_upgrade_card and card.upgraded) else COLOR_CARD
            pygame.draw.rect(self.screen, color, rect, border_radius=8)
            self.blit_emoji_text(self.screen, card.name, (rect.x + 8, rect.y + 8), self.font, (40, 30, 20))
            self.blit_emoji_text(self.screen, card.get_display_cost(), (rect.x + 8, rect.y + 35), self.font_big, (40, 30, 20))
            type_emoji = CARD_TYPE_EMOJI.get(card.card_type, "")
            self.blit_emoji_text(self.screen, f"{type_emoji} {card.card_type}", (rect.x + 8, rect.y + 80), self.font_small, (80, 60, 40))
            if game.pending_upgrade_card and card.upgraded:
                self.blit_emoji_text(self.screen, "已升级", (rect.x + 8, rect.y + 100), self.font_small, (200, 50, 50))

    def _handle_event_click(self, game: "GameController", pos) -> None:
        # 卡牌选择状态
        if game.pending_delete_card or game.pending_upgrade_card:
            for i, rect in enumerate(self.choice_rects):
                if rect.collidepoint(pos):
                    game.confirm_event_card_action(i)
                    return
            # 点击空白处取消
            game.confirm_event_card_action(-1)
            return

        # 选项按钮
        for i, rect in enumerate(getattr(self, 'event_option_rects', [])):
            if rect.collidepoint(pos):
                game.select_event_option(i)
                return

    # ================================================================== #
    # 游戏结束
    # ================================================================== #
    def _render_game_over(self, game: "GameController") -> None:
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        player = game.player
        is_win = "通关" in game.message or "恭喜" in game.message

        if is_win:
            title, title_color = "🏆 游戏通关！", (100, 255, 100)
        else:
            title, title_color = "💀 游戏结束", (255, 100, 100)

        # 标题
        surf = self.font_big.render(title, True, title_color)
        x = (WINDOW_WIDTH - surf.get_width()) // 2
        y = 120
        self.screen.blit(surf, (x, y))

        # 结算面板
        panel_x = 300
        panel_y = 200
        panel_w = 680
        panel_h = 400
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((20, 20, 35, 220))
        pygame.draw.rect(panel, (80, 80, 100), panel.get_rect(), 2)
        self.screen.blit(panel, (panel_x, panel_y))

        # 分数计算
        hp_score = player.current_hp * 2
        gold_score = game.gold
        kill_score = player.total_kills * 5
        floor_score = player.floors_cleared * 10
        relic_score = len(player.relics) * 15
        deck_score = max(0, (30 - len(player.deck_pile))) * 3
        total_score = hp_score + gold_score + kill_score + floor_score + relic_score + deck_score
        if is_win:
            total_score += 100

        stats = [
            ("📊 结算统计", "", True),
            ("", "", False),
            (f"当前 HP: {player.current_hp}/{player.max_hp}", f"+{hp_score} 分", False),
            (f"金币: {game.gold}", f"+{gold_score} 分", False),
            (f"击杀数: {player.total_kills}", f"+{kill_score} 分", False),
            (f"已清理楼层: {player.floors_cleared}", f"+{floor_score} 分", False),
            (f"遗物数量: {len(player.relics)}", f"+{relic_score} 分", False),
            (f"牌组大小: {len(player.deck_pile)}", f"+{deck_score} 分", False),
        ]
        if is_win:
            stats.append(("通关奖励", "+100 分", False))
        stats.append(("", "", False))
        stats.append((f"总分: {total_score}", "", True))

        line_y = 15
        for label, value, is_header in stats:
            if is_header:
                text_surf = self.font_big.render(label, True, (255, 215, 0) if "总分" in label else COLOR_TEXT)
                panel.blit(text_surf, ((panel_w - text_surf.get_width()) // 2, line_y))
            else:
                label_surf = self.font.render(label, True, COLOR_TEXT)
                panel.blit(label_surf, (30, line_y))
                if value:
                    val_surf = self.font.render(value, True, (180, 180, 100))
                    panel.blit(val_surf, (panel_w - val_surf.get_width() - 30, line_y))
            line_y += 32

        hint = self.font.render("点击任意处继续", True, (180, 180, 180))
        self.screen.blit(hint, ((WINDOW_WIDTH - hint.get_width()) // 2, panel_y + panel_h + 15))

    # ================================================================== #
    # 战斗辅助渲染
    # ================================================================== #
    def _render_player_info(self, player):
        y = 60  # 下移到顶部状态栏下方，避免遮挡
        self.blit_emoji_text(self.screen, player.name, (20, y), self.font, COLOR_TEXT)  # font_big -> font，字体稍小
        y += 30
        # 移除 HP 文本（顶部已有进度条），护甲和能量加图标
        self.blit_emoji_text(
            self.screen,
            f"🛡️护甲:{player.block}  ⚡能量:{player.current_energy}/{player.max_energy}",
            (20, y), self.font, COLOR_TEXT,
        )
        y += 30
        bx = 20
        for name, stacks in player.buffs.items():
            if name in ("力量","敏捷") and stacks == 0: continue
            emoji = BUFF_EMOJI.get(name, "[?]")
            text = f"{emoji}{stacks}"  # 统一图标+层数，层数为1也显示
            self.blit_emoji_text(self.screen, text, (bx, y), self.font_small, COLOR_TEXT_DIM)
            bw = self.font_small.size(text)[0]
            # 记录 buff 区域，供 handle_mousemotion 悬停检测
            self.buff_rects.append((name, stacks, pygame.Rect(bx, y, bw, 20)))
            bx += bw + 8

    def _render_enemies(self, enemies, summaries):
        self.enemy_rects = []
        n = len(enemies)
        slot_w = 220
        total_w = n * slot_w
        start_x = (WINDOW_WIDTH - total_w) // 2 - 100
        y = 180
        for i, enemy in enumerate(enemies):
            x = start_x + i * slot_w
            rect = pygame.Rect(x, y, slot_w - 20, 200)
            self.enemy_rects.append(rect)
            c = COLOR_DEAD if not enemy.is_alive() else COLOR_ENEMY
            pygame.draw.rect(self.screen, c, rect, border_radius=10)
            emoji = ENEMY_EMOJI.get(enemy.name, "[?]")
            self.blit_emoji_text(self.screen, f"{emoji} {enemy.name}", (rect.x + 10, rect.y + 10), self.font, COLOR_TEXT)
            self.blit_emoji_text(self.screen, f"HP:{enemy.current_hp}/{enemy.max_hp}", (rect.x + 10, rect.y + 40), self.font, COLOR_TEXT)
            self.blit_emoji_text(self.screen, f"护甲:{enemy.block}", (rect.x + 10, rect.y + 70), self.font_small, COLOR_TEXT)
            bx2 = rect.x + 10
            for name, stacks in enemy.buffs.items():
                if name in ("力量","敏捷") and stacks == 0: continue
                be = BUFF_EMOJI.get(name, "[?]")
                bt = f"{be}{stacks}"  # 统一图标+层数，层数为1也显示
                self.blit_emoji_text(self.screen, bt, (bx2, rect.y + 95), self.font_small, COLOR_TEXT_DIM)
                bw2 = self.font_small.size(bt)[0]
                # 记录 buff 区域，供 handle_mousemotion 悬停检测
                self.buff_rects.append((name, stacks, pygame.Rect(bx2, rect.y + 95, bw2, 20)))
                bx2 += bw2 + 12
            if enemy.is_alive() and summaries[i]:
                it = " ".join(self._intent_to_emoji(s) for s in summaries[i])
                intent_x, intent_y = rect.x + 10, rect.y + 205
                self.blit_emoji_text(self.screen, it, (intent_x, intent_y), self.font, COLOR_TEXT)
                # 记录意图区域，供 handle_mousemotion 悬停检测
                intent_w = self.font.size(it)[0]
                self.intent_rects.append((" ".join(summaries[i]), pygame.Rect(intent_x, intent_y, intent_w, 24)))

    def _intent_to_emoji(self, summary):
        if "攻击" in summary:
            import re
            m = re.search(r"\d+", summary)
            num = m.group(0) if m else "?"
            return f"🗡️{num}"
        if "防御" in summary: return "🛡️"
        if "强化" in summary: return "💪"
        if "削弱" in summary: return "⬇️"
        if "塞牌" in summary: return "📥"
        return summary

    def _render_hand(self, player, battle=None):
        self.card_rects = []
        n = len(player.hand)
        if n == 0:
            return
        card_w = 140
        card_h = 180
        max_gap = 10
        margin = 20
        available_w = WINDOW_WIDTH - 2 * margin
        if n <= 1:
            spacing = 0
        else:
            spacing = (available_w - card_w) // (n - 1)
        spacing = min(spacing, card_w + max_gap)
        spacing = max(spacing, 30)
        total_w = card_w + (n - 1) * spacing
        start_x = (WINDOW_WIDTH - total_w) // 2
        y = WINDOW_HEIGHT - card_h - 40
        draw_order = list(range(n))
        if self.hovered_card_idx is not None and 0 <= self.hovered_card_idx < n:
            draw_order.remove(self.hovered_card_idx)
            draw_order.append(self.hovered_card_idx)
        for i in draw_order:
            card = player.hand[i]
            x = start_x + i * spacing
            offset_y = 0
            if battle and battle.selected_card_idx == i:
                offset_y = -30
            elif self.hovered_card_idx == i:
                offset_y = 0
            rect = pygame.Rect(x, y + offset_y, card_w, card_h)
            self.card_rects.append((i, rect))
            can_play = card.playable
            if can_play and not card.is_x_cost and battle:
                can_play = battle.player.can_afford(card.cost)
            color = COLOR_CARD if can_play else COLOR_CARD_DISABLED
            pygame.draw.rect(self.screen, color, rect, border_radius=8)
            if self.hovered_card_idx == i:
                pygame.draw.rect(self.screen, (255, 255, 100), rect, 3, border_radius=8)
            cost_text = card.get_display_cost()
            self.blit_emoji_text(self.screen, card.name, (rect.x + 8, rect.y + 8), self.font, (40, 30, 20))
            self.blit_emoji_text(self.screen, cost_text, (rect.x + 8, rect.y + 35), self.font_big, (40, 30, 20))
            type_emoji = CARD_TYPE_EMOJI.get(card.card_type, "")
            self.blit_emoji_text(self.screen, f"{type_emoji} {card.card_type}", (rect.x + 8, rect.y + 80), self.font_small, (80, 60, 40))
            tags = []
            if card.exhausts:
                tags.append("消耗")
            if card.ethereal:
                tags.append("虚无")
            if card.auto_play_end_of_turn:
                tags.append("自动")
            if tags:
                self.blit_emoji_text(self.screen, "/".join(tags), (rect.x + 8, rect.y + 100), self.font_small, (200, 50, 50))
            desc = card.description
            lines = [desc[j:j + 8] for j in range(0, len(desc), 8)]
            for li, line in enumerate(lines[:4]):
                self.blit_emoji_text(self.screen, line, (rect.x + 8, rect.y + 120 + li * 18), self.font_small, (80, 60, 40))

    def _render_pile_buttons(self, player):
        w, h = 130, 40
        x, y = 20, WINDOW_HEIGHT - 250
        self.draw_pile_rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(self.screen, COLOR_PILE_BUTTON, self.draw_pile_rect, border_radius=6)
        self.blit_emoji_text(self.screen, f"📥抽牌堆({player.draw_pile_size()})", (x + 10, y + 10), self.font_small, COLOR_TEXT)
        y += 45
        self.discard_pile_rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(self.screen, COLOR_PILE_BUTTON, self.discard_pile_rect, border_radius=6)
        self.blit_emoji_text(self.screen, f"📤弃牌堆({player.discard_pile_size()})", (x + 10, y + 10), self.font_small, COLOR_TEXT)
        y += 45
        self.exhaust_pile_rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(self.screen, COLOR_PILE_BUTTON, self.exhaust_pile_rect, border_radius=6)
        self.blit_emoji_text(self.screen, f"🗑️消耗堆({player.exhaust_pile_size()})", (x + 10, y + 10), self.font_small, COLOR_TEXT)

    def _render_battle_log(self, log):
        px, py, pw, ph = WINDOW_WIDTH - 220, TOP_BAR_HEIGHT + 70, 200, 250
        pygame.draw.rect(self.screen, COLOR_LOG_BG, (px, py, pw, ph), border_radius=6)
        self.blit_emoji_text(self.screen, "📋 战斗日志", (px + 10, py + 5), self.font_small, COLOR_TEXT_DIM)
        recent = log[-8:]
        cm = {"damage": (255, 80, 80), "block": (80, 180, 255), "buff": (200, 100, 255),
              "card": (255, 160, 60), "energy": (255, 220, 80), "separator": (120, 120, 120),
              "entity": (255, 220, 80), "normal": (240, 240, 240)}
        line_y = py + 25
        max_x = px + pw - 10
        for entry in recent:
            if isinstance(entry, str):
                segs = [(entry, "normal")]
            else:
                segs = getattr(entry, "segments", None)
                if not segs:
                    text = getattr(entry, "text", str(entry))
                    ct = getattr(entry, "color_type", "normal")
                    segs = [(text, ct)]
            # 按片段渲染
            cur_x = px + 10
            for seg_text, seg_type in segs:
                seg_color = cm.get(seg_type, COLOR_TEXT)
                seg_surf = self.font_small.render(seg_text, True, seg_color)
                if cur_x + seg_surf.get_width() > max_x:
                    line_y += 18
                    cur_x = px + 10
                self.screen.blit(seg_surf, (cur_x, line_y))
                cur_x += seg_surf.get_width()
            line_y += 18

    def _render_target_hint(self, enemies):
        for i, rect in enumerate(self.enemy_rects):
            if enemies[i].is_alive():
                pygame.draw.rect(self.screen, COLOR_TARGET_HIGHLIGHT, rect, 4, border_radius=10)

    def _create_browser_for_pending(self, pending, player):
        if isinstance(pending, PendingCardSelection):
            self.browser = CardBrowser(cards=pending.cards, prompt=pending.prompt, selectable=True)
        elif isinstance(pending, PendingCardChoice):
            self.browser = CardBrowser(cards=pending.options, prompt=pending.prompt, selectable=True)

    def _render_end_turn_button(self, state):
        w, h = 160, 50
        x = WINDOW_WIDTH - w - 20
        y = WINDOW_HEIGHT - h - 20
        self.end_turn_rect = pygame.Rect(x, y, w, h)
        c = COLOR_BUTTON if state == BattleState.PLAYER_TURN else COLOR_DEAD
        pygame.draw.rect(self.screen, c, self.end_turn_rect, border_radius=8)
        self.blit_emoji_text(self.screen, "结束回合", (x + 30, y + 12), self.font, COLOR_TEXT)

    def _render_message(self, message):
        if not message:
            return
        surf = self.font.render(message, True, COLOR_TEXT)
        self.screen.blit(surf, ((WINDOW_WIDTH - surf.get_width()) // 2, WINDOW_HEIGHT - 250))

    def _render_battle_end_screen(self, battle):
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))
        if battle.state == BattleState.VICTORY:
            text, color = "✅ 战斗胜利！", (100, 255, 100)
        else:
            text, color = "❌ 战斗失败...", (255, 100, 100)
        surf = self.font_big.render(text, True, color)
        x = (WINDOW_WIDTH - surf.get_width()) // 2
        y = (WINDOW_HEIGHT - surf.get_height()) // 2
        self.screen.blit(surf, (x, y))
        hint = self.font.render("点击任意处继续", True, COLOR_TEXT)
        self.screen.blit(hint, ((WINDOW_WIDTH - hint.get_width()) // 2, y + 50))

    def _handle_browser_click(self, game: "GameController", pos) -> None:
        battle = game.battle
        if self.browser is not None and self.browser.selectable:
            for i, rect in enumerate(self.browser.card_rects):
                if rect.collidepoint(pos) and i < len(self.browser.cards):
                    sel = self.browser.cards[i]
                    browser = self.browser
                    self.browser = None
                    # 商店删牌 / 事件等其他场景通过 on_select 回调
                    if browser.on_select is not None:
                        browser.on_select(sel)
                    else:
                        self._resolve_pending_with_card(battle, sel)
                    return
            return
        else:
            self.browser = None

    def _resolve_pending_with_card(self, battle, card):
        if battle is None:
            return
        pending = battle.pending_action
        if pending is None:
            return
        if isinstance(pending, PendingCardSelection):
            battle.resolve_pending_selection([card])
        elif isinstance(pending, PendingCardChoice):
            battle.resolve_pending_choice(card)

    # ================================================================== #
    # 辅助方法
    # ================================================================== #
    def _format_buffs(self, buffs: dict) -> str:
        """格式化 buff 字典，添加 emoji 图标。"""
        if not buffs:
            return "无"
        parts = []
        for name, stacks in buffs.items():
            emoji = BUFF_EMOJI.get(name, "[?]")
            if stacks == 1:
                parts.append(f"{emoji}{name}")
            else:
                parts.append(f"{emoji}{name}×{stacks}")
        return ", ".join(parts)