"""main.py: 项目入口（战斗循环 + 调试控制台）。"""

from __future__ import annotations
import logging
import pygame

from src.controllers.battle import BattleController, BattleState
from src.core.player import Player
from src.data.cards import create_test_deck_with_new_cards as create_starter_deck
from src.data.enemies import create_test_enemies
from src.views.pygame_view import PygameView
from src.views.console import DebugConsole


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-5s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )


def main():
    setup_logging()
    logger = logging.getLogger("main")

    player = Player(name="铁甲战士", max_hp=75, max_energy=3)
    for card in create_starter_deck():
        player.add_card_to_draw(card)

    enemies = create_test_enemies()
    battle = BattleController(player=player, enemies=enemies)
    view = PygameView()
    console = DebugConsole()
    console.battle = battle
    view.console = console

    battle.start_battle()
    logger.info("[Main] 战斗开始")

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKQUOTE:  # ~ 键切换
                    console.toggle()
                elif console.active:
                    # 控制台激活时只处理特殊键（回车/退格/ESC）
                    if event.key in (pygame.K_RETURN, pygame.K_BACKSPACE, pygame.K_ESCAPE):
                        console.handle_keydown(event)
            elif event.type == pygame.TEXTINPUT and console.active:
                # 控制台激活时用 TEXTINPUT 事件处理字符输入
                console.handle_text_input(event.text)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if battle.is_over():
                    running = False
                elif not console.active:
                    view.handle_click(battle, event.pos)

        if not console.active and battle.state == BattleState.ENEMY_TURN:
            view.run_enemy_turn_with_delay(battle)

        view.render(battle)
        view.clock.tick(30)

    pygame.quit()


if __name__ == "__main__":
    main()