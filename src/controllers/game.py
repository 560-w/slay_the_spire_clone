"""game.py: GameController 高层游戏状态机。

职责:
1. 管理整个游戏的流程状态（地图 → 战斗 → 奖励 → 篝火 → 商店 → 地图 → ... → 结束）。
2. 持有 Player（跨战斗持久化）、Map、当前战斗控制器。
3. 协调地图导航、战斗启动、战后奖励、篝火/商店交互。
4. 战后保留玩家 HP，牌组全部洗回抽牌堆。

状态枚举:
- MAP: 展示地图，等待玩家选择节点
- BATTLE: 战斗中
- REWARD: 战后选牌/领金币
- CAMPFIRE: 篝火（休息/升级）
- SHOP: 商店
- GAME_OVER: 游戏结束（胜利或失败）

需求2 修改: 引入 deck_pile（跨战斗持久牌组），战斗开始时深拷贝到 draw_pile。
"""

from __future__ import annotations

import copy
import logging
import random
from enum import Enum
from typing import List, Optional, TYPE_CHECKING

from src.core.map import Map, MapNode, RoomType
from src.core.player import Player
from src.core.card import Card
from src.data.cards import create_starter_deck
from src.data.enemies import create_test_enemies

if TYPE_CHECKING:
    from src.controllers.battle import BattleController

logger = logging.getLogger(__name__)


class GameState(Enum):
    """游戏状态枚举。"""
    MAP = "地图"
    BATTLE = "战斗"
    REWARD = "奖励"
    CAMPFIRE = "篝火"
    SHOP = "商店"
    GAME_OVER = "游戏结束"


