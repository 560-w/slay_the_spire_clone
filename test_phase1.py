# -*- coding: utf-8 -*-
"""test_phase1.py: Phase 1 骨架打印测试。

本测试脚本用于验证底层核心类（Entity、Card、Player、Enemy）的正确性。
不包含任何战斗循环，仅做实例化与功能打印测试。

运行方式:
    python test_phase1.py
"""

import logging
import sys

# 配置日志输出到控制台，便于观察结算过程
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)

# 导入核心模块
from src.core.entity import Entity
from src.core.card import Card
from src.core.player import Player
from src.core.enemy import Enemy


# ---------------------------------------------------------------- #
# 测试专用卡牌：继承 Card 并实现 play 方法
# ---------------------------------------------------------------- #
class TestAttackCard(Card):
    """测试用攻击牌：对目标造成 6 点伤害（无 buff 修正）。"""

    def __init__(self) -> None:
        super().__init__(
            name="打击",
            cost=1,
            card_type=Card.TYPE_ATTACK,
            description="造成 6 点伤害",
            needs_target=True,
        )

    def play(self, user, target=None, battle=None, x_value=0):
        """打出卡牌：对目标造成 6 点伤害。"""
        assert target is not None, "打击需要指定目标"
        target.take_damage(6)


class TestDefendCard(Card):
    """测试用技能牌：获得 5 点护甲。"""

    def __init__(self) -> None:
        super().__init__(
            name="防御",
            cost=1,
            card_type=Card.TYPE_SKILL,
            description="获得 5 点护甲",
            needs_target=False,
        )

    def play(self, user, target=None, battle=None, x_value=0):
        """打出卡牌：获得 5 点护甲。"""
        user.gain_block(5)


class TestPowerCard(Card):
    """测试用能力牌：获得力量。"""

    def __init__(self) -> None:
        super().__init__(
            name="恶魔形态",
            cost=3,
            card_type=Card.TYPE_POWER,
            description="每回合获得 3 点力量",
            needs_target=False,
        )

    def play(self, user, target=None, battle=None, x_value=0):
        """打出卡牌：添加力量 buff。"""
        user.add_buff("力量", 3)


# ---------------------------------------------------------------- #
# 测试 1: Entity 基类
# ---------------------------------------------------------------- #
def test_entity() -> None:
    """测试 Entity 的受击、护甲、治疗、buff 管理。"""
    print("\n" + "=" * 60)
    print("测试 1: Entity 基类")
    print("=" * 60)

    e = Entity("测试假人", max_hp=50)
    print("初始状态:", e)

    # 获得护甲
    e.gain_block(10)
    print("获得护甲后:", e)

    # 受击（护甲部分吸收）
    e.take_damage(8)
    print("受击 8 点后:", e)
    assert e.current_hp == 50, "护甲应完全吸收 8 点伤害"
    assert e.block == 2, "护甲应剩余 2 点"

    # 受击（穿透护甲）
    e.take_damage(15)
    print("再受击 15 点后:", e)
    assert e.current_hp == 37, "应扣 13 点血 (15-2 护甲)"
    assert e.block == 0, "护甲应为 0"

    # 治疗
    e.heal(10)
    print("治疗 10 点后:", e)
    assert e.current_hp == 47, "应恢复 10 点"

    # 治疗溢出
    e.heal(100)
    print("治疗 100 点后（溢出测试）:", e)
    assert e.current_hp == e.max_hp, "不应超过最大生命值"

    # buff 管理
    e.add_buff("力量", 3)
    e.add_buff("易伤", 2)
    print("添加 buff 后:", e)

    e.remove_buff("力量", 1)
    print("移除 1 层力量:", e)
    assert e.get_buff_stacks("力量") == 2

    e.remove_buff("力量")
    print("完全移除力量:", e)
    assert not e.has_buff("力量")

    # __repr__ 测试
    print("开发者调试表示:", repr(e))

    print("[PASS] Entity 测试全部通过！")


