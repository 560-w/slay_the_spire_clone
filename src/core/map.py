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
        }
        return icons.get(self.room_type, "?")

    @property
    def display_name(self) -> str:
        """获取用于 UI 显示的名称。"""
        return self.room_type.value


class Map:
    """地图生成器。

    生成规则（节点级别分配类型，需求7）:
    - Layer 0: 全部战斗
    - Layer 1~4: 每层 2~3 个节点，随机抽 1~2 个坐标作商店、1~2 个作精英，其余战斗
    - Layer 5: 全部篝火
    - Layer 6: Boss（固定 1 个）
    - 连接: 每个节点连接下一层 position 最接近的 1~2 个节点（减少交叉）
    - 玩家从第 0 层开始，每行只能选一个节点前进（不允许回头路）
    """

    def __init__(
        self, num_layers: int = 7, seed: Optional[int] = None
    ) -> None:
        assert num_layers >= 3, "[Map] 层数至少为 3"
        self.num_layers: int = num_layers
        self.nodes: List[MapNode] = []
        self.current_node_id: Optional[str] = None
        self._counter: int = 0

        if seed is not None:
            random.seed(seed)

        self._generate()

    def _next_id(self) -> str:
        """生成唯一节点 ID。"""
        self._counter += 1
        return f"node_{self._counter}"

    def _generate(self) -> None:
        """生成整个地图（节点级别分配类型 + 路线不交叉）。"""
        self.nodes = []

        # 生成各层节点（先全部设为战斗，后续按节点级别覆盖类型）
        layer_nodes: List[List[MapNode]] = []
        for layer_idx in range(self.num_layers):
            nodes_in_layer: List[MapNode] = []
            if layer_idx == self.num_layers - 1:
                # Boss 层固定 1 个
                count = 1
            elif layer_idx == self.num_layers - 2:
                # 篝火层：2 个
                count = 2
            else:
                count = random.randint(2, 3)
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

        # 按节点级别分配类型
        self._assign_room_types(layer_nodes)

        # 连接相邻层（position 优先，减少交叉）
        for layer_idx in range(len(layer_nodes) - 1):
            current_layer = layer_nodes[layer_idx]
            next_layer = layer_nodes[layer_idx + 1]
            for node in current_layer:
                self._connect_by_position(node, next_layer)

        # 确保所有节点可达（从第 0 层 BFS）
        self._ensure_reachability(layer_nodes)

        # 设置第 0 层所有节点为 accessible
        for node in layer_nodes[0]:
            node.accessible = True

        logger.info(
            "[Map] 地图生成完成: %d 层, %d 个节点",
            self.num_layers, len(self.nodes),
        )

    def _assign_room_types(self, layer_nodes: List[List[MapNode]]) -> None:
        """按节点级别分配房间类型（需求7）。

        - Layer 0: 全部战斗
        - 中间层(1 ~ num_layers-3): 随机抽 1~2 个坐标作商店、1~2 个作精英，其余战斗
        - Layer num_layers-2: 全部篝火
        - Layer num_layers-1: 全部 Boss（已固定 1 个）
        """
        num_layers = len(layer_nodes)
        # 固定层
        for node in layer_nodes[0]:
            node.room_type = RoomType.BATTLE
        for node in layer_nodes[num_layers - 2]:
            node.room_type = RoomType.CAMPFIRE
        for node in layer_nodes[num_layers - 1]:
            node.room_type = RoomType.BOSS

        # 中间层：收集所有 (layer, position) 坐标
        mid_coords: list[tuple[int, int]] = []
        for layer_idx in range(1, num_layers - 2):
            for node in layer_nodes[layer_idx]:
                mid_coords.append((layer_idx, node.position))

        if mid_coords:
            # 随机抽 1~2 个作商店
            num_shops = random.randint(1, min(2, max(1, len(mid_coords) // 2)))
            shop_coords = set(random.sample(mid_coords, num_shops))
            remaining = [c for c in mid_coords if c not in shop_coords]
            # 随机抽 1~2 个作精英
            num_elites = random.randint(1, min(2, max(1, len(remaining) // 2))) if remaining else 0
            elite_coords = set(random.sample(remaining, num_elites)) if num_elites > 0 else set()

            for layer_idx in range(1, num_layers - 2):
                for node in layer_nodes[layer_idx]:
                    coord = (layer_idx, node.position)
                    if coord in shop_coords:
                        node.room_type = RoomType.SHOP
                    elif coord in elite_coords:
                        node.room_type = RoomType.ELITE
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