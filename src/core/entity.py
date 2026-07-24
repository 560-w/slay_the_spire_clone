"""entity.py: Entity 基类。

定义所有战斗实体（玩家、敌人）共有的属性与行为：
- 生命值（HP / Max_HP）
- 护甲（Block）
- 状态效果（Buff 字典）
- 受击结算、获得护甲、治疗、buff 管理

设计原则：
1. 与 UI 表现绝对解耦，纯逻辑层。
2. 关键方法使用 assert 校验入参，logging 记录结算过程，便于查错。
3. 不强制抽象（非 ABC），因为其方法已完全可复用；如需禁止直接实例化，
   子类化时改为 ABC 即可。
"""

from __future__ import annotations

import logging
from typing import Dict

# 模块级 logger：日志会带上模块名，便于定位
logger = logging.getLogger(__name__)


class Entity:
    """战斗实体基类。

    属性:
        name (str): 实体名称（如 "铁甲战士"、"史莱姆"）。
        max_hp (int): 最大生命值。
        current_hp (int): 当前生命值。
        block (int): 当前护甲值（回合开始时通常清零，由控制器负责）。
        buffs (Dict[str, int]): 状态效果字典，键为 buff 名称，值为层数。
            例: {"虚弱": 2, "易伤": 1}
    """

    def __init__(self, name: str, max_hp: int) -> None:
        """初始化一个实体。

        Args:
            name: 实体名称。
            max_hp: 最大生命值，必须为正整数。

        Raises:
            AssertionError: 当 max_hp 非正时触发。
        """
        # 防御性校验：最大生命值必须大于 0
        assert max_hp > 0, f"[Entity] max_hp 必须为正整数，收到 {max_hp}"
        assert isinstance(name, str) and name, "[Entity] name 不能为空字符串"

        self.name: str = name
        self.max_hp: int = max_hp
        self.current_hp: int = max_hp  # 初始满血
        self.block: int = 0  # 初始无护甲
        self.buffs: Dict[str, int] = {}  # 初始无 buff

        logger.debug("[Entity] 创建实体 %s (max_hp=%d)", self.name, self.max_hp)

    # ------------------------------------------------------------------ #
    # 伤害与护甲结算
    # ------------------------------------------------------------------ #
    def take_damage(self, amount: int) -> int:
        """承受伤害结算。

        结算顺序（遵循《杀戮尖塔》机制）：
        1. 先用护甲抵扣伤害。
        2. 护甲不足部分扣减生命值。
        3. 返回实际造成的生命值损失（扣血量）。

        注意: 本方法暂不处理 "易伤" 等增伤 buff 的放大效果，
              那些放大计算应在调用方（控制器）完成，传入最终伤害。
              buff 对伤害的修正将在后续 Phase 由控制器统一处理。

        Args:
            amount: 伤害数值，必须 >= 0。

        Returns:
            实际扣减的生命值（>=0）。

        Raises:
            AssertionError: 当 amount 为负时触发。
        """
        # 防御性校验
        assert amount >= 0, f"[Entity] {self.name} 受击伤害不能为负，收到 {amount}"

        # 护甲抵扣：先算被护甲吸收的部分
        blocked: int = min(self.block, amount)
        remaining: int = amount - blocked  # 穿透护甲的部分

        # 扣减护甲
        self.block -= blocked
        # 扣减生命值（不低于 0）
        hp_loss: int = min(remaining, self.current_hp)
        self.current_hp -= hp_loss

        logger.info(
            "[Entity] %s 受击: 总伤害=%d, 护甲吸收=%d, 实际扣血=%d, "
            "剩余HP=%d/%d, 剩余护甲=%d",
            self.name, amount, blocked, hp_loss,
            self.current_hp, self.max_hp, self.block,
        )

        return hp_loss

    def gain_block(self, amount: int) -> int:
        """获得护甲。

        Args:
            amount: 获得的护甲值，必须 >= 0。

        Returns:
            实际增加的护甲值（等于 amount，预留扩展接口）。

        Raises:
            AssertionError: 当 amount 为负时触发。
        """
        assert amount >= 0, f"[Entity] {self.name} 获得护甲不能为负，收到 {amount}"

        self.block += amount
        logger.info(
            "[Entity] %s 获得 %d 护甲，当前护甲=%d",
            self.name, amount, self.block,
        )
        return amount

    def lose_block(self, amount: int) -> int:
        """损失护甲（用于某些卡牌效果，如 "失去所有护甲"）。

        Args:
            amount: 损失的护甲值，必须 >= 0。

        Returns:
            实际损失的护甲值。
        """
        assert amount >= 0, f"[Entity] {self.name} 损失护甲不能为负，收到 {amount}"
        lost: int = min(amount, self.block)
        self.block -= lost
        logger.info("[Entity] %s 损失 %d 护甲，当前护甲=%d", self.name, lost, self.block)
        return lost

    # ------------------------------------------------------------------ #
    # 治疗
    # ------------------------------------------------------------------ #
    def heal(self, amount: int) -> int:
        """治疗生命值（不超过 max_hp）。

        Args:
            amount: 治疗量，必须 >= 0。

        Returns:
            实际恢复的生命值。

        Raises:
            AssertionError: 当 amount 为负时触发。
        """
        assert amount >= 0, f"[Entity] {self.name} 治疗量不能为负，收到 {amount}"

        # 已满血则不治疗
        if self.current_hp >= self.max_hp:
            logger.debug("[Entity] %s 已满血，治疗无效", self.name)
            return 0

        actual_heal: int = min(amount, self.max_hp - self.current_hp)
        self.current_hp += actual_heal
        logger.info(
            "[Entity] %s 治疗 %d，实际恢复=%d，当前HP=%d/%d",
            self.name, amount, actual_heal, self.current_hp, self.max_hp,
        )
        return actual_heal

    # ------------------------------------------------------------------ #
    # Buff 管理
    # ------------------------------------------------------------------ #
    def add_buff(self, name: str, stacks: int) -> int:
        """添加状态效果（叠加层数）。

        Args:
            name: buff 名称（如 "虚弱"、"力量"）。
            stacks: 层数，必须 >= 0。为 0 时视为不添加但仍返回当前层数。

        Returns:
            添加后该 buff 的总层数。

        Raises:
            AssertionError: 当 stacks 为负或 name 为空时触发。
        """
        assert isinstance(name, str) and name, "[Entity] buff 名称不能为空"
        assert stacks >= 0, f"[Entity] buff 层数不能为负，收到 {stacks}"

        if stacks == 0:
            return self.buffs.get(name, 0)

        self.buffs[name] = self.buffs.get(name, 0) + stacks
        logger.info(
            "[Entity] %s 获得 buff [%s] x%d，当前总层数=%d",
            self.name, name, stacks, self.buffs[name],
        )
        return self.buffs[name]

    def remove_buff(self, name: str, stacks: int | None = None) -> int:
        """移除状态效果。

        Args:
            name: buff 名称。
            stacks: 要移除的层数。None 表示全部移除。必须 >= 0。

        Returns:
            移除后该 buff 剩余层数（若无则返回 0）。

        Raises:
            AssertionError: 当 stacks 为负时触发。
        """
        if stacks is not None:
            assert stacks >= 0, f"[Entity] 移除 buff 层数不能为负，收到 {stacks}"

        if name not in self.buffs:
            logger.debug("[Entity] %s 不存在 buff [%s]，移除无效", self.name, name)
            return 0

        if stacks is None:
            removed = self.buffs.pop(name)
            logger.info("[Entity] %s 完全移除 buff [%s] (移除 %d 层)", self.name, name, removed)
            return 0

        removed = min(stacks, self.buffs[name])
        self.buffs[name] -= removed
        if self.buffs[name] <= 0:
            del self.buffs[name]
            logger.info("[Entity] %s buff [%s] 层数耗尽已清除", self.name, name)
        else:
            logger.info(
                "[Entity] %s 部分移除 buff [%s] x%d，剩余=%d",
                self.name, name, removed, self.buffs[name],
            )
        return self.buffs.get(name, 0)

    def has_buff(self, name: str) -> bool:
        """是否拥有某 buff。"""
        return name in self.buffs

    def get_buff_stacks(self, name: str) -> int:
        """获取某 buff 的层数（无则返回 0）。"""
        return self.buffs.get(name, 0)

    # ------------------------------------------------------------------ #
    # 状态查询
    # ------------------------------------------------------------------ #
    def is_dead(self) -> bool:
        """是否死亡。"""
        return self.current_hp <= 0

    def is_alive(self) -> bool:
        """是否存活。"""
        return self.current_hp > 0

    # ------------------------------------------------------------------ #
    # 魔术方法
    # ------------------------------------------------------------------ #
    def __str__(self) -> str:
        """可读的状态字符串，便于终端打印测试。"""
        buff_str: str = ", ".join(f"{k}×{v}" for k, v in self.buffs.items()) or "无"
        return (
            f"[{self.name}] HP:{self.current_hp}/{self.max_hp} "
            f"护甲:{self.block} Buff:{buff_str}"
        )