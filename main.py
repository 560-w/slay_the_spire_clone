"""main.py: 项目入口。

Phase 1 仅作打印测试，验证基础类能正确实例化与交互。
不包含任何战斗循环（战斗循环将在后续 Phase 由控制器实现）。

运行方式:
    python main.py
"""

from __future__ import annotations

import logging
from typing import Optional

from src.core.card import Card
from src.core.enemy import Enemy
from src.core.entity import Entity
from src.core.player import Player


# ====================================================================== #
# 临时测试用卡牌子类（Phase 2+ 会迁移到 src/data/cards/ 数据层）
# ====================================================================== #
class Strike(Card):
    """打击：攻击牌，对目标造成 6 点伤害，费用 1。"""

    DAMAGE: int = 6

    def __init__(self) -> None:
        super().__init__(
            name="打击",
            cost=1,
            card_type=Card.TYPE_ATTACK,
            description=f"造成 {self.DAMAGE} 点伤害。",
        )

    def play(self, user: Entity, target: Optional[Entity] = None) -> None:
        """打出效果：对目标造成伤害。

        Args:
            user: 打出者（此处未直接使用，预留扩展如力量加成）。
            target: 目标敌人，攻击牌必须提供。

        Raises:
            AssertionError: 当 target 为 None 时触发。
        """
        assert target is not None, "[Strike] 攻击牌必须指定目标"
        logging.info("[Card] %s 打出 %s → %s", user.name, self.name, target.name)
        target.take_damage(self.DAMAGE)


class Defend(Card):
    """防御：技能牌，获得 5 点护甲，费用 1。"""

    BLOCK: int = 5

    def __init__(self) -> None:
        super().__init__(
            name="防御",
            cost=1,
            card_type=Card.TYPE_SKILL,
            description=f"获得 {self.BLOCK} 点护甲。",
        )

    def play(self, user: Entity, target: Optional[Entity] = None) -> None:
        """打出效果：使用者获得护甲。"""
        logging.info("[Card] %s 打出 %s", user.name, self.name)
        user.gain_block(self.BLOCK)


# ====================================================================== #
# 主函数：打印测试
# ====================================================================== #
def setup_logging() -> None:
    """配置日志：INFO 级别，输出到控制台，格式含时间与模块。"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-5s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )


def main() -> None:
    """Phase 1 打印测试入口。"""
    setup_logging()
    logger = logging.getLogger("main")

    print("=" * 60)
    print("《杀戮尖塔》克隆版 - Phase 1 骨架测试")
    print("=" * 60)

    # ----- 实例化玩家与敌人 -----
    player = Player(name="铁甲战士", max_hp=75, max_energy=3)
    enemy = Enemy(name="酸液史莱姆", max_hp=42, enemy_id="acid_slime")

    print("\n【初始状态】")
    print(f"  玩家: {player}")
    print(f"  敌人: {enemy}")

    # ----- 组建初始牌组并洗入抽牌堆 -----
    print("\n【组建初始牌组（5 张打击 + 5 张防御）】")
    starter_deck: list[Card] = [Strike() for _ in range(5)] + [Defend() for _ in range(5)]
    for card in starter_deck:
        player.add_card_to_draw(card)
    print(f"  抽牌堆数量: {player.draw_pile_size()}")

    # ----- 演示回合开始：回复能量 + 抽 5 张牌 -----
    print("\n【回合开始：回复能量并抽 5 张牌】")
    player.start_turn()
    print(f"  玩家: {player}")
    print("  当前手牌:")
    for idx, card in enumerate(player.hand, start=1):
        print(f"    {idx}. {card}")

    # ----- 演示打出一张防御牌获得护甲 -----
    print("\n【演示打出一张防御牌】")
    defend_card = next((c for c in player.hand if c.name == "防御"), None)
    if defend_card is not None:
        player.spend_energy(defend_card.cost)   # 先扣能量
        defend_card.play(user=player)            # 再结算效果
        player.discard_card(defend_card)         # 最后弃置
        print(f"  玩家: {player}")

    # ----- 演示打出一张打击牌攻击敌人 -----
    print("\n【演示打出一张打击牌攻击敌人】")
    strike_card = next((c for c in player.hand if c.name == "打击"), None)
    if strike_card is not None:
        player.spend_energy(strike_card.cost)
        strike_card.play(user=player, target=enemy)
        player.discard_card(strike_card)
        print(f"  玩家: {player}")
        print(f"  敌人: {enemy}")

    # ----- 演示敌人受击后获得 buff -----
    print("\n【演示敌人获得「虚弱」buff】")
    enemy.add_buff("虚弱", 2)
    print(f"  敌人: {enemy}")

    # ----- 演示敌人设置意图 -----
    print("\n【演示敌人设置攻击意图】")
    enemy.set_intent(Enemy.INTENT_ATTACK, value=8)
    print(f"  敌人: {enemy}")

    # ----- 演示回合结束：弃置所有手牌 -----
    print("\n【回合结束：弃置所有手牌】")
    player.end_turn()
    print(f"  玩家: {player}")
    print(f"  手牌:{player.hand_size()} 抽牌堆:{player.draw_pile_size()} "
          f"弃牌堆:{player.discard_pile_size()} 消耗堆:{player.exhaust_pile_size()}")

    print("\n" + "=" * 60)
    print("Phase 1 骨架测试完成（无战斗循环）。")
    print("=" * 60)
    logger.info("测试结束")


if __name__ == "__main__":
    main()