# ---------------------------------------------------------------- #
# 测试 2: Card 基类与测试卡牌
# ---------------------------------------------------------------- #
def test_card() -> None:
    """测试 Card 抽象基类与各类型卡牌。"""
    print("\n" + "=" * 60)
    print("测试 2: Card 基类与测试卡牌")
    print("=" * 60)

    strike = TestAttackCard()
    defend = TestDefendCard()
    demon_form = TestPowerCard()

    # 打印卡牌信息
    for card in [strike, defend, demon_form]:
        print(card)
        print(f"  攻击牌: {card.is_attack}, 技能牌: {card.is_skill}, 能力牌: {card.is_power}")
        print(f"  显示费用: {card.get_display_cost()}")
        print(f"  需要目标: {card.needs_target}")

    # 测试升级
    strike.upgrade()
    print("升级后:", strike)
    assert strike.upgraded, "应已升级"
    assert strike.cost == 0, "升级后费用应为 0"

    # 二次升级不应重复
    strike.upgrade()
    print("二次升级后:", strike)
    assert strike.cost == 0, "二次升级费用应不变"

    # 测试卡牌效果
    player = Player("铁甲战士", max_hp=75)
    enemy = Enemy("史莱姆", max_hp=20)

    print("\n打出卡牌效果测试:")
    # 防御牌
    defend.play(player)
    print(f"  打出防御后: {player}")
    assert player.block == 5, "应获得 5 点护甲"

    # 攻击牌
    print(f"  敌人初始: {enemy}")
    strike.play(player, target=enemy)
    print(f"  打出打击后: {enemy}")
    assert enemy.current_hp == 14, "应造成 6 点伤害"

    # 能力牌
    demon_form.play(player)
    print(f"  打出恶魔形态后: {player}")
    assert player.get_buff_stacks("力量") == 3, "应有 3 层力量"

    print("[PASS] Card 测试全部通过！")


# ---------------------------------------------------------------- #
# 测试 3: Player 牌堆管理
# ---------------------------------------------------------------- #
def test_player() -> None:
    """测试 Player 的牌堆管理、能量管理、遗物管理。"""
    print("\n" + "=" * 60)
    print("测试 3: Player 牌堆管理")
    print("=" * 60)

    player = Player("铁甲战士", max_hp=75, max_energy=3, max_hand_size=10)

    # 初始状态
    print("初始状态:", player)

    # 添加卡牌到抽牌堆
    for i in range(5):
        player.add_card_to_draw(TestAttackCard())
    print(f"添加 5 张攻击牌到抽牌堆: 抽牌堆={player.draw_pile_size()}")

    # 回合开始（回复能量、抽牌）
    player.start_turn()
    print(f"回合开始后: {player}")
    assert player.current_energy == player.max_energy, "应回复满能量"
    assert player.hand_size() == 5, "应抽 5 张牌"

    # 能量管理
    player.spend_energy(2)
    print(f"消耗 2 能量后: {player}")
    assert player.current_energy == 1, "应剩余 1 能量"
    assert player.can_afford(1), "应有 1 费"
    assert not player.can_afford(2), "不应有 2 费"

    # 弃牌
    if player.hand:
        card = player.hand[0]
        player.discard_card(card)
        print(f"弃置 {card.name} 后: 手牌={player.hand_size()}, 弃牌堆={player.discard_pile_size()}")

    # 回合结束（弃置所有手牌）
    player.end_turn()
    print(f"回合结束后: 手牌={player.hand_size()}, 弃牌堆={player.discard_pile_size()}")
    assert player.hand_size() == 0, "手牌应全弃置"

    # 洗牌测试：抽牌堆空，再从弃牌堆洗回
    player.start_turn()
    print(f"第二次回合开始后: 手牌={player.hand_size()}, 抽牌堆={player.draw_pile_size()}, 弃牌堆={player.discard_pile_size()}")
    assert player.hand_size() == 5, "应抽到 5 张牌（从弃牌堆洗回）"

    # 消耗测试
    if player.hand:
        card = player.hand[0]
        player.exhaust_card(card)
        print(f"消耗 {card.name} 后: 消耗堆={player.exhaust_pile_size()}")
        assert player.exhaust_pile_size() == 1, "消耗堆应有 1 张牌"

    print("[PASS] Player 测试全部通过！")


