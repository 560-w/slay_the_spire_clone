"""enemies.py: 具体敌人定义。

包含:
- 普通敌人：AcidSlime 酸液史莱姆, SpikeSlime 尖刺史莱姆, Cultist 邪教徒, SlimeBoss 史莱姆老大, Gremlin 地精
- 精英敌人：EliteSlime 精英史莱姆, GremlinLeader 地精头领, Chosen 被选中者
- Boss：BossSlime 史莱姆王(Act1), BronzeGuardian 青铜守护者(Act2), TimeEater 时间吞噬者(Act3)

设计原则:
1. create_enemies_for_act(act, elite, boss) 根据幕数调整 HP 和伤害倍率。
2. 意图模式在 __init__ 中设置，choose_intents 由基类按模式循环。
3. Boss 不会重复出现（不同幕不同 Boss）。
"""

from __future__ import annotations

from src.core.intent import Intent
from src.core.enemy import Enemy

from .cards import create_dazed, create_wound, create_burn


# ====================================================================== #
# 难度倍率
# ====================================================================== #
def _act_mult(act: int, base: int, elite: bool = False, boss: bool = False) -> int:
    """根据 Act 返回缩放后的数值。
    
    Act 1: 1.0x, Act 2: 1.2x, Act 3: 1.5x
    精英额外 +15%, Boss 额外 +30%
    """
    mult = {1: 1.0, 2: 1.2, 3: 1.5}[act]
    if boss:
        mult *= 1.3
    elif elite:
        mult *= 1.15
    return int(base * mult)


# ====================================================================== #
# 普通敌人
# ====================================================================== #
class AcidSlime(Enemy):
    """酸液史莱姆：普通敌人，基础 HP 42。

    意图模式（循环）:
    - 回合1: 攻击 8
    - 回合2: 攻击 8
    - 回合3: 防御 3
    """

    BASE_HP: int = 42
    BASE_ATK: int = 8
    BASE_DEF: int = 3

    def __init__(self, act: int = 1) -> None:
        hp = _act_mult(act, self.BASE_HP)
        atk = _act_mult(act, self.BASE_ATK)
        df = _act_mult(act, self.BASE_DEF)
        super().__init__(
            name="酸液史莱姆",
            max_hp=hp,
            enemy_id="acid_slime",
            is_elite=False,
        )
        self.intent_pattern = [
            [Intent(Intent.TYPE_ATTACK, base_value=atk)],
            [Intent(Intent.TYPE_ATTACK, base_value=atk)],
            [Intent(Intent.TYPE_DEFEND, base_value=df)],
        ]


class SpikeSlime(Enemy):
    """尖刺史莱姆：普通敌人，基础 HP 28。

    意图模式（循环）:
    - 回合1: 攻击 5
    - 回合2: 削弱（给玩家 2 层虚弱）
    - 回合3: 塞牌（向玩家牌堆塞入「晕眩」）
    """

    BASE_HP: int = 28
    BASE_ATK: int = 5

    def __init__(self, act: int = 1) -> None:
        hp = _act_mult(act, self.BASE_HP)
        atk = _act_mult(act, self.BASE_ATK)
        super().__init__(
            name="尖刺史莱姆",
            max_hp=hp,
            enemy_id="spike_slime",
            is_elite=False,
        )
        self.intent_pattern = [
            [Intent(Intent.TYPE_ATTACK, base_value=atk)],
            [Intent(Intent.TYPE_DEBUFF, base_value=2, buff_name="虚弱")],
            [Intent(Intent.TYPE_ADD_CARD, status_card=create_dazed())],
        ]
        # 被动：尖刺外壳 - 自带 2 层荆棘
        self.add_buff("荆棘", 2)


