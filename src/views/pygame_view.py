"""pygame_view.py: pygame 简易界面（表现层）。"""

from __future__ import annotations
import logging, os
from typing import TYPE_CHECKING, Optional
import pygame
from src.controllers.battle import BattleState
from src.core.pending_action import PendingCardChoice, PendingCardSelection
from src.views.card_browser import CardBrowser

if TYPE_CHECKING:
    from src.controllers.battle import BattleController

logger = logging.getLogger(__name__)
WINDOW_WIDTH=1280; WINDOW_HEIGHT=800; ENEMY_TURN_STEP_DELAY=500
COLOR_BG=(30,30,40); COLOR_ENEMY=(200,80,80); COLOR_CARD=(220,200,140)
COLOR_TEXT=(240,240,240); COLOR_TEXT_DIM=(160,160,160); COLOR_BUTTON=(80,160,80)
COLOR_TARGET_HIGHLIGHT=(255,255,0); COLOR_DEAD=(80,80,80)
COLOR_PILE_BUTTON=(100,100,140); COLOR_LOG_BG=(20,20,30)


class PygameView:
    def __init__(self):
        pygame.init()
        self.screen=pygame.display.set_mode((WINDOW_WIDTH,WINDOW_HEIGHT))
        pygame.display.set_caption("杀戮尖塔克隆版-Phase3")
        self.clock=pygame.time.Clock()
        fonts=["C:/Windows/Fonts/msyh.ttc","C:/Windows/Fonts/simhei.ttf","C:/Windows/Fonts/simsun.ttc"]
        fn=None
        for f in fonts:
            if os.path.isfile(f): fn=f; break
        if fn is None: fn=pygame.font.get_default_font()
        self.font=pygame.font.Font(fn,20); self.font_small=pygame.font.Font(fn,16); self.font_big=pygame.font.Font(fn,32)
        self.card_rects=[]; self.enemy_rects=[]; self.choice_rects=[]
        self.end_turn_rect=pygame.Rect(0,0,0,0)
        self.draw_pile_rect=pygame.Rect(0,0,0,0); self.discard_pile_rect=pygame.Rect(0,0,0,0); self.exhaust_pile_rect=pygame.Rect(0,0,0,0)
        self.browser=None
        self.console=None  # DebugConsole

    def render(self, battle):
        state=battle.get_state()
        self.screen.fill(COLOR_BG)
        self._render_player_info(state["player"])
        self._render_enemies(state["enemies"], state["enemy_summaries"])
        self._render_hand(state["player"])
        self._render_pile_buttons(state["player"])
        self._render_battle_log(state.get("battle_log",[]))
        if state["selected_card_idx"] is not None:
            self._render_target_hint(state["enemies"])
        self._render_end_turn_button(state["state"])
        self._render_message(state["message"])
        pending=state.get("pending_action")
        if pending is not None and self.browser is None:
            self._create_browser_for_pending(pending, state["player"])
        if battle.is_over(): self._render_end_screen(battle)
        if self.browser is not None:
            self.browser.render(self.screen,self.font,self.font_small,self.font_big)
        if self.console is not None:
            self.console.render(self.screen,self.font,self.font_small)
        pygame.display.flip()

    def _render_player_info(self, player):
        y=20
        self.screen.blit(self.font_big.render(player.name,True,COLOR_TEXT),(20,y)); y+=45
        self.screen.blit(self.font.render(f"HP:{player.current_hp}/{player.max_hp} 护甲:{player.block} 能量:{player.current_energy}/{player.max_energy}",True,COLOR_TEXT),(20,y)); y+=30
        bs=", ".join(f"{k}x{v}" for k,v in player.buffs.items()) or "无"
        self.screen.blit(self.font_small.render(f"Buff:{bs}",True,COLOR_TEXT_DIM),(20,y))

    def _render_enemies(self, enemies, summaries):
        self.enemy_rects=[]
        n=len(enemies); slot_w=220; total_w=n*slot_w
        start_x=(WINDOW_WIDTH-total_w)//2-100; y=180
        for i,enemy in enumerate(enemies):
            x=start_x+i*slot_w; rect=pygame.Rect(x,y,slot_w-20,200)
            self.enemy_rects.append(rect)
            c=COLOR_DEAD if not enemy.is_alive() else COLOR_ENEMY
            pygame.draw.rect(self.screen,c,rect,border_radius=10)
            self.screen.blit(self.font.render(enemy.name,True,COLOR_TEXT),(rect.x+10,rect.y+10))
            self.screen.blit(self.font.render(f"HP:{enemy.current_hp}/{enemy.max_hp}",True,COLOR_TEXT),(rect.x+10,rect.y+40))
            self.screen.blit(self.font_small.render(f"护甲:{enemy.block}",True,COLOR_TEXT),(rect.x+10,rect.y+70))
            bs=", ".join(f"{k}x{v}" for k,v in enemy.buffs.items()) or "无"
            self.screen.blit(self.font_small.render(f"Buff:{bs}",True,COLOR_TEXT_DIM),(rect.x+10,rect.y+95))
            if enemy.is_alive() and summaries[i]:
                it=" | ".join(summaries[i])
                self.screen.blit(self.font.render(f"意图:{it}",True,COLOR_TEXT),(rect.x+10,rect.y+140))

    def _render_hand(self, player):
        self.card_rects=[]
        n=len(player.hand)
        if n==0: return
        card_w=140; card_h=180; gap=10
        total_w=n*card_w+(n-1)*gap
        start_x=(WINDOW_WIDTH-total_w)//2; y=WINDOW_HEIGHT-card_h-40
        for i,card in enumerate(player.hand):
            x=start_x+i*(card_w+gap); rect=pygame.Rect(x,y,card_w,card_h)
            self.card_rects.append(rect)
            color=COLOR_DEAD if not card.playable else COLOR_CARD
            pygame.draw.rect(self.screen,color,rect,border_radius=8)
            cost_text=card.get_display_cost()
            self.screen.blit(self.font.render(card.name,True,(40,30,20)),(rect.x+8,rect.y+8))
            self.screen.blit(self.font_big.render(cost_text,True,(40,30,20)),(rect.x+8,rect.y+35))
            self.screen.blit(self.font_small.render(card.card_type,True,(80,60,40)),(rect.x+8,rect.y+80))
            tags=[]
            if card.exhausts: tags.append("消耗")
            if card.ethereal: tags.append("虚无")
            if card.auto_play_end_of_turn: tags.append("自动")
            if tags:
                self.screen.blit(self.font_small.render("/".join(tags),True,(200,50,50)),(rect.x+8,rect.y+100))
            desc=card.description
            lines=[desc[j:j+8] for j in range(0,len(desc),8)]
            for li,line in enumerate(lines[:4]):
                self.screen.blit(self.font_small.render(line,True,(80,60,40)),(rect.x+8,rect.y+120+li*18))

    def _render_pile_buttons(self, player):
        w,h=130,40; x,y=20,WINDOW_HEIGHT-250
        self.draw_pile_rect=pygame.Rect(x,y,w,h)
        pygame.draw.rect(self.screen,COLOR_PILE_BUTTON,self.draw_pile_rect,border_radius=6)
        self.screen.blit(self.font_small.render(f"抽牌堆({player.draw_pile_size()})",True,COLOR_TEXT),(x+10,y+10))
        y+=45; self.discard_pile_rect=pygame.Rect(x,y,w,h)
        pygame.draw.rect(self.screen,COLOR_PILE_BUTTON,self.discard_pile_rect,border_radius=6)
        self.screen.blit(self.font_small.render(f"弃牌堆({player.discard_pile_size()})",True,COLOR_TEXT),(x+10,y+10))
        y+=45; self.exhaust_pile_rect=pygame.Rect(x,y,w,h)
        pygame.draw.rect(self.screen,COLOR_PILE_BUTTON,self.exhaust_pile_rect,border_radius=6)
        self.screen.blit(self.font_small.render(f"消耗堆({player.exhaust_pile_size()})",True,COLOR_TEXT),(x+10,y+10))

    def _render_battle_log(self, log):
        px,py,pw,ph=WINDOW_WIDTH-220,120,200,200
        pygame.draw.rect(self.screen,COLOR_LOG_BG,(px,py,pw,ph),border_radius=6)
        self.screen.blit(self.font_small.render("战斗日志",True,COLOR_TEXT_DIM),(px+10,py+5))
        recent=log[-8:]
        for i,msg in enumerate(recent):
            self.screen.blit(self.font_small.render(msg,True,COLOR_TEXT),(px+10,py+25+i*20))

    def _render_target_hint(self, enemies):
        for i,rect in enumerate(self.enemy_rects):
            if enemies[i].is_alive():
                pygame.draw.rect(self.screen,COLOR_TARGET_HIGHLIGHT,rect,4,border_radius=10)

    def _create_browser_for_pending(self, pending, player):
        if isinstance(pending,PendingCardSelection):
            self.browser=CardBrowser(cards=pending.cards,prompt=pending.prompt,selectable=True)
        elif isinstance(pending,PendingCardChoice):
            self.browser=CardBrowser(cards=pending.options,prompt=pending.prompt,selectable=True)

    def _render_end_turn_button(self, state):
        w,h=160,50; x=WINDOW_WIDTH-w-20; y=WINDOW_HEIGHT-h-20
        self.end_turn_rect=pygame.Rect(x,y,w,h)
        c=COLOR_BUTTON if state==BattleState.PLAYER_TURN else COLOR_DEAD
        pygame.draw.rect(self.screen,c,self.end_turn_rect,border_radius=8)
        self.screen.blit(self.font.render("结束回合",True,COLOR_TEXT),(x+30,y+12))

    def _render_message(self, message):
        if not message: return
        surf=self.font.render(message,True,COLOR_TEXT)
        self.screen.blit(surf,((WINDOW_WIDTH-surf.get_width())//2,WINDOW_HEIGHT-250))

    def _render_end_screen(self, battle):
        overlay=pygame.Surface((WINDOW_WIDTH,WINDOW_HEIGHT),pygame.SRCALPHA)
        overlay.fill((0,0,0,150)); self.screen.blit(overlay,(0,0))
        if battle.state==BattleState.VICTORY: text,color="战斗胜利！",(100,255,100)
        else: text,color="战斗失败...",(255,100,100)
        surf=self.font_big.render(text,True,color)
        x=(WINDOW_WIDTH-surf.get_width())//2; y=(WINDOW_HEIGHT-surf.get_height())//2
        self.screen.blit(surf,(x,y))
        hint=self.font.render("点击任意处退出",True,COLOR_TEXT)
        self.screen.blit(hint,((WINDOW_WIDTH-hint.get_width())//2,y+50))

    def handle_click(self, battle, pos):
        if battle.is_over(): return
        if self.browser is not None:
            self._handle_browser_click(battle,pos); return
        if battle.state!=BattleState.PLAYER_TURN: return
        if self.draw_pile_rect.collidepoint(pos):
            self.browser=CardBrowser(list(battle.player.draw_pile),"抽牌堆（查看）",selectable=False); return
        if self.discard_pile_rect.collidepoint(pos):
            self.browser=CardBrowser(list(battle.player.discard_pile),"弃牌堆（查看）",selectable=False); return
        if self.exhaust_pile_rect.collidepoint(pos):
            self.browser=CardBrowser(list(battle.player.exhaust_pile),"消耗堆（查看）",selectable=False); return
        if battle.pending_action is not None: return
        if self.end_turn_rect.collidepoint(pos):
            battle.end_player_turn(); return
        if battle.selected_card_idx is not None:
            for i,rect in enumerate(self.enemy_rects):
                if rect.collidepoint(pos) and battle.enemies[i].is_alive():
                    battle.select_target(i); return
            return
        for i,rect in enumerate(self.card_rects):
            if rect.collidepoint(pos):
                battle.select_card(i); return

    def _handle_browser_click(self, battle, pos):
        if self.browser is not None and self.browser.selectable:
            for i,rect in enumerate(self.browser.card_rects):
                if rect.collidepoint(pos) and i<len(self.browser.cards):
                    sel=self.browser.cards[i]; self.browser=None
                    self._resolve_pending_with_card(battle,sel); return
            return
        else:
            self.browser=None

    def _resolve_pending_with_card(self, battle, card):
        pending=battle.pending_action
        if pending is None: return
        if isinstance(pending,PendingCardSelection):
            battle.resolve_pending_selection([card])
        elif isinstance(pending,PendingCardChoice):
            battle.resolve_pending_choice(card)

    def run_enemy_turn_with_delay(self, battle):
        battle.message="敌人行动中..."
        self.render(battle); pygame.time.delay(ENEMY_TURN_STEP_DELAY)
        battle.run_enemy_turn()
        self.render(battle); pygame.time.delay(ENEMY_TURN_STEP_DELAY)