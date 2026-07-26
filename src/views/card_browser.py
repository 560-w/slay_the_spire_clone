"""card_browser.py: 通用卡牌浏览/选择模态窗口。

统一处理:
- 牌堆查看（抽牌堆/弃牌堆/消耗堆）：只读，点击空白关闭
- 卡牌选择（弃牌、加入手牌等）：可选，点击卡牌确认
- 三选一：同上

设计原则:
1. 纯表现层，不修改任何核心逻辑。
2. selectable 区分查看/选择模式。
3. 模态遮罩，阻断底层交互。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable, Optional

import pygame

from src.core.card import Card

logger = logging.getLogger(__name__)

# 配色
COLOR_OVERLAY = (0, 0, 0, 160)
COLOR_CARD_BG = (220, 200, 140)
COLOR_CARD_BG_UNPLAYABLE = (120, 110, 90)
COLOR_TEXT = (240, 240, 240)
COLOR_TEXT_DARK = (40, 30, 20)
COLOR_PROMPT = (255, 200, 0)
COLOR_SELECT_BORDER = (100, 200, 255)


class CardBrowser:
    """通用卡牌浏览/选择模态窗口。

    属性:
        cards: 要展示的卡牌列表。
        prompt: 顶部提示文字。
        selectable: 是否可选（True=选择模式，False=只读查看）。
        on_select: 选择回调（可选模式），参数为选中的卡牌。
        card_rects: 卡牌方块矩形列表（点击命中检测）。
    """

    def __init__(
        self,
        cards: list[Card],
        prompt: str,
        selectable: bool = False,
        on_select: Optional[Callable[[Card], None]] = None,
    ) -> None:
        self.cards: list[Card] = cards
        self.prompt: str = prompt
        self.selectable: bool = selectable
        self.on_select: Optional[Callable[[Card], None]] = on_select
        self.card_rects: list[pygame.Rect] = []

    def render(self, screen: pygame.Surface, font: pygame.font.Font,
               font_small: pygame.font.Font, font_big: pygame.font.Font) -> None:
        """渲染模态窗口。"""
        w, h = screen.get_size()
        # 遮罩
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill(COLOR_OVERLAY)
        screen.blit(overlay, (0, 0))

        # 提示文字
        prompt_surf = font_big.render(self.prompt, True, COLOR_PROMPT)
        screen.blit(prompt_surf, ((w - prompt_surf.get_width()) // 2, 60))

        # 卡牌网格排列
        self.card_rects = []
        n = len(self.cards)
        if n == 0:
            empty = font.render("（无卡牌）", True, COLOR_TEXT)
            screen.blit(empty, ((w - empty.get_width()) // 2, h // 2))
            return

        card_w, card_h = 140, 180
        gap = 15
        # 每行最多 8 张
        per_row = min(n, 8)
        rows = (n + per_row - 1) // per_row
        total_w = per_row * card_w + (per_row - 1) * gap
        start_x = (w - total_w) // 2
        start_y = (h - rows * (card_h + gap)) // 2 + 40

        for i, card in enumerate(self.cards):
            row = i // per_row
            col = i % per_row
            x = start_x + col * (card_w + gap)
            y = start_y + row * (card_h + gap)
            rect = pygame.Rect(x, y, card_w, card_h)
            self.card_rects.append(rect)

            color = COLOR_CARD_BG_UNPLAYABLE if not card.playable else COLOR_CARD_BG
            pygame.draw.rect(screen, color, rect, border_radius=8)
            if self.selectable:
                pygame.draw.rect(screen, COLOR_SELECT_BORDER, rect, 3, border_radius=8)

            # 名称
            name_surf = font.render(card.name, True, COLOR_TEXT_DARK)
            screen.blit(name_surf, (rect.x + 8, rect.y + 8))
            # 费用
            cost_surf = font_big.render(card.get_display_cost(), True, COLOR_TEXT_DARK)
            screen.blit(cost_surf, (rect.x + 8, rect.y + 35))
            # 类型
            type_surf = font_small.render(card.card_type, True, (80, 60, 40))
            screen.blit(type_surf, (rect.x + 8, rect.y + 80))
            # 描述
            desc = card.description
            lines = [desc[j:j+8] for j in range(0, len(desc), 8)]
            for li, line in enumerate(lines[:4]):
                dsurf = font_small.render(line, True, (80, 60, 40))
                screen.blit(dsurf, (rect.x + 8, rect.y + 120 + li * 18))

    def handle_click(self, pos: tuple[int, int]) -> Optional[Card]:
        """处理模态窗口内的点击。

        Returns:
            选择模式下返回选中的卡牌；查看模式下返回 None（仅关闭）。
        """
        for i, rect in enumerate(self.card_rects):
            if rect.collidepoint(pos) and i < len(self.cards):
                if self.selectable:
                    return self.cards[i]
                # 只读模式点击卡牌无效果（需点空白关闭）
                return None
        # 点击空白处：查看模式关闭，选择模式忽略
        if not self.selectable:
            return None
        return None