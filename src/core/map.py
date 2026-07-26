"""map.py: 地图数据结构与生成。

定义:
- MapNode: 单个房间节点（类型、坐标、连接）
- Map: 地图生成，分层随机生成节点与连线

房间类型:
- BATTLE: 普通战斗
- ELITE: 精英战斗
- CAMPFIRE: 篝火（休息/升级）
- SHOP: 商店
- BOSS: Boss 战（每层最后）
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Set

logger = logging.getLogger(__name__)


class RoomType(Enum):
    """房间类型枚举。"""
    BATTLE = "战斗"
    ELITE = "精英"
    CAMPFIRE = "篝火"
    SHOP = "商店"
    BOSS = "Boss"
    TREASURE = "宝箱"
    EVENT = "事件"


@dataclass
class MapNode:
    """地图节点。

    Attributes:
        node_id: 唯一标识符。
        room_type: 房间类型。
        layer: 所在层（0-based）。
        position: 在该层中的位置索引（0-based）。
        connections: 下游连接的节点 ID 集合。
        visited: 是否已被访问。
        accessible: 是否可从当前节点到达。
    """
    node_id: str
    room_type: RoomType
    layer: int
    position: int
    connections: Set[str] = field(default_factory=set)
    visited: bool = False
    accessible: bool = False

    @property
    def display_icon(self) -> str:
        """获取用于 UI 显示的图标（真 Emoji）。"""
        icons = {
            RoomType.BATTLE: "⚔️",
            RoomType.ELITE: "👑",
            RoomType.CAMPFIRE: "🔥",
            RoomType.SHOP: "🏪",
            RoomType.BOSS: "🐉",
            RoomType.TREASURE: "📦",
            RoomType.EVENT: "❓",
        }
        return icons.get(self.room_type, "?")

    @property
    def display_name(self) -> str:
        """获取用于 UI 显示的名称。"""
        return self.room_type.value


class Map:
    """地图生成器（六页结构）。

    生成规则:
    第 1~5 页:
    - Layer 0~4: 正常随机生成（战斗/精英/商店/篝火/事件）
    - Layer 5: 篝火
    - Layer 6: 宝箱房（固定 1 个，作为页间衔接点）

    第 6 页（最终页）:
    - Layer 0: 宝箱房（固定 1 个，已访问状态，代表玩家从此进入）
    - Layer 1~4: 正常随机生成（难度最高）
    - Layer 5: 篝火
    - Layer 6: Boss（固定 1 个）

    连接: 每个节点连接下一层 position 最接近的 1~2 个节点
    玩家从第一页 Layer 0 开始，每行只能选一个节点前进
    """

    TOTAL_PAGES: int = 6

    def __init__(
        self, num_layers: int = 7, seed: Optional[int] = None
    ) -> None:
        assert num_layers >= 3, "[Map] 层数至少为 3"
        self.num_layers: int = num_layers
        self.nodes: List[MapNode] = []
        self.current_node_id: Optional[str] = None
        self._counter: int = 0
        self.current_page: int = 1  # 当前页码（1~6）
        self.page_completed: bool = False  # 当前页是否完成（宝箱/Boss 已访问）

        if seed is not None:
            random.seed(seed)

        self._generate_page1()

    def _next_id(self) -> str:
        """生成唯一节点 ID。"""
        self._counter += 1
        return f"node_{self._counter}"

    def _generate_page1(self) -> None:
        """生成第一页地图（Layer 0~5 随机 + Layer 6 宝箱房）。"""
        self.nodes = []
        self.current_node_id = None
        self.current_page = 1
        self.page_completed = False

        layer_nodes = self._generate_page_layers(page_num=1)
        # 第一页最后一层是宝箱房
        for node in layer_nodes[-1]:
            node.room_type = RoomType.TREASURE

        # 设置第 0 层为 accessible
        for node in layer_nodes[0]:
            node.accessible = True

        logger.info(
            "[Map] 第 %d 页地图生成完成: %d 层, %d 个节点",
            self.current_page, self.num_layers, len(self.nodes),
        )

    def _generate_mid_page(self, page_num: int) -> None:
        """生成中间页地图（第 2~5 页，统一结构）。

        Layer 0: 宝箱入口（已访问）
        Layer 1~4: 随机
        Layer 5: 篝火
        Layer 6: 宝箱房（下一页入口）
        """
        self.nodes = []
        self.current_node_id = None
        self.current_page = page_num
        self.page_completed = False

        layer_nodes = self._generate_page_layers(page_num=page_num, layer0_count=1)
        # 第 0 层是宝箱房入口（已访问状态）
        for node in layer_nodes[0]:
            node.room_type = RoomType.TREASURE
            node.visited = True
        # 最后一层是宝箱房（通往下页）
        for node in layer_nodes[-1]:
            node.room_type = RoomType.TREASURE

        # 第 1 层设为 accessible
        for node in layer_nodes[1]:
            node.accessible = True

        logger.info(
            "[Map] 第 %d 页地图生成完成: %d 层, %d 个节点",
            page_num, self.num_layers, len(self.nodes),
        )

    def _generate_final_page(self) -> None:
        """生成最终页地图（第 6 页，末尾是 Boss）。

        Layer 0: 宝箱入口（已访问）
        Layer 1~4: 随机（最高难度）
        Layer 5: 篝火
        Layer 6: Boss
        """
        self.nodes = []
        self.current_node_id = None
        self.current_page = self.TOTAL_PAGES
        self.page_completed = False

        layer_nodes = self._generate_page_layers(page_num=self.TOTAL_PAGES, layer0_count=1)
        # 第 0 层是宝箱房入口（已访问状态）
        for node in layer_nodes[0]:
            node.room_type = RoomType.TREASURE
            node.visited = True
        # 最后一层是 Boss
        for node in layer_nodes[-1]:
            node.room_type = RoomType.BOSS

        # 第 1 层设为 accessible
        for node in layer_nodes[1]:
            node.accessible = True

        logger.info(
            "[Map] 最终页地图生成完成: %d 层, %d 个节点",
            self.num_layers, len(self.nodes),
        )

    def generate_next_page(self) -> None:
        """生成下一页地图。

        当前页宝箱房完成后调用，自动判断生成中间页还是最终页。
        """
        next_page = self.current_page + 1
        if next_page >= self.TOTAL_PAGES:
            self._generate_final_page()
        else:
            self._generate_mid_page(next_page)

    def generate_page2(self) -> None:
        """生成第二页（兼容旧接口，内部调用 generate_next_page）。"""
        self.generate_next_page()

    def _generate_page_layers(self, page_num: int = 1, layer0_count: int = 0) -> List[List[MapNode]]:
        """生成单页的各层节点（含类型分配、连接、可达性）。

        Args:
            page_num: 当前页码（1~6），影响房间类型概率。
            layer0_count: 第0层固定节点数（0=随机）。

        Returns:
            该页的各层节点列表。
        """
        layer_nodes: List[List[MapNode]] = []
        for layer_idx in range(self.num_layers):
            nodes_in_layer: List[MapNode] = []
            if layer_idx == self.num_layers - 1:
                # 最后一层固定 1 个
                count = 1
            elif layer_idx == self.num_layers - 2:
                # 倒数第二层：2 个
                count = 2
            else:
                count = layer0_count if (layer_idx == 0 and layer0_count > 0) else random.randint(2, 3)
            for pos in range(count):
                node = MapNode(
                    node_id=self._next_id(),
                    room_type=RoomType.BATTLE,  # 先占位，后续覆盖
                    layer=layer_idx,
                    position=pos,
                )
                nodes_in_layer.append(node)
                self.nodes.append(node)
            layer_nodes.append(nodes_in_layer)

        # 分配房间类型（中间层随机，难度随页码递增）
        self._assign_room_types(layer_nodes, page_num)

        # 连接相邻层
        for layer_idx in range(len(layer_nodes) - 1):
            current_layer = layer_nodes[layer_idx]
            next_layer = layer_nodes[layer_idx + 1]
            for node in current_layer:
                self._connect_by_position(node, next_layer)

        # 确保可达性
        self._ensure_reachability(layer_nodes)

        return layer_nodes

    def _assign_room_types(self, layer_nodes: List[List[MapNode]], page_num: int = 1) -> None:
        """分配单页内的房间类型，难度随页码递增。

        - Layer 0: 全部战斗（第一页）/ 宝箱房（第二页及以后，已在 _generate 中设置）
        - 中间层(1 ~ num_layers-3): 随机商店/精英/事件/战斗
        - Layer num_layers-2: 全部篝火
        - Layer num_layers-1: 宝箱房（非最终页）/ Boss（最终页，已在 _generate 中设置）

        页码影响:
        - 第 1~2 页: 精英 1~2 个，商店 1~2 个
        - 第 3~4 页: 精英 2~3 个，商店 1~2 个
        - 第 5~6 页: 精英 2~4 个，商店 1~2 个
        """
        num_layers = len(layer_nodes)
        # 固定层
        for node in layer_nodes[0]:
            if node.room_type == RoomType.BATTLE:  # 后续页入口已被设为 TREASURE
                node.room_type = RoomType.BATTLE
        for node in layer_nodes[num_layers - 2]:
            node.room_type = RoomType.CAMPFIRE

        # 中间层：收集所有 (layer, position) 坐标
        mid_coords: list[tuple[int, int]] = []
        for layer_idx in range(1, num_layers - 2):
            for node in layer_nodes[layer_idx]:
                mid_coords.append((layer_idx, node.position))

        if not mid_coords:
            return

        # 根据页码调整精英数量
        if page_num <= 2:
            min_elites, max_elites = 1, 2
        elif page_num <= 4:
            min_elites, max_elites = 2, 3
        else:
            min_elites, max_elites = 2, 4

        # 随机抽 1~2 个作商店
        num_shops = random.randint(1, min(2, max(1, len(mid_coords) // 3)))
        shop_coords = set(random.sample(mid_coords, num_shops))
        remaining = [c for c in mid_coords if c not in shop_coords]

        # 随机抽精英
        max_possible = min(max_elites, len(remaining))
        min_possible = min(min_elites, max_possible)
        num_elites = random.randint(min_possible, max_possible) if remaining else 0
        elite_coords = set(random.sample(remaining, num_elites)) if num_elites > 0 else set()
        remaining2 = [c for c in remaining if c not in elite_coords]

        # 随机抽 1 个作事件房
        num_events = min(1, len(remaining2)) if remaining2 else 0
        event_coords = set(random.sample(remaining2, num_events)) if num_events > 0 else set()

        for layer_idx in range(1, num_layers - 2):
            for node in layer_nodes[layer_idx]:
                coord = (layer_idx, node.position)
                if coord in shop_coords:
                    node.room_type = RoomType.SHOP
                elif coord in elite_coords:
                    node.room_type = RoomType.ELITE
                elif coord in event_coords:
                    node.room_type = RoomType.EVENT
                else:
                    node.room_type = RoomType.BATTLE

    def _connect_by_position(self, node: MapNode, next_layer: List[MapNode]) -> None:
        """连接下一层 position 最接近的 1~2 个节点（减少路线交叉）。

        策略: 按 position 差值排序，取最近的 1~2 个。
        """
        if not next_layer:
            return
        sorted_next = sorted(next_layer, key=lambda n: abs(n.position - node.position))
        num_connections = random.randint(1, min(2, len(sorted_next)))
        for target in sorted_next[:num_connections]:
            node.connections.add(target.node_id)

    def _build_layouts(self) -> List[RoomType]:
        """已弃用：保留兼容（实际改用 _assign_room_types）。"""
        return [RoomType.BATTLE] * self.num_layers

    def _ensure_reachability(self, layer_nodes: List[List[MapNode]]) -> None:
        """确保从第 0 层出发，所有节点可达（必要时添加连接）。"""
        reachable_ids: Set[str] = set()
        queue: List[str] = [n.node_id for n in layer_nodes[0]]
        while queue:
            nid = queue.pop(0)
            if nid in reachable_ids:
                continue
            reachable_ids.add(nid)
            node = self.get_node(nid)
            if node:
                for conn_id in node.connections:
                    if conn_id not in reachable_ids:
                        queue.append(conn_id)

        for layer_idx in range(1, len(layer_nodes)):
            for node in layer_nodes[layer_idx]:
                if node.node_id not in reachable_ids:
                    prev_layer = layer_nodes[layer_idx - 1]
                    connector = random.choice(prev_layer)
                    connector.connections.add(node.node_id)
                    reachable_ids.add(node.node_id)
                    logger.debug(
                        "[Map] 修复可达性: %s -> %s",
                        connector.node_id, node.node_id,
                    )

    # ------------------------------------------------------------------ #
    # 查询接口
    # ------------------------------------------------------------------ #
    def get_node(self, node_id: str) -> Optional[MapNode]:
        """根据 ID 获取节点。"""
        for node in self.nodes:
            if node.node_id == node_id:
                return node
        return None

    def get_layer_nodes(self, layer: int) -> List[MapNode]:
        """获取某一层的所有节点。"""
        return [n for n in self.nodes if n.layer == layer]

    def get_accessible_nodes(self) -> List[MapNode]:
        """获取当前可访问的节点。"""
        return [n for n in self.nodes if n.accessible and not n.visited]

    def get_current_node(self) -> Optional[MapNode]:
        """获取当前所在节点。"""
        if self.current_node_id is None:
            return None
        return self.get_node(self.current_node_id)

    def get_next_layer(self) -> int:
        """获取下一个可访问的层（最小层号）。"""
        accessible = self.get_accessible_nodes()
        if not accessible:
            return -1
        return min(n.layer for n in accessible)

    def move_to_node(self, node_id: str) -> MapNode:
        """移动到指定节点。

        修复（需求2）: 先清除所有节点的 accessible，再只设置当前节点下游连接为 accessible，
        确保玩家只能前进（不能走回头路）。

        Args:
            node_id: 目标节点 ID。

        Returns:
            目标节点。

        Raises:
            AssertionError: 当节点不可访问时触发。
        """
        node = self.get_node(node_id)
        assert node is not None, f"[Map] 节点不存在: {node_id}"
        assert node.accessible, f"[Map] 节点不可访问: {node_id}"
        assert not node.visited, f"[Map] 节点已访问: {node_id}"

        node.visited = True
        self.current_node_id = node_id

        # 清除所有节点的 accessible（防止回头路）
        for n in self.nodes:
            n.accessible = False

        # 只设置当前节点的下游连接为 accessible
        for conn_id in node.connections:
            conn_node = self.get_node(conn_id)
            if conn_node and not conn_node.visited:
                conn_node.accessible = True

        logger.info(
            "[Map] 移动到 %s (layer=%d, type=%s)",
            node_id, node.layer, node.room_type.value,
        )
        return node

    def is_complete(self) -> bool:
        """地图是否已完成（Boss 被击败）。"""
        boss_nodes = [
            n for n in self.nodes
            if n.room_type == RoomType.BOSS and n.visited
        ]
        return len(boss_nodes) > 0

    # ------------------------------------------------------------------ #
    # 状态快照
    # ------------------------------------------------------------------ #
    def get_state(self) -> dict:
        """获取地图状态快照（供 View 渲染）。"""
        return {
            "num_layers": self.num_layers,
            "nodes": self.nodes,
            "current_node_id": self.current_node_id,
            "accessible_nodes": self.get_accessible_nodes(),
            "is_complete": self.is_complete(),
        }