class GameController:
    """高层游戏状态机。

    Attributes:
        player: 玩家对象（跨战斗持久化）。
        game_map: 地图对象。
        state: 当前游戏状态。
        battle: 当前战斗控制器（仅在 BATTLE 状态有效）。
        gold: 玩家金币。
    """

    def __init__(self, player_name: str = "铁甲战士") -> None:
        # 创建玩家
        self.player: Player = Player(name=player_name, max_hp=75, max_energy=3)
        # 初始化跨战斗持久牌组 deck_pile
        for card in create_starter_deck():
            self.player.deck_pile.append(card)
        # 生成地图
        self.game_map: Map = Map(num_layers=7)
        self.state: GameState = GameState.MAP
        self.battle: Optional[BattleController] = None
        self.gold: int = 99  # 初始金币
        self.message: str = "选择下一个房间前进"

        # 奖励相关
        self.reward_cards: List[Card] = []
        self.reward_gold: int = 0

        # 商店相关
        self.shop_cards: List[tuple[Card, int]] = []  # (卡牌, 价格)

        logger.info("[Game] 游戏初始化完成: %s", player_name)

    def _load_deck_to_draw_pile(self) -> None:
        """战斗开始：从 deck_pile 深拷贝到 draw_pile 并洗牌。

        deck_pile 是跨战斗持久牌组，战斗中塞入的状态牌不会污染 deck_pile。
        """
        self.player.draw_pile.clear()
        self.player.hand.clear()
        self.player.discard_pile.clear()
        self.player.exhaust_pile.clear()
        self.player.processing_pile.clear()
        for card in self.player.deck_pile:
            self.player.draw_pile.append(copy.deepcopy(card))
        random.shuffle(self.player.draw_pile)
        logger.info("[Game] deck_pile(%d) 拷贝到 draw_pile 并洗牌", len(self.player.draw_pile))

    # ------------------------------------------------------------------ #
    # 地图导航
    # ------------------------------------------------------------------ #
    def select_map_node(self, node_id: str) -> None:
        """玩家在地图上选择一个节点。"""
        if self.state != GameState.MAP:
            return

        node = self.game_map.get_node(node_id)
        if node is None:
            return
        if not node.accessible or node.visited:
            return

        # 移动到节点
        self.game_map.move_to_node(node_id)

        # 根据节点类型切换状态
        if node.room_type == RoomType.BATTLE:
            self._start_battle(is_elite=False)
        elif node.room_type == RoomType.ELITE:
            self._start_battle(is_elite=True)
        elif node.room_type == RoomType.BOSS:
            self._start_battle(is_elite=False, is_boss=True)
        elif node.room_type == RoomType.CAMPFIRE:
            self.state = GameState.CAMPFIRE
            self.message = "篝火：休息回复 30% HP，或升级一张牌"
        elif node.room_type == RoomType.SHOP:
            self._enter_shop()
        else:
            logger.warning("[Game] 未知房间类型: %s", node.room_type)

    def return_to_map(self) -> None:
        """从战斗/奖励/篝火/商店返回地图。"""
        self.state = GameState.MAP

        if self.game_map.is_complete():
            self.state = GameState.GAME_OVER
            self.message = "恭喜！你击败了 Boss，通关成功！"
            logger.info("[Game] 游戏通关！")
            return

        self.message = "选择下一个房间前进"

    # ------------------------------------------------------------------ #
    # 战斗管理
    # ------------------------------------------------------------------ #
    def _start_battle(self, is_elite: bool = False, is_boss: bool = False) -> None:
        """启动一场战斗。

        修复（需求1）: 清除 player.buffs，防止跨战斗 buff 保留。
        修复（需求2）: 从 deck_pile 深拷贝到 draw_pile。
        """
        from src.controllers.battle import BattleController

        # 重置玩家回合状态（HP 保留）
        self.player.current_energy = 0
        self.player.block = 0
        self.player.buffs.clear()  # 需求1: 清除跨战斗 buff
        # 从 deck_pile 加载到 draw_pile
        self._load_deck_to_draw_pile()

        # 生成敌人
        enemies = create_test_enemies(elite=is_elite, boss=is_boss)

        self.battle = BattleController(player=self.player, enemies=enemies)
        self.battle.start_battle()
        self.state = GameState.BATTLE
        self.message = f"战斗开始！{'精英' if is_elite else 'Boss' if is_boss else ''}"

        logger.info(
            "[Game] 战斗启动: elite=%s, boss=%s, 敌人=%s",
            is_elite, is_boss, [e.name for e in enemies],
        )

    def on_battle_end(self) -> None:
        """战斗结束后的处理。"""
        assert self.battle is not None, "[Game] 无当前战斗"
        assert self.battle.is_over(), "[Game] 战斗尚未结束"

        if self.battle.state.value == "失败":
            self.state = GameState.GAME_OVER
            self.message = "你被击败了...游戏结束"
            logger.info("[Game] 玩家阵亡，游戏结束")
            return

        # 胜利：进入奖励阶段
        is_elite = any(
            n.room_type == RoomType.ELITE and n.visited
            for n in self.game_map.nodes
            if n.node_id == self.game_map.current_node_id
        )
        is_boss = any(
            n.room_type == RoomType.BOSS and n.visited
            for n in self.game_map.nodes
            if n.node_id == self.game_map.current_node_id
        )

        if is_boss:
            self.state = GameState.GAME_OVER
            self.message = "恭喜！你击败了 Boss，通关成功！"
            logger.info("[Game] Boss 击败，游戏通关！")
            return

        # 生成奖励
        self._generate_reward(is_elite)
        self.state = GameState.REWARD
        self.message = f"战斗胜利！获得 {self.reward_gold} 金币，选择一张牌加入牌组"

    def _generate_reward(self, is_elite: bool) -> None:
        """生成战斗奖励（金币 + 三选一卡牌）。"""
        from src.data.cards import (
            Strike, Defend, Bash, Survivor, Offering,
            MachineLearning, Whirlwind, Hologram, Domination, DarkShackles,
        )

        # 金币
        if is_elite:
            self.reward_gold = random.randint(30, 45)
        else:
            self.reward_gold = random.randint(15, 25)
        self.gold += self.reward_gold

        # 卡牌奖励：从可用卡池随机 3 张
        card_pool = [
            Strike, Defend, Bash, Survivor, Offering,
            MachineLearning, Whirlwind, Hologram, Domination, DarkShackles,
        ]
        chosen_types = random.sample(card_pool, min(3, len(card_pool)))
        self.reward_cards = [ct() for ct in chosen_types]

        logger.info(
            "[Game] 生成奖励: %d 金币, %d 张卡牌可选",
            self.reward_gold, len(self.reward_cards),
        )

    def select_reward_card(self, card_idx: int) -> None:
        """玩家选择奖励卡牌。

        修复（需求2）: 新牌加入 deck_pile（而非 draw_pile）。
        """
        assert self.state == GameState.REWARD, "[Game] 当前不在奖励状态"
        if card_idx >= 0:
            assert 0 <= card_idx < len(self.reward_cards), (
                f"[Game] 奖励卡牌索引越界: {card_idx}"
            )
            chosen = self.reward_cards[card_idx]
            self.player.deck_pile.append(chosen)  # 加入持久牌组
            self.message = f"获得卡牌: {chosen.name}"
            logger.info("[Game] 玩家选择奖励卡牌: %s", chosen.name)
        else:
            self.message = "跳过选牌"

        self.reward_cards.clear()
        self.return_to_map()

    # ------------------------------------------------------------------ #
    # 篝火
    # ------------------------------------------------------------------ #
    def campfire_rest(self) -> None:
        """篝火休息：回复 30% 最大生命值。"""
        assert self.state == GameState.CAMPFIRE, "[Game] 当前不在篝火状态"
        heal_amount = int(self.player.max_hp * 0.3)
        actual = self.player.heal(heal_amount)
        self.message = f"休息回复了 {actual} 点生命值"
        logger.info("[Game] 篝火休息: 回复 %d HP", actual)
        self.return_to_map()

    def campfire_upgrade(self, card_index: int) -> None:
        """篝火升级一张牌。

        修复（需求2）: 从 deck_pile 遍历升级。
        """
        assert self.state == GameState.CAMPFIRE, "[Game] 当前不在篝火状态"
        assert 0 <= card_index < len(self.player.deck_pile), (
            f"[Game] 升级卡牌索引越界: {card_index}"
        )
        card = self.player.deck_pile[card_index]
        card.upgrade()
        self.message = f"升级了 {card.name}！"
        logger.info("[Game] 篝火升级: %s", card.name)
        self.return_to_map()

    # ------------------------------------------------------------------ #
    # 商店
    # ------------------------------------------------------------------ #
    def _enter_shop(self) -> None:
        """进入商店时生成商品并切换状态。"""
        from src.data.cards import (
            Strike, Defend, Bash, Survivor, Offering,
            MachineLearning, Whirlwind, Hologram, Domination, DarkShackles,
        )
        card_pool = [
            Strike, Defend, Bash, Survivor, Offering,
            MachineLearning, Whirlwind, Hologram, Domination, DarkShackles,
        ]
        chosen_types = random.sample(card_pool, min(3, len(card_pool)))
        self.shop_cards = []
        for ct in chosen_types:
            card = ct()
            price = random.randint(50, 150)
            self.shop_cards.append((card, price))
        self.state = GameState.SHOP
        self.message = f"商店：你有 {self.gold} 金币，选择要购买的卡牌"
        logger.info("[Game] 进入商店: %d 件商品", len(self.shop_cards))

    def shop_buy_card(self, card_idx: int) -> bool:
        """商店购买卡牌。

        修复（需求2）: 购买的卡牌加入 deck_pile。
        """
        assert self.state == GameState.SHOP, "[Game] 当前不在商店状态"
        assert 0 <= card_idx < len(self.shop_cards), (
            f"[Game] 商店商品索引越界: {card_idx}"
        )
        card, price = self.shop_cards[card_idx]
        if self.gold < price:
            self.message = "金币不足！"
            return False
        self.gold -= price
        self.player.deck_pile.append(card)  # 加入持久牌组
        self.shop_cards.pop(card_idx)
        self.message = f"购买了 {card.name}，花费 {price} 金币"
        logger.info("[Game] 商店购买卡牌: %s (%d 金币)", card.name, price)
        return True

    def shop_leave(self) -> None:
        """离开商店。"""
        assert self.state == GameState.SHOP, "[Game] 当前不在商店状态"
        self.shop_cards.clear()
        self.return_to_map()

    # ------------------------------------------------------------------ #
    # 状态查询
    # ------------------------------------------------------------------ #
    def is_game_over(self) -> bool:
        """游戏是否已结束。"""
        return self.state == GameState.GAME_OVER

    def get_state(self) -> dict:
        """获取游戏状态快照（供 View 渲染）。"""
        return {
            "state": self.state,
            "message": self.message,
            "player": self.player,
            "map": self.game_map.get_state() if self.game_map else None,
            "gold": self.gold,
            "reward_cards": self.reward_cards,
            "reward_gold": self.reward_gold,
            "battle": self.battle,
        }