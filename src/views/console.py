"""console.py: 调试控制台。

用 ~ 键呼出/收起，支持输入指令进行调试：
- add_card <类名>           向手牌添加卡牌
- remove_card <索引>         从手牌移除卡牌
- add_buff <目标> <buff> <层数>  给予buff
- remove_buff <目标> <buff> [层数] 移除buff
- set_hp <目标> <数值>       设置HP
- set_energy <数值>         设置能量
- set_block <目标> <数值>    设置护甲
- kill <目标>               击杀目标
- list_cards                列出可用卡牌类名
- help                      显示帮助

目标格式: player / enemy0 / enemy1 / enemy2 ...
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable

import pygame

from src.data.cards import (
    Bash, Burn, Dazed, Defend, DarkShackles, Domination,
    Hologram, MachineLearning, Offering, Strike, Survivor, Whirlwind, Wound,
)

if TYPE_CHECKING:
    from src.controllers.battle import BattleController

logger = logging.getLogger(__name__)

# 卡牌类名注册表
CARD_REGISTRY = {
    "Strike": Strike, "Defend": Defend, "Bash": Bash,
    "Survivor": Survivor, "Offering": Offering,
    "MachineLearning": MachineLearning, "Burn": Burn,
    "Whirlwind": Whirlwind, "Hologram": Hologram,
    "Domination": Domination, "DarkShackles": DarkShackles,
    "Wound": Wound, "Dazed": Dazed,
}

# 控制台配色
COLOR_CONSOLE_BG = (20, 20, 30, 220)
COLOR_INPUT_BG = (40, 40, 50)
COLOR_TEXT = (240, 240, 240)
COLOR_PROMPT = (100, 255, 100)
COLOR_ERROR = (255, 100, 100)
COLOR_INFO = (100, 200, 255)


class DebugConsole:
    """调试控制台。

    属性:
        active (bool): 是否激活
        input_text (str): 当前输入文本
        history (list[tuple[str, tuple]]): 历史输出 (text, color)
        battle: 战斗控制器引用
        max_history (int): 最大历史条数
    """

    def __init__(self) -> None:
        self.active: bool = False
        self.input_text: str = ""
        self.history: list[tuple[str, tuple[int, int, int]]] = []
        self.battle: "BattleController | None" = None
        self.max_history: int = 15

    def toggle(self) -> None:
        """切换控制台激活状态。"""
        self.active = not self.active
        self.input_text = ""
        if self.active:
            pygame.key.start_text_input()
            self._print("调试控制台已激活，输入 help 查看命令", COLOR_INFO)
        else:
            pygame.key.stop_text_input()

    def handle_keydown(self, event: pygame.event.Event) -> bool:
        """处理键盘输入（控制台激活时调用）。

        Returns:
            True 表示事件已处理（阻止底层游戏交互）。
        """
        if not self.active:
            return False

        if event.key == pygame.K_RETURN:
            self._execute_command(self.input_text)
            self.input_text = ""
            return True

        if event.key == pygame.K_BACKSPACE:
            self.input_text = self.input_text[:-1]
            return True

        if event.key == pygame.K_ESCAPE:
            self.active = False
            self.input_text = ""
            pygame.key.stop_text_input()
            return True

        # 可打印字符（用 TEXTINPUT 事件更可靠，但 KEYDOWN 的 unicode 也可用）
        if event.unicode and event.unicode.isprintable() and event.key != pygame.K_BACKQUOTE:
            self.input_text += event.unicode
            return True

        return True  # 屏蔽其他键

    def handle_text_input(self, text: str) -> None:
        """处理 TEXTINPUT 事件的字符输入。"""
        if self.active and text:
            self.input_text += text

    def render(self, screen: pygame.Surface, font: pygame.font.Font,
               font_small: pygame.font.Font) -> None:
        """渲染控制台（仅激活时）。"""
        if not self.active:
            return

        w, h = screen.get_size()
        console_h = 200
        console_y = h - console_h

        # 背景
        overlay = pygame.Surface((w, console_h), pygame.SRCALPHA)
        overlay.fill(COLOR_CONSOLE_BG)
        screen.blit(overlay, (0, console_y))

        # 历史输出
        y = console_y + 5
        for text, color in self.history[-self.max_history:]:
            surf = font_small.render(text, True, color)
            screen.blit(surf, (10, y))
            y += 18

        # 输入框
        input_y = h - 35
        pygame.draw.rect(screen, COLOR_INPUT_BG, (0, input_y, w, 35))
        prompt = font.render(f"> {self.input_text}_", True, COLOR_PROMPT)
        screen.blit(prompt, (10, input_y + 5))

    # ------------------------------------------------------------------ #
    # 指令执行
    # ------------------------------------------------------------------ #
    def _execute_command(self, raw: str) -> None:
        """解析并执行命令。"""
        raw = raw.strip()
        if not raw:
            return
        self._print(f"> {raw}", COLOR_TEXT)
        parts = raw.split()
        cmd = parts[0].lower()
        args = parts[1:]

        if self.battle is None:
            self._print("错误: 无战斗引用", COLOR_ERROR)
            return

        try:
            if cmd == "help":
                self._print_help()
            elif cmd == "list_cards":
                self._print("可用卡牌: " + ", ".join(CARD_REGISTRY.keys()), COLOR_INFO)
            elif cmd == "add_card":
                self._cmd_add_card(args)
            elif cmd == "remove_card":
                self._cmd_remove_card(args)
            elif cmd == "add_buff":
                self._cmd_add_buff(args)
            elif cmd == "remove_buff":
                self._cmd_remove_buff(args)
            elif cmd == "set_hp":
                self._cmd_set_hp(args)
            elif cmd == "set_energy":
                self._cmd_set_energy(args)
            elif cmd == "set_block":
                self._cmd_set_block(args)
            elif cmd == "kill":
                self._cmd_kill(args)
            else:
                self._print(f"未知命令: {cmd}，输入 help 查看帮助", COLOR_ERROR)
        except Exception as e:
            self._print(f"错误: {e}", COLOR_ERROR)

    def _print(self, text: str, color=(240, 240, 240)) -> None:
        """输出到历史区。"""
        self.history.append((text, color))

    def _print_help(self) -> None:
        """显示帮助。"""
        cmds = [
            "add_card <类名> - 向手牌添加卡牌",
            "remove_card <索引> - 从手牌移除卡牌",
            "add_buff <目标> <buff名> <层数> - 给予buff",
            "remove_buff <目标> <buff名> [层数] - 移除buff",
            "set_hp <目标> <数值> - 设置HP",
            "set_energy <数值> - 设置能量",
            "set_block <目标> <数值> - 设置护甲",
            "kill <目标> - 击杀目标",
            "list_cards - 列出可用卡牌类名",
            "目标: player / enemy0 / enemy1 ...",
        ]
        for c in cmds:
            self._print(c, COLOR_INFO)

    def _get_target(self, target_str: str):
        """解析目标字符串为实体。"""
        if target_str == "player":
            return self.battle.player
        if target_str.startswith("enemy"):
            idx = int(target_str[5:])
            if 0 <= idx < len(self.battle.enemies):
                return self.battle.enemies[idx]
            raise ValueError(f"敌人索引越界: {idx}")
        raise ValueError(f"未知目标: {target_str}")

    def _cmd_add_card(self, args) -> None:
        if not args:
            raise ValueError("用法: add_card <类名>")
        card_name = args[0]
        if card_name not in CARD_REGISTRY:
            raise ValueError(f"未知卡牌: {card_name}，用 list_cards 查看")
        card = CARD_REGISTRY[card_name]()
        self.battle.player.hand.append(card)
        self._print(f"添加卡牌 {card_name} 到手牌", COLOR_INFO)

    def _cmd_remove_card(self, args) -> None:
        if not args:
            raise ValueError("用法: remove_card <索引>")
        idx = int(args[0])
        if 0 <= idx < len(self.battle.player.hand):
            card = self.battle.player.hand.pop(idx)
            self._print(f"移除手牌[{idx}]: {card.name}", COLOR_INFO)
        else:
            raise ValueError(f"手牌索引越界: {idx}")

    def _cmd_add_buff(self, args) -> None:
        if len(args) < 3:
            raise ValueError("用法: add_buff <目标> <buff名> <层数>")
        target = self._get_target(args[0])
        buff_name = args[1]
        stacks = int(args[2])
        target.add_buff(buff_name, stacks)
        self._print(f"{args[0]} 获得 {buff_name}×{stacks}", COLOR_INFO)

    def _cmd_remove_buff(self, args) -> None:
        if len(args) < 2:
            raise ValueError("用法: remove_buff <目标> <buff名> [层数]")
        target = self._get_target(args[0])
        buff_name = args[1]
        if len(args) >= 3:
            stacks = int(args[2])
            target.remove_buff(buff_name, stacks)
            self._print(f"{args[0]} 移除 {buff_name}×{stacks}", COLOR_INFO)
        else:
            target.remove_buff(buff_name)
            self._print(f"{args[0]} 移除全部 {buff_name}", COLOR_INFO)

    def _cmd_set_hp(self, args) -> None:
        if len(args) < 2:
            raise ValueError("用法: set_hp <目标> <数值>")
        target = self._get_target(args[0])
        hp = int(args[1])
        target.current_hp = max(0, min(hp, target.max_hp))
        self._print(f"{args[0]} HP 设为 {target.current_hp}", COLOR_INFO)

    def _cmd_set_energy(self, args) -> None:
        if not args:
            raise ValueError("用法: set_energy <数值>")
        energy = int(args[0])
        self.battle.player.current_energy = max(0, energy)
        self._print(f"能量设为 {self.battle.player.current_energy}", COLOR_INFO)

    def _cmd_set_block(self, args) -> None:
        if len(args) < 2:
            raise ValueError("用法: set_block <目标> <数值>")
        target = self._get_target(args[0])
        block = int(args[1])
        target.block = max(0, block)
        self._print(f"{args[0]} 护甲设为 {target.block}", COLOR_INFO)

    def _cmd_kill(self, args) -> None:
        if not args:
            raise ValueError("用法: kill <目标>")
        target = self._get_target(args[0])
        target.current_hp = 0
        self._print(f"{args[0]} 已击杀", COLOR_INFO)
        self.battle.check_victory()