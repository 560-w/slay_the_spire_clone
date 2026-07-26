"""event.py: 事件系统基类。

设计原则:
1. GameEvent 定义事件场景，每个事件包含一个或多个选项。
2. EventOption 定义玩家的选择，包含文本、条件、回调。
3. 事件系统与 GameController 解耦，通过回调函数交互。
4. 事件在游戏地图的"事件房"中触发。

典型流程:
1. GameController 进入事件房 → 从事件池随机抽取一个 GameEvent
2. 玩家选择一个 EventOption
3. 执行回调 → 修改玩家状态（HP/金币/牌组/遗物）
4. 返回地图
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.controllers.game import GameController

logger = logging.getLogger(__name__)


@dataclass
class EventOption:
    """事件选项。

    Attributes:
        text: 选项描述文本。
        callback: 选择后执行的回调函数，接收 (game_controller, player) 参数。
        condition: 可选条件函数，返回 True 才显示该选项，None 表示始终显示。
        tooltip: 选项的悬停提示（预估结果）。
    """
    text: str
    callback: Callable[["GameController"], None]
    condition: Optional[Callable[["GameController"], bool]] = None
    tooltip: str = ""


class GameEvent(ABC):
    """事件抽象基类。

    属性:
        name: 事件名称。
        description: 事件场景描述文本。
        options: 可用选项列表。

    子类需在 __init__ 中调用 _setup_options() 初始化选项。
    """

    def __init__(self, name: str, description: str) -> None:
        assert isinstance(name, str) and name, "[Event] name 不能为空"
        assert isinstance(description, str) and description, "[Event] description 不能为空"

        self.name: str = name
        self.description: str = description
        self.options: List[EventOption] = []

        logger.debug("[Event] 创建事件: %s", self.name)

    def get_available_options(self, game: "GameController") -> List[EventOption]:
        """获取当前可用的选项（已过滤条件）。

        Args:
            game: 游戏控制器实例。

        Returns:
            满足条件的选项列表。
        """
        available: List[EventOption] = []
        for opt in self.options:
            if opt.condition is None or opt.condition(game):
                available.append(opt)
        return available

    def execute_option(self, option_idx: int, game: "GameController") -> None:
        """执行指定选项。

        Args:
            option_idx: 选项索引（0-based）。
            game: 游戏控制器实例。

        Raises:
            AssertionError: 当索引越界时触发。
        """
        available = self.get_available_options(game)
        assert 0 <= option_idx < len(available), (
            f"[Event] 选项索引越界: {option_idx}, 可用选项: {len(available)}"
        )
        option = available[option_idx]
        logger.info(
            "[Event] 执行事件 %s 选项: %s", self.name, option.text
        )
        option.callback(game)

    def __repr__(self) -> str:
        return f"<GameEvent {self.name}>"

    def __str__(self) -> str:
        return self.name