# ---------------------------------------------------------------- #
# 测试 4: Enemy 意图系统
# ---------------------------------------------------------------- #
def test_enemy() -> None:
    """测试 Enemy 的意图循环与回合执行。"""
    print("\n" + "=" * 60)
    print("测试 4: Enemy 意图系统")
    print("=" * 60)

    from src.core.intent import Intent

    enemy = Enemy("史莱姆", max_hp=30, enemy_id="slime", is_elite=False)
    player = Player("铁甲战士", max_hp=75)

    # 设置意图模式
    enemy.intent_pattern = [
        [Intent(Intent.TYPE_ATTACK, 8)],      # 回合 1: 攻击 8
        [Intent(Intent.TYPE_ATTACK, 12)],     # 回合 2: 攻击 12
    ]

    print("初始状态:", enemy)

    # 选择意图（循环）
    enemy.choose_intents()
    print(f"第 1 回合意图: {enemy.current_intents}")
    assert len(enemy.current_intents) == 1, "应有 1 个意图"
    assert enemy.current_intents[0].base_value == 8, "伤害应为 8"

    enemy.choose_intents()
    print(f"第 2 回合意图: {enemy.current_intents}")
    assert enemy.current_intents[0].base_value == 12, "伤害应为 12"

    # 循环回第 1 个
    enemy.choose_intents()
    print(f"第 3 回合意图（循环）: {enemy.current_intents}")
    assert enemy.current_intents[0].base_value == 8, "应循环回 8"

    # 敌人受击
    enemy.take_damage(10)
    print(f"受击 10 点后: {enemy}")
    assert enemy.current_hp == 20, "应剩余 20 HP"

    # 死亡检测
    enemy.take_damage(25)
    print(f"受击 25 点后: {enemy}")
    assert enemy.is_dead(), "应已死亡"
    assert not enemy.is_alive(), "应不再存活"

    print("[PASS] Enemy 测试全部通过！")


# ---------------------------------------------------------------- #
# 测试 5: 综合打印测试
# ---------------------------------------------------------------- #
def test_print() -> None:
    """综合打印测试：展示所有核心类的字符串表示。"""
    print("\n" + "=" * 60)
    print("测试 5: 综合打印测试")
    print("=" * 60)

    # 实例化
    player = Player("铁甲战士", max_hp=75, max_energy=3)
    enemy = Enemy("史莱姆", max_hp=25, enemy_id="slime")

    # 添加卡牌到玩家抽牌堆
    player.add_card_to_draw(TestAttackCard())
    player.add_card_to_draw(TestAttackCard())
    player.add_card_to_draw(TestDefendCard())
    player.add_card_to_draw(TestDefendCard())
    player.add_card_to_draw(TestPowerCard())

    # 回合开始
    player.start_turn()

    # 添加 buff
    player.add_buff("力量", 2)
    enemy.add_buff("易伤", 1)

    # 设置意图
    from src.core.intent import Intent
    enemy.intent_pattern = [[Intent(Intent.TYPE_ATTACK, 8)]]
    enemy.choose_intents()

    # 打印所有状态
    print("\n--- 战斗状态 ---")
    print(player)
    print(enemy)
    print(f"玩家手牌: {', '.join(str(c) for c in player.hand)}")
    print(f"玩家抽牌堆: {player.draw_pile_size()} 张")
    print(f"玩家弃牌堆: {player.discard_pile_size()} 张")
    print(f"玩家消耗堆: {player.exhaust_pile_size()} 张")

    # 打出卡牌
    print("\n--- 打出卡牌 ---")
    for card in player.hand[:]:
        if card.is_attack and enemy.is_alive():
            print(f"  打出 {card.name} → 目标 {enemy.name}")
            card.play(player, target=enemy)
        elif card.is_skill:
            print(f"  打出 {card.name} → 自身")
            card.play(player)
        elif card.is_power:
            print(f"  打出 {card.name} → 自身")
            card.play(player)
        player.hand.remove(card)

    print(f"\n--- 结算后 ---")
    print(player)
    print(enemy)

    print("[PASS] 综合打印测试完成！")


# ---------------------------------------------------------------- #
# 入口
# ---------------------------------------------------------------- #
if __name__ == "__main__":
    print("=" * 60)
    print("Phase 1 骨架打印测试")
    print("=" * 60)
    print("测试底层核心类: Entity, Card, Player, Enemy\n")

    # 运行所有测试
    test_entity()
    test_card()
    test_player()
    test_enemy()
    test_print()

    print("\n" + "=" * 60)
    print("[PASS] 所有 Phase 1 测试全部通过！")
    print("=" * 60)