class Cultist(Enemy):
    """邪教徒：普通敌人，基础 HP 50。

    意图模式（循环）:
    - 回合1: 攻击 6
    - 回合2: 强化（获得 3 力量）
    - 回合3: 攻击 6
    """

    BASE_HP: int = 50
    BASE_ATK: int = 6
    BASE_BUFF: int = 3

    def __init__(self, act: int = 1) -> None:
        hp = _act_mult(act, self.BASE_HP)
        atk = _act_mult(act, self.BASE_ATK)
        buff = _act_mult(act, self.BASE_BUFF)
        super().__init__(
            name="邪教徒",
            max_hp=hp,
            enemy_id="cultist",
            is_elite=False,
        )
        self.intent_pattern = [
            [Intent(Intent.TYPE_ATTACK, base_value=atk)],
            [Intent(Intent.TYPE_BUFF, base_value=buff, buff_name="力量")],
            [Intent(Intent.TYPE_ATTACK, base_value=atk)],
        ]


class SlimeBoss(Enemy):
    """史莱姆老大：普通敌人，基础 HP 60。

    意图模式（循环）:
    - 回合1: 攻击 10
    - 回合2: 塞牌（向玩家牌堆塞入「伤口」）
    - 回合3: 攻击 10
    """

    BASE_HP: int = 60
    BASE_ATK: int = 10

    def __init__(self, act: int = 1) -> None:
        hp = _act_mult(act, self.BASE_HP)
        atk = _act_mult(act, self.BASE_ATK)
        super().__init__(
            name="史莱姆老大",
            max_hp=hp,
            enemy_id="slime_boss",
            is_elite=False,
        )
        self.intent_pattern = [
            [Intent(Intent.TYPE_ATTACK, base_value=atk)],
            [Intent(Intent.TYPE_ADD_CARD, status_card=create_wound())],
            [Intent(Intent.TYPE_ATTACK, base_value=atk)],
        ]


class Gremlin(Enemy):
    """地精：普通敌人，基础 HP 22。

    意图模式（循环）:
    - 回合1: 攻击 4
    - 回合2: 攻击 4
    - 回合3: 防御 2
    """

    BASE_HP: int = 22
    BASE_ATK: int = 4
    BASE_DEF: int = 2

    def __init__(self, act: int = 1) -> None:
        hp = _act_mult(act, self.BASE_HP)
        atk = _act_mult(act, self.BASE_ATK)
        df = _act_mult(act, self.BASE_DEF)
        super().__init__(
            name="地精",
            max_hp=hp,
            enemy_id="gremlin",
            is_elite=False,
        )
        self.intent_pattern = [
            [Intent(Intent.TYPE_ATTACK, base_value=atk)],
            [Intent(Intent.TYPE_ATTACK, base_value=atk)],
            [Intent(Intent.TYPE_DEFEND, base_value=df)],
        ]


# ====================================================================== #
# 精英敌人
# ====================================================================== #
class EliteSlime(Enemy):
    """精英史莱姆：精英敌人，基础 HP 65。

    意图模式（循环）:
    - 回合1: 攻击 12
    - 回合2: 强化（获得 2 力量）
    - 回合3: 攻击 12
    """

    BASE_HP: int = 65
    BASE_ATK: int = 12
    BASE_BUFF: int = 2

    def __init__(self, act: int = 1) -> None:
        hp = _act_mult(act, self.BASE_HP, elite=True)
        atk = _act_mult(act, self.BASE_ATK, elite=True)
        buff = _act_mult(act, self.BASE_BUFF, elite=True)
        super().__init__(
            name="精英史莱姆",
            max_hp=hp,
            enemy_id="elite_slime",
            is_elite=True,
        )
        self.intent_pattern = [
            [Intent(Intent.TYPE_ATTACK, base_value=atk)],
            [Intent(Intent.TYPE_BUFF, base_value=buff, buff_name="力量")],
            [Intent(Intent.TYPE_ATTACK, base_value=atk)],
        ]
        # 被动：精英体能 - 自带 1 层力量
        self.add_buff("力量", 1)


