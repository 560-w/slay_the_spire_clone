"""enemies.py: 具体敌人定义。

包含:
- AcidSlime 酸液史莱姆：意图模式循环 [攻击8, 攻击8, 防御3]
- SpikeSlime 尖刺史莱姆：意图模式 [攻击5, 削弱(虚弱×2), 塞牌(晕眩)]

设计原则:
1. 意图模式在 __init__ 中设置，choose_intents 由基类按模式循环。
2. 每个意图用 Intent 对象封装，ADD_CARD 意图通过工厂函数创建状态牌。
3. 敌人数据驱动，便于后续扩展更多敌人类型。
"""

from __future__ import annotations

from src.core.intent import Intent
from src.core.enemy import Enemy

from .cards import create_dazed


class AcidSlime(Enemy):
    """酸液史莱姆：普通敌人，HP 42。

    意图模式（循环）:
    - 回合1: 攻击 8
    - 回合2: 攻击 8
    - 回合3: 防御 3
    """

    def __init__(self, max_hp: int = 42) -> None:
        super().__init__(
            name="酸液史莱姆",
            max_hp=max_hp,
            enemy_id="acid_slime",
            is_elite=False,
        )
        # 意图模式：三回合循环
        self.intent_pattern = [
            [Intent(Intent.TYPE_ATTACK, base_value=8)],
            [Intent(Intent.TYPE_ATTACK, base_value=8)],
            [Intent(Intent.TYPE_DEFEND, base_value=3)],
        ]


class SpikeSlime(Enemy):
    """尖刺史莱姆：普通敌人，HP 28。

    意图模式（循环）:
    - 回合1: 攻击 5
    - 回合2: 削弱（给玩家 2 层虚弱）
    - 回合3: 塞牌（向玩家牌堆塞入「晕眩」）
    """

    def __init__(self, max_hp: int = 28) -> None:
        super().__init__(
            name="尖刺史莱姆",
            max_hp=max_hp,
            enemy_id="spike_slime",
            is_elite=False,
        )
        self.intent_pattern = [
            [Intent(Intent.TYPE_ATTACK, base_value=5)],
            [Intent(Intent.TYPE_DEBUFF, base_value=2, buff_name="虚弱")],
            [Intent(Intent.TYPE_ADD_CARD, status_card=create_dazed())],
        ]


def create_test_enemies() -> list[Enemy]:
    """创建测试用敌人组合：1 酸液史莱姆 + 1 尖刺史莱姆。"""
    return [AcidSlime(), SpikeSlime()]