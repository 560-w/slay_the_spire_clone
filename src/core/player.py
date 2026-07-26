"""player.py: Player 类。

继承自 Entity，额外管理：
- 能量（Energy）：回合资源，用于打出卡牌
- 抽牌堆（Draw Pile）：未抽取的卡牌
- 手牌（Hand）：当前可打出的卡牌
- 弃牌堆（Discard Pile）：打出的卡牌弃置于此
- 消耗堆（Exhaust Pile）：被「消耗」的卡牌，本局战斗不再可用

设计原则：
1. 牌堆管理方法使用 assert 校验卡牌确实位于相应牌堆，防止状态错乱。
2. 能量管理独立于卡牌效果：卡牌 play 不扣费，由本类/控制器调用
   spend_energy 显式扣除，职责分离。
3. 抽牌堆耗尽时自动洗回弃牌堆（随机洗牌），贴近《杀戮尖塔》机制。
4. 回合钩子 start_turn/end_turn 为占位，具体结算逻辑由控制器实现。
"""

from __future__ import annotations

import logging
import random
from typing import List, Optional

from .card import Card
from .entity import Entity

logger = logging.getLogger(__name__)


class Player(Entity):
    """玩家角色，继承自 Entity。

    额外属性:
        max_energy (int): 每回合最大能量（基础通常为 3）。
        current_energy (int): 当前剩余能量。
        draw_pile (List[Card]): 抽牌堆。
        hand (List[Card]): 手牌。
        discard_pile (List[Card]): 弃牌堆。
        exhaust_pile (List[Card]): 消耗堆。
        max_hand_size (int): 手牌上限（默认 10）。
    """

    def __init__(
        self,
        name: str = "铁甲战士",
        max_hp: int = 75,
        max_energy: int = 3,
        max_hand_size: int = 10,
    ) -> None:
        """初始化玩家。

        Args:
            name: 角色名，默认 "铁甲战士"。
            max_hp: 最大生命值，默认 75。
            max_energy: 每回合最大能量，默认 3。必须为正整数。
            max_hand_size: 手牌上限，默认 10。

        Raises:
            AssertionError: 当 max_energy <= 0 或 max_hand_size <= 0 时触发。
        """
        super().__init__(name=name, max_hp=max_hp)

        assert max_energy > 0, f"[Player] max_energy 必须为正整数，收到 {max_energy}"
        assert max_hand_size > 0, f"[Player] max_hand_size 必须为正整数，收到 {max_hand_size}"

        self.max_energy: int = max_energy
        self.current_energy: int = 0  # 初始 0 能量，回合开始时才回复
        self.draw_pile: List[Card] = []
        self.hand: List[Card] = []
        self.discard_pile: List[Card] = []
        self.exhaust_pile: List[Card] = []
        self.processing_pile: List[Card] = []  # 处理区（栈结构，末尾为栈顶）
        self.max_hand_size: int = max_hand_size
        # 跨战斗持久牌组（真正的玩家牌组，战斗中不改变）
        # 战斗开始时从此深拷贝到 draw_pile；奖励/购买的新牌加入此处
        self.deck_pile: List[Card] = []
        # 遗物列表（跨战斗持久化）
        self.relics: list = []  # List[Relic]

        logger.debug(
            "[Player] 创建玩家 %s (max_hp=%d, max_energy=%d)",
            self.name, self.max_hp, self.max_energy,
        )

    # ------------------------------------------------------------------ #
    # 能量管理
    # ------------------------------------------------------------------ #
    def gain_energy(self, amount: int) -> int:
        """获得能量（可超出 max_energy，用于临时能量道具）。

        Args:
            amount: 获得的能量，必须 >= 0。

        Returns:
            获得后的当前能量。
        """
        assert amount >= 0, f"[Player] 获得能量不能为负，收到 {amount}"
        self.current_energy += amount
        logger.info("[Player] %s 获得 %d 能量，当前能量=%d", self.name, amount, self.current_energy)
        return self.current_energy

    def spend_energy(self, cost: int) -> int:
        """消耗能量。

        Args:
            cost: 消耗的能量，必须 >= 0。

        Returns:
            消耗后的当前能量。

        Raises:
            AssertionError: 当 cost 为负或能量不足时触发。
        """
        assert cost >= 0, f"[Player] 消耗能量不能为负，收到 {cost}"
        assert self.current_energy >= cost, (
            f"[Player] {self.name} 能量不足: 需要 {cost}，当前 {self.current_energy}"
        )
        self.current_energy -= cost
        logger.info("[Player] %s 消耗 %d 能量，剩余能量=%d", self.name, cost, self.current_energy)
        return self.current_energy

    def can_afford(self, cost: int) -> bool:
        """是否负担得起该费用。"""
        return self.current_energy >= cost

    # ------------------------------------------------------------------ #
    # 牌堆管理
    # ------------------------------------------------------------------ #
    def draw_cards(self, count: int = 1) -> List[Card]:
        """从抽牌堆抽取卡牌到手牌。

        若抽牌堆不足，自动将弃牌堆洗回抽牌堆后继续抽。
        若手牌已满，多余抽到的卡牌直接进入弃牌堆（《杀戮尖塔》规则）。

        Args:
            count: 抽牌数量，必须 >= 0。

        Returns:
            实际进入手牌的卡牌列表（顺序为抽取顺序）。

        Raises:
            AssertionError: 当 count 为负时触发。
        """
        assert count >= 0, f"[Player] 抽牌数量不能为负，收到 {count}"

        drawn: List[Card] = []
        for _ in range(count):
            # 抽牌堆耗尽：尝试洗回弃牌堆
            if not self.draw_pile:
                self._shuffle_discard_into_draw()
            # 仍无牌可抽（弃牌堆也空），结束
            if not self.draw_pile:
                logger.info("[Player] %s 无牌可抽（抽牌堆与弃牌堆均空）", self.name)
                break

            card = self.draw_pile.pop()
            # 手牌已满：直接弃置
            if len(self.hand) >= self.max_hand_size:
                self.discard_pile.append(card)
                logger.info(
                    "[Player] %s 手牌已满，抽到的 %s 直接弃置", self.name, card.name
                )
            else:
                self.hand.append(card)
                drawn.append(card)
                logger.info("[Player] %s 抽到卡牌: %s", self.name, card.name)

        return drawn

    def discard_card(self, card: Card) -> None:
        """从手牌弃置一张卡牌到弃牌堆。

        Args:
            card: 要弃置的卡牌，必须当前在手牌中。

        Raises:
            AssertionError: 当卡牌不在手牌中时触发。
        """
        assert card in self.hand, (
            f"[Player] 弃牌失败: {card.name} 不在 {self.name} 的手牌中"
        )
        self.hand.remove(card)
        self.discard_pile.append(card)
        logger.info("[Player] %s 弃置卡牌: %s", self.name, card.name)

    def exhaust_card(self, card: Card) -> None:
        """从手牌消耗一张卡牌到消耗堆。

        消耗的卡牌本局战斗不再可用（区别于普通弃置）。

        Args:
            card: 要消耗的卡牌，必须当前在手牌中。

        Raises:
            AssertionError: 当卡牌不在手牌中时触发。
        """
        assert card in self.hand, (
            f"[Player] 消耗失败: {card.name} 不在 {self.name} 的手牌中"
        )
        self.hand.remove(card)
        self.exhaust_pile.append(card)
        logger.info("[Player] %s 消耗卡牌: %s", self.name, card.name)

    def _shuffle_discard_into_draw(self) -> None:
        """将弃牌堆洗回抽牌堆（内部方法）。

        使用 random.shuffle 随机洗牌。Phase 1 简单实现，
        未来若需确定性测试可注入 RNG。
        """
        if not self.discard_pile:
            logger.debug("[Player] %s 弃牌堆为空，无需洗回", self.name)
            return

        random.shuffle(self.discard_pile)
        self.draw_pile.extend(self.discard_pile)
        moved = len(self.discard_pile)
        self.discard_pile.clear()
        logger.info("[Player] %s 将 %d 张弃牌洗回抽牌堆", self.name, moved)

    def add_card_to_draw(self, card: Card) -> None:
        """向抽牌堆添加一张卡牌（用于初始组牌或特殊效果）。"""
        self.draw_pile.append(card)
        logger.debug("[Player] %s 抽牌堆加入卡牌: %s", self.name, card.name)

    def add_card_to_discard(self, card: Card) -> None:
        """直接向弃牌堆添加一张卡牌。"""
        self.discard_pile.append(card)
        logger.debug("[Player] %s 弃牌堆加入卡牌: %s", self.name, card.name)

    # ------------------------------------------------------------------ #
    # 处理区管理（栈结构）
    # ------------------------------------------------------------------ #
    def push_to_processing(self, card: Card) -> None:
        """将卡牌推入处理区栈顶（打出时调用）。"""
        self.processing_pile.append(card)
        logger.debug("[Player] %s 处理区推入: %s (栈深=%d)", self.name, card.name, len(self.processing_pile))

    def pop_from_processing(self) -> Card:
        """从处理区弹出栈顶卡牌（结算完成时调用）。

        Raises:
            AssertionError: 当处理区为空时触发。
        """
        assert self.processing_pile, "[Player] 处理区为空，无法弹出"
        card = self.processing_pile.pop()
        logger.debug("[Player] %s 处理区弹出: %s (栈深=%d)", self.name, card.name, len(self.processing_pile))
        return card

    # ------------------------------------------------------------------ #
    # 回合钩子（占位，具体逻辑由控制器实现）
    # ------------------------------------------------------------------ #
    def start_turn(self) -> None:
        """回合开始钩子。

        Phase 1 仅做基础处理：回复能量、抽 5 张牌。
        后续可由控制器覆盖或扩展（处理 buff 结算等）。
        """
        self.current_energy = self.max_energy
        self.draw_cards(5)
        logger.info(
            "[Player] %s 回合开始: 能量=%d, 手牌数=%d",
            self.name, self.current_energy, len(self.hand),
        )

    def end_turn(self) -> None:
        """回合结束钩子。

        Phase 1 仅做基础处理：手牌全部弃置。
        后续可由控制器覆盖（清护甲、结算 buff 回合数等）。
        """
        # 弃置所有手牌
        while self.hand:
            self.discard_card(self.hand[0])
        logger.info("[Player] %s 回合结束: 手牌已全部弃置", self.name)

    # ------------------------------------------------------------------ #
    # 状态查询
    # ------------------------------------------------------------------ #
    def hand_size(self) -> int:
        """当前手牌数量。"""
        return len(self.hand)

    def draw_pile_size(self) -> int:
        """抽牌堆数量。"""
        return len(self.draw_pile)

    def discard_pile_size(self) -> int:
        """弃牌堆数量。"""
        return len(self.discard_pile)

    def exhaust_pile_size(self) -> int:
        """消耗堆数量。"""
        return len(self.exhaust_pile)

    def deck_pile_size(self) -> int:
        """跨战斗持久牌组数量。"""
        return len(self.deck_pile)

    # ------------------------------------------------------------------ #
    # 魔术方法
    # ------------------------------------------------------------------ #
    def __str__(self) -> str:
        """可读的玩家状态字符串。"""
        base = super().__str__()
        return (
            f"{base} | 能量:{self.current_energy}/{self.max_energy} "
            f"手牌:{len(self.hand)} 抽牌堆:{len(self.draw_pile)} "
            f"弃牌堆:{len(self.discard_pile)} 消耗堆:{len(self.exhaust_pile)}"
        )