class GremlinLeader(Enemy):
    """地精头领：精英敌人，基础 HP 80。

    意图模式（循环）:
    - 回合1: 攻击 14
    - 回合2: 塞牌（向玩家牌堆塞入「灼伤」）
    - 回合3: 攻击 14
    - 回合4: 防御 8
    """

    BASE_HP: int = 80
    BASE_ATK: int = 14
    BASE_DEF: int = 8

    def __init__(self, act: int = 1) -> None:
        hp = _act_mult(act, self.BASE_HP, elite=True)
        atk = _act_mult(act, self.BASE_ATK, elite=True)
        df = _act_mult(act, self.BASE_DEF, elite=True)
        super().__init__(
            name="地精头领",
            max_hp=hp,
            enemy_id="gremlin_leader",
            is_elite=True,
        )
        self.intent_pattern = [
            [Intent(Intent.TYPE_ATTACK, base_value=atk)],
            [Intent(Intent.TYPE_ADD_CARD, status_card=create_burn())],
            [Intent(Intent.TYPE_ATTACK, base_value=atk)],
            [Intent(Intent.TYPE_DEFEND, base_value=df)],
        ]
        # 被动：荆棘护甲 - 自带 1 层荆棘
        self.add_buff("荆棘", 1)


class Chosen(Enemy):
    """被选中者：精英敌人，基础 HP 72。

    意图模式（循环）:
    - 回合1: 攻击 10
    - 回合2: 削弱（给玩家 3 层易伤）
    - 回合3: 攻击 10
    """

    BASE_HP: int = 72
    BASE_ATK: int = 10

    def __init__(self, act: int = 1) -> None:
        hp = _act_mult(act, self.BASE_HP, elite=True)
        atk = _act_mult(act, self.BASE_ATK, elite=True)
        super().__init__(
            name="被选中者",
            max_hp=hp,
            enemy_id="chosen",
            is_elite=True,
        )
        self.intent_pattern = [
            [Intent(Intent.TYPE_ATTACK, base_value=atk)],
            [Intent(Intent.TYPE_DEBUFF, base_value=3, buff_name="易伤")],
            [Intent(Intent.TYPE_ATTACK, base_value=atk)],
        ]


# ====================================================================== #
# Boss 敌人（每个 Act 一个，不重复）
# ====================================================================== #
class BossSlime(Enemy):
    """Boss 史莱姆王：Act 1 Boss，基础 HP 120。

    意图模式（循环）:
    - 回合1: 攻击 15
    - 回合2: 攻击 15
    - 回合3: 塞牌（向玩家牌堆塞入「伤口」）
    - 回合4: 防御 10
    """

    BASE_HP: int = 120
    BASE_ATK: int = 15
    BASE_DEF: int = 10

    def __init__(self, act: int = 1) -> None:
        hp = _act_mult(act, self.BASE_HP, boss=True)
        atk = _act_mult(act, self.BASE_ATK, boss=True)
        df = _act_mult(act, self.BASE_DEF, boss=True)
        super().__init__(
            name="史莱姆王",
            max_hp=hp,
            enemy_id="boss_slime",
            is_elite=False,
        )
        self.intent_pattern = [
            [Intent(Intent.TYPE_ATTACK, base_value=atk)],
            [Intent(Intent.TYPE_ATTACK, base_value=atk)],
            [Intent(Intent.TYPE_ADD_CARD, status_card=create_wound())],
            [Intent(Intent.TYPE_DEFEND, base_value=df)],
        ]
        # 被动：Boss 威压 - 自带 2 层力量
        self.add_buff("力量", 2)


