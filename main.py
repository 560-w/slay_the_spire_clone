"""
main.py — 杀戮尖塔克隆版 Phase 5 入口。

通过 GameController 驱动完整游戏流程:
地图 → 战斗 → 奖励 → 篝火 → 商店 → 地图 → ... → Boss → 通关
"""

import logging
import sys
import pygame
from src.controllers.game import GameController, GameState
from src.controllers.battle import BattleState
from src.views.pygame_view import PygameView
from src.views.console import DebugConsole

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("main")


def main():
    game = GameController()
    view = PygameView()
    console = DebugConsole()
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break

            # 调试控制台：Shift+~ 切换
            if event.type == pygame.KEYDOWN and event.key == pygame.K_BACKQUOTE:
                mods = pygame.key.get_mods()
                if mods & pygame.KMOD_SHIFT:
                    console.toggle()
                    continue

            # 控制台激活时，由控制台处理事件
            if console.active:
                if event.type == pygame.KEYDOWN:
                    console.handle_keydown(event)
                elif event.type == pygame.TEXTINPUT:
                    console.handle_text_input(event.text)
                continue

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if game.is_game_over():
                    running = False
                    break
                if view.handle_click(game, event.pos):
                    running = False
                    break

            # 需求6/10: 鼠标移动事件（悬停检测）
            if event.type == pygame.MOUSEMOTION:
                if hasattr(view,"handle_mousemotion"): view.handle_mousemotion(game, event.pos)

        if not running:
            break

        # 更新控制台战斗引用
        if game.battle is not None:
            console.battle = game.battle

        # 战斗状态特殊处理：敌人回合自动执行 & 战斗结束检测
        if game.state == GameState.BATTLE and game.battle is not None:
            battle = game.battle
            if battle.is_over():
                pass
            elif battle.state == BattleState.ENEMY_TURN:
                view.run_enemy_turn_with_delay(game)
                if battle.is_over():
                    game.on_battle_end()

        view.render(game)

        # 渲染调试控制台（覆盖在游戏界面上方）
        if console.active:
            console.render(view.screen, view.font, view.font_small)

        pygame.display.flip()
        view.clock.tick(30)

    pygame.quit()
    logger.info("游戏退出")


if __name__ == "__main__":
    main()