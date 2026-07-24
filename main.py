"""main.py: 项目入口（Phase 2 战斗循环）。

启动 pygame 窗口，驱动一场完整战斗（玩家 vs 2 个史莱姆），
通过鼠标点击操作至胜利或失败。

运行方式:
    python main.py
"""

from __future__ import annotations

import logging
import sys

import pygame

from src.controllers.battle import BattleController, BattleState
from src.core.player import Player
from src.data.cards import create_starter_deck
from src.data.enemies import create_test_enemies
from src.views.pygame_view import PygameView


def setup_logging() -> None:
    """配置日志：INFO 级别，输出到控制台。"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-5s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )


def main() -> None:
    """Phase 2 战斗主循环入口。"""
    setup_logging()
    logger = logging.getLogger("main")

    # ----- 初始化玩家与牌组 -----
    player = Player(name="铁甲战士", max_hp=75, max_energy=3)
    for card in create_starter_deck():
        player.add_card_to_draw(card)

    # ----- 初始化敌人 -----
    enemies = create_test_enemies()

    # ----- 初始化战斗与视图 -----
    battle = BattleController(player=player, enemies=enemies)
    view = PygameView()

    battle.start_battle()
    logger.info("[Main] 战斗开始，进入 pygame 主循环")

    # ----- 主循环 -----
    running = True
    while running:
        # 事件处理
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # 战斗结束：任意点击退出
                if battle.is_over():
                    running = False
                else:
                    view.handle_click(battle, event.pos)

        # 敌人回合自动执行（带延迟展示）
        if battle.state == BattleState.ENEMY_TURN:
            view.run_enemy_turn_with_delay(battle)

        # 渲染
        view.render(battle)
        view.clock.tick(30)

    pygame.quit()
    logger.info("[Main] 程序退出")


if __name__ == "__main__":
    main()