class BronzeGuardian(Enemy):
    """青铜守护者：Act 2 Boss，基础 HP 160。

    意图模式（循环）:
    - 回合1: 攻击 20
    - 回合2: 防御 12
    - 回合3: 攻击 20
    - 回合4: 塞牌（向玩家牌堆塞入「晕眩」）
    """

    BASE_HP: int = 160
    BASE_ATK: int = 20
    BASE_DEF: int = 12

    def __init__(self, act: int = 2) -> None:
        hp = _act_mult(act, self.BASE_HP, boss=True)
        atk = _act_mult(act, self.BASE_ATK, boss=True)
        df = _act_mult(act, self.BASE_DEF, boss=True)
        super().__init__(
            name="青铜守护者",
            max_hp=hp,
            enemy_id="bronze_guardian",
            is_elite=False,
        )
        self.intent_pattern = [
            [Intent(Intent.TYPE_ATTACK, base_value=atk)],
            [Intent(Intent.TYPE_DEFEND, base_value=df)],
            [Intent(Intent.TYPE_ATTACK, base_value=atk)],
            [Intent(Intent.TYPE_ADD_CARD, status_card=create_dazed())],
        ]
        # 被动：青铜装甲 - 自带 3 层荆棘
        self.add_buff("荆棘", 3)


class TimeEater(Enemy):
    """时间吞噬者：Act 3 Boss，基础 HP 220。

    意图模式（循环）:
    - 回合1: 攻击 25
    - 回合2: 削弱（给玩家 3 层虚弱）
    - 回合3: 攻击 25
    - 回合4: 攻击 25
    - 回合5: 防御 15
    """

    BASE_HP: int = 220
    BASE_ATK: int = 25
    BASE_DEF: int = 15

    def __init__(self, act: int = 3) -> None:
        hp = _act_mult(act, self.BASE_HP, boss=True)
        atk = _act_mult(act, self.BASE_ATK, boss=True)
        df = _act_mult(act, self.BASE_DEF, boss=True)
        super().__init__(
            name="时间吞噬者",
            max_hp=hp,
            enemy_id="time_eater",
            is_elite=False,
        )
        self.intent_pattern = [
            [Intent(Intent.TYPE_ATTACK, base_value=atk)],
            [Intent(Intent.TYPE_DEBUFF, base_value=3, buff_name="虚弱")],
            [Intent(Intent.TYPE_ATTACK, base_value=atk)],
            [Intent(Intent.TYPE_ATTACK, base_value=atk)],
            [Intent(Intent.TYPE_DEFEND, base_value=df)],
        ]


# ====================================================================== #
# 敌人创建工厂函数
# ====================================================================== #
# 普通敌人池（按 Act 分组）
NORMAL_POOL_BY_ACT = {
    1: [AcidSlime, SpikeSlime, Cultist],
    2: [AcidSlime, SpikeSlime, Cultist, SlimeBoss, Gremlin],
    3: [Cultist, SlimeBoss, Gremlin, SpikeSlime],
}

# 精英敌人池
ELITE_POOL = [EliteSlime, GremlinLeader, Chosen]

# Boss 映射（每个 Act 一个，不重复）
BOSS_BY_ACT = {
    1: BossSlime,
    2: BronzeGuardian,
    3: TimeEater,
}


def create_enemies_for_act(
    act: int, elite: bool = False, boss: bool = False
) -> list[Enemy]:
    """根据 Act 创建敌人组合。

    Args:
        act: 当前幕数（1-3）。
        elite: 是否为精英战。
        boss: 是否为 Boss 战。

    Returns:
        敌人列表。
    """
    import random

    act = max(1, min(3, act))  # 钳制在 1-3

    if boss:
        boss_cls = BOSS_BY_ACT[act]
        return [boss_cls(act=act)]

    if elite:
        elite_cls = random.choice(ELITE_POOL)
        return [elite_cls(act=act)]

    # 普通战斗：随机选 1-2 个敌人
    pool = NORMAL_POOL_BY_ACT.get(act, NORMAL_POOL_BY_ACT[1])
    count = random.randint(1, 2)
    enemies = []
    for _ in range(count):
        cls = random.choice(pool)
        enemies.append(cls(act=act))
    return enemies


def create_test_enemies(
    elite: bool = False, boss: bool = False
) -> list[Enemy]:
    """创建测试用敌人组合（向后兼容，默认 Act 1）。

    Args:
        elite: 是否为精英战。
        boss: 是否为 Boss 战。

    Returns:
        敌人列表。
    """
    return create_enemies_for_act(act=1, elite=elite, boss=boss)