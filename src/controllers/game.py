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
from src.data.enemies import create_enemies_for_act

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
    TREASURE = "宝箱"
    EVENT = "事件"
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
        self.reward_relic = None  # Boss 遗物

        # 商店相关
        self.shop_cards: List[tuple[Card, int]] = []  # (卡牌, 价格)
        self.shop_relic = None  # 商店遗物
        self.shop_relic_price: int = 0
        self.shop_remove_price: int = 75

        # 宝箱房相关
        self.treasure_gold: int = 0
        self.treasure_relic = None  # Relic

        # 事件房相关
        self.current_event = None  # GameEvent
        self.pending_delete_card: bool = False
        self.pending_upgrade_card: bool = False
        self._event_transform_callback = None  # 变牌事件回调

        # 多幕相关
        self.current_act: int = 1
        self.max_acts: int = 3

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
        # 统计已清理楼层
        self.player.floors_cleared += 1

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
        elif node.room_type == RoomType.TREASURE:
            self._enter_treasure()
        elif node.room_type == RoomType.EVENT:
            self._enter_event()
        else:
            logger.warning("[Game] 未知房间类型: %s", node.room_type)

    def return_to_map(self) -> None:
        """从战斗/奖励/篝火/商店/宝箱/事件返回地图。"""
        self.state = GameState.MAP

        # 检查是否需要进入下一幕
        if self.game_map.is_complete():
            if self.current_act < self.max_acts:
                # 进入下一幕
                self.current_act += 1
                self.game_map = Map(num_layers=7)
                self.message = f"第 {self.current_act} 幕开始！选择下一个房间前进"
                logger.info("[Game] 进入第 %d 幕", self.current_act)
                return
            else:
                # 通关
                self.state = GameState.GAME_OVER
                self.message = "恭喜！你击败了所有 Boss，通关成功！"
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

        # 生成敌人（根据当前 Act 和难度）
        enemies = create_enemies_for_act(act=self.current_act, elite=is_elite, boss=is_boss)

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

        # 胜利：统计击杀数
        self.player.total_kills += len([e for e in self.battle.enemies if not e.is_alive()])

        # 胜利：先触发遗物 on_combat_end 钩子
        for relic in self.player.relics:
            try:
                relic.on_combat_end(self.player, self.battle)
            except Exception as e:
                logger.warning("[Game] 遗物 %s on_combat_end 异常: %s", relic.name, e)

        # 胜利：战后回血
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
            heal_amount = self.player.max_hp  # Boss 战后回满血
        elif is_elite:
            heal_amount = int(self.player.max_hp * 0.3)
        else:
            heal_amount = int(self.player.max_hp * 0.2)
        actual_heal = min(heal_amount, self.player.max_hp - self.player.current_hp)
        self.player.current_hp += actual_heal
        if actual_heal > 0:
            logger.info("[Game] 战后回血: +%d HP (当前 %d/%d)", actual_heal, self.player.current_hp, self.player.max_hp)

        # 生成奖励（Boss 也走奖励流程，不掉落卡牌但给金币和遗物）
        self._generate_reward(is_elite, is_boss)
        self.state = GameState.REWARD
        if is_boss:
            self.message = f"Boss 击败！回满 HP，获得 {self.reward_gold} 金币和 Boss 遗物"
        else:
            self.message = f"战斗胜利！回复 {actual_heal} HP，获得 {self.reward_gold} 金币，选择一张牌加入牌组"

    def _generate_reward(self, is_elite: bool, is_boss: bool = False) -> None:
        """生成战斗奖励（金币 + 遗物 + 三选一卡牌）。

        - 普通战斗: 15~25 金币，3 张卡牌（1 罕见 + 2 普通）
        - 精英战斗: 30~45 金币，3 张卡牌（1 稀有 + 2 罕见）
        - Boss 战斗: 50~80 金币，Boss 遗物，不选卡牌
        """
        from src.data.cards import COMMON_CARDS, UNCOMMON_CARDS, RARE_CARDS

        self.reward_cards = []
        self.reward_relic = None

        # 金币
        if is_boss:
            self.reward_gold = random.randint(50, 80)
        elif is_elite:
            self.reward_gold = random.randint(30, 45)
        else:
            self.reward_gold = random.randint(15, 25)
        self.gold += self.reward_gold

        # Boss 遗物 + 2 张稀有卡牌可选
        if is_boss:
            from src.data.relics import BOSS_RELICS
            self.reward_relic = random.choice(BOSS_RELICS)()
            self.player.relics.append(self.reward_relic)
            logger.info("[Game] Boss 遗物: %s", self.reward_relic.name)
            # Boss 额外提供 2 张稀有卡牌可选
            boss_card_pool = []
            boss_card_pool.append(random.choice(RARE_CARDS))
            boss_card_pool.append(random.choice(RARE_CARDS))
            self.reward_cards = [ct() for ct in boss_card_pool]
            return

        # 卡牌奖励（按稀有度权重）
        if is_elite:
            # 精英：1 稀有 + 2 罕见
            pool = []
            pool.append(random.choice(RARE_CARDS))
            pool.extend(random.choices(UNCOMMON_CARDS, k=2))
        else:
            # 普通：1 罕见 + 2 普通
            pool = []
            pool.append(random.choice(UNCOMMON_CARDS))
            pool.extend(random.choices(COMMON_CARDS, k=2))
        random.shuffle(pool)
        self.reward_cards = [ct() for ct in pool]

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
        self.reward_relic = None
        self.return_to_map()

    # ------------------------------------------------------------------ #
    # 篝火
    # ------------------------------------------------------------------ #
    def campfire_rest(self) -> None:
        """篝火休息：回复 30% 最大生命值。

        遗物加成:
        - 皇家枕头: 额外回复 15% 最大 HP。
        - 捕梦网: 休息时获得 1 张随机卡牌。
        """
        assert self.state == GameState.CAMPFIRE, "[Game] 当前不在篝火状态"

        # 皇家枕头：额外 15% 回复
        from src.data.relics import RoyalPillow, DreamCatcher
        bonus_pct = 0.15 if any(isinstance(r, RoyalPillow) for r in self.player.relics) else 0.0
        heal_amount = int(self.player.max_hp * (0.3 + bonus_pct))
        actual = self.player.heal(heal_amount)
        self.message = f"休息回复了 {actual} 点生命值"

        # 捕梦网：获得 1 张随机卡牌
        if any(isinstance(r, DreamCatcher) for r in self.player.relics):
            from src.data.cards import COMMON_CARDS
            new_card = random.choice(COMMON_CARDS)()
            self.player.deck_pile.append(new_card)
            self.message += f"（捕梦网：获得 {new_card.name}）"
            logger.info("[Game] 捕梦网: 获得卡牌 %s", new_card.name)

        logger.info("[Game] 篝火休息: 回复 %d HP", actual)
        self.return_to_map()

    def campfire_upgrade(self, card_index: int) -> None:
        """篝火升级一张牌。

        修复（需求2）: 从 deck_pile 遍历升级。
        遗物限制: 融合之锤阻止篝火升级。
        """
        assert self.state == GameState.CAMPFIRE, "[Game] 当前不在篝火状态"

        # 融合之锤：不能升级
        from src.data.relics import FusionHammer
        if any(isinstance(r, FusionHammer) for r in self.player.relics):
            self.message = "融合之锤：无法在篝火升级卡牌！"
            logger.info("[Game] 融合之锤阻止篝火升级")
            self.return_to_map()
            return

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
        """进入商店时生成商品并切换状态。

        商店内容：
        - 3 张卡牌（含稀有度关联价格）
        - 1 个遗物（非 Boss 遗物）
        - 删牌服务（75 金币）
        """
        from src.data.cards import COMMON_CARDS, UNCOMMON_CARDS, RARE_CARDS
        from src.data.relics import NON_BOSS_RELICS

        # 卡牌：1 普通 + 1 罕见 + 1 稀有
        card_cls_list = [
            random.choice(COMMON_CARDS),
            random.choice(UNCOMMON_CARDS),
            random.choice(RARE_CARDS),
        ]
        random.shuffle(card_cls_list)
        self.shop_cards = []
        for ct in card_cls_list:
            card = ct()
            # 价格按稀有度
            if card.rarity and card.rarity.value == "稀有":
                price = random.randint(70, 110)
            elif card.rarity and card.rarity.value == "罕见":
                price = random.randint(50, 80)
            else:
                price = random.randint(30, 55)
            self.shop_cards.append((card, price))

        # 遗物（1 个随机非 Boss 遗物，排除已拥有）
        self.shop_relic = None
        self.shop_relic_price = 0
        owned_names = {r.name for r in self.player.relics}
        available = [r for r in NON_BOSS_RELICS if r().name not in owned_names]
        if available:
            relic_cls = random.choice(available)
            self.shop_relic = relic_cls()
            self.shop_relic_price = random.randint(120, 160)

        # 微笑面具：删牌费用减半（向下取整）
        from src.data.relics import SmilingMask
        self.shop_remove_price = 25 if any(
            isinstance(r, SmilingMask) for r in self.player.relics
        ) else 50

        self.state = GameState.SHOP
        self.message = f"商店：你有 {self.gold} 金币，选择要购买的物品"
        logger.info(
            "[Game] 进入商店: %d 件卡牌商品, 遗物=%s, 删牌=%d 金币",
            len(self.shop_cards),
            self.shop_relic.name if self.shop_relic else "无",
            self.shop_remove_price,
        )

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

    def shop_buy_relic(self) -> bool:
        """商店购买遗物。"""
        assert self.state == GameState.SHOP, "[Game] 当前不在商店状态"
        if self.shop_relic is None:
            self.message = "遗物已售罄"
            return False
        if self.gold < self.shop_relic_price:
            self.message = "金币不足！"
            return False
        self.gold -= self.shop_relic_price
        self.player.relics.append(self.shop_relic)
        self.message = f"购买了遗物 {self.shop_relic.name}，花费 {self.shop_relic_price} 金币"
        logger.info("[Game] 商店购买遗物: %s (%d 金币)", self.shop_relic.name, self.shop_relic_price)
        self.shop_relic = None
        self.shop_relic_price = 0
        return True

    def shop_remove_card(self, card_index: int) -> bool:
        """商店删牌服务"""
        assert self.state == GameState.SHOP, "[Game] 当前不在商店状态"
        if self.gold < self.shop_remove_price:
            self.message = "金币不足！"
            return False
        if not (0 <= card_index < len(self.player.deck_pile)):
            self.message = "无效的卡牌"
            return False
        self.gold -= self.shop_remove_price
        card = self.player.deck_pile[card_index]
        self.player.deck_pile.remove(card)
        self.message = f"删除了 {card.name}，花费 {self.shop_remove_price} 金币"
        logger.info("[Game] 商店删牌: %s (%d 金币)", card.name, self.shop_remove_price)
        return True

    def shop_leave(self) -> None:
        """离开商店。"""
        assert self.state == GameState.SHOP, "[Game] 当前不在商店状态"
        self.shop_cards.clear()
        self.shop_relic = None
        self.shop_relic_price = 0
        self.return_to_map()

    # ------------------------------------------------------------------ #
    # 宝箱房
    # ------------------------------------------------------------------ #
    def _enter_treasure(self) -> None:
        """进入宝箱房：获得 30~70 金币 + 1 个随机遗物。

        遗物副作用:
        - 黑暗之球: 宝箱房不给遗物。
        - 诅咒钥匙: 宝箱房金币减半。
        """
        from src.data.relics import NON_BOSS_RELICS, DarkOrb, CursedKey

        has_dark_orb = any(isinstance(r, DarkOrb) for r in self.player.relics)
        has_cursed_key = any(isinstance(r, CursedKey) for r in self.player.relics)

        self.treasure_gold = random.randint(30, 70)
        if has_cursed_key:
            self.treasure_gold = self.treasure_gold // 2
        self.gold += self.treasure_gold

        # 黑暗之球：不给遗物
        if has_dark_orb:
            self.treasure_relic = None
            self.state = GameState.TREASURE
            self.message = f"宝箱！获得 {self.treasure_gold} 金币（黑暗之球：无遗物）"
            logger.info("[Game] 宝箱房: %d 金币 (黑暗之球)", self.treasure_gold)
            return

        # 随机选 1 个遗物（玩家尚未拥有的，非 Boss 遗物）
        relic_pool = NON_BOSS_RELICS
        owned_names = {r.name for r in self.player.relics}
        available = [r for r in relic_pool if r().name not in owned_names]
        if available:
            relic_cls = random.choice(available)
            self.treasure_relic = relic_cls()
            self.player.relics.append(self.treasure_relic)
        else:
            # 已拥有所有遗物，额外给金币
            extra = random.randint(30, 50)
            self.treasure_gold += extra
            self.gold += extra
            self.treasure_relic = None

        self.state = GameState.TREASURE
        relic_name = self.treasure_relic.name if self.treasure_relic else "无（已有所有遗物，获得额外金币）"
        self.message = f"宝箱！获得 {self.treasure_gold} 金币，遗物：{relic_name}"
        logger.info(
            "[Game] 宝箱房: %d 金币, 遗物=%s",
            self.treasure_gold, relic_name,
        )

    def confirm_treasure(self) -> None:
        """确认宝箱奖励，返回地图。

        宝箱房确认后：生成下一页地图（第1~5页），或返回地图（最终页）。
        """
        assert self.state == GameState.TREASURE, "[Game] 当前不在宝箱状态"
        self.treasure_gold = 0
        self.treasure_relic = None
        self.game_map.page_completed = True
        if self.game_map.current_page < self.game_map.TOTAL_PAGES:
            self.game_map.generate_next_page()
            self.message = f"进入第 {self.game_map.current_page} 页地图！选择下一个房间前进"
            logger.info("[Game] 第 %d 页完成，生成第 %d 页地图",
                         self.game_map.current_page - 1, self.game_map.current_page)
        self.return_to_map()

    # ------------------------------------------------------------------ #
    # 事件房
    # ------------------------------------------------------------------ #
    def _enter_event(self) -> None:
        """进入事件房：随机抽取一个事件。"""
        from src.data.events import EVENT_POOL

        event_cls = random.choice(EVENT_POOL)
        self.current_event = event_cls()
        self.state = GameState.EVENT
        self.message = f"事件：{self.current_event.name}"
        logger.info("[Game] 事件房: %s", self.current_event.name)

    def select_event_option(self, option_idx: int) -> None:
        """玩家选择事件选项。"""
        assert self.state == GameState.EVENT, "[Game] 当前不在事件状态"
        assert self.current_event is not None, "[Game] 无当前事件"
        self.current_event.execute_option(option_idx, self)
        # 如果事件设置了 pending_delete_card/pending_upgrade_card，不立即返回地图
        # 由 View 层完成卡牌选择后调用 confirm_event_card_action
        if not self.pending_delete_card and not self.pending_upgrade_card:
            self.current_event = None
            self.return_to_map()

    def confirm_event_card_action(self, card_index: int = -1) -> None:
        """事件卡牌选择确认（删除/升级/变牌）。

        Args:
            card_index: 选中的卡牌索引（-1 表示取消）。
        """
        if self._event_transform_callback:
            # 变牌事件
            callback = self._event_transform_callback
            self._event_transform_callback = None
            self.pending_delete_card = False
            callback(card_index)
        elif self.pending_delete_card:
            self.pending_delete_card = False
            if card_index >= 0 and card_index < len(self.player.deck_pile):
                card = self.player.deck_pile[card_index]
                self.player.deck_pile.remove(card)
                self.message = f"删除了 {card.name}"
                logger.info("[Game] 事件删除卡牌: %s", card.name)
        elif self.pending_upgrade_card:
            self.pending_upgrade_card = False
            if card_index >= 0 and card_index < len(self.player.deck_pile):
                card = self.player.deck_pile[card_index]
                if not card.upgraded:
                    card.upgrade()
                    self.message = f"升级了 {card.name}"
                    logger.info("[Game] 事件升级卡牌: %s", card.name)

        self.current_event = None
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
            "reward_relic": self.reward_relic,
            "shop_relic": self.shop_relic,
            "shop_relic_price": self.shop_relic_price,
            "shop_remove_price": self.shop_remove_price,
            "treasure_gold": self.treasure_gold,
            "treasure_relic": self.treasure_relic,
            "current_event": self.current_event,
            "current_act": self.current_act,
            "max_acts": self.max_acts,
        }
