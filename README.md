# 杀戮尖塔克隆版

一款用 Python 开发的类杀戮尖塔 Roguelike 卡牌游戏。
严格遵循模块化、MVC 分层与防御性编程原则。

## 开发原则

1. 极端模块化与高内聚低耦合
2. 数据与表现分离（MVC）：核心逻辑与 UI 绝对解耦
3. 防御性编程：assert + logging 详尽记录

## 目录结构

slay_the_spire_clone/
+- main.py                         # 入口：pygame 主循环
+- src/
   +- core/                        # 核心层
   |  +- entity.py                 # Entity 基类
   |  +- card.py                   # Card 抽象基类（含词条）
   |  +- player.py                 # Player（能量+四类牌堆+处理区）
   |  +- enemy.py                  # Enemy（多意图模式）
   |  +- intent.py                 # Intent（敌人意图）
   |  +- buff_system.py            # BuffSystem（伤害/格挡修正+tick）
   |  +- status_effect.py           # StatusEffect 基类+注册表+7种效果
   |  +- card_effects.py            # CardEffects 工具类
   |  +- pending_action.py          # 挂起动作系统
   |  +- map.py                     # Map 地图系统（节点类型、Boss、随机生成）
   +- data/                        # 数据层
   |  +- cards.py                  # 11种范例卡牌
   |  +- enemies.py                 # 2种敌人
   +- controllers/
   |  +- battle.py                  # BattleController 战斗状态机
   |  +- game.py                    # GameController 游戏流程控制
   +- views/
      +- pygame_view.py            # pygame 图形界面（地图/战斗/奖励/篝火/商店/游戏结束）
      +- card_browser.py           # 通用卡牌浏览/选择模态窗口
      +- console.py                # 调试控制台（Shift+~ 切换）

## 快速开始

cd slay_the_spire_clone
python main.py

环境要求: Python 3.10+, pygame>=2.5.0

## 已实现功能

### Phase 1: 底层骨架
- Entity/Card/Player/Enemy 基类

### Phase 2: 战斗循环
- Intent 系统（多意图，攻击数值经 buff 修正展示）
- BattleController 状态机（玩家回合<->敌人回合<->胜负）
- 手动/自动打出分离，处理区栈结构（支持嵌套结算）
- pygame 界面（鼠标点击，敌人意图显示）

### Phase 3: 卡牌词条与状态效果

卡牌词条:
- 消耗 / 虚无 / 不能被打出 / 回合结束自动打出 / X费

状态效果（StatusEffect + 注册表）:
- 力量(+攻击伤害,可负) / 敏捷(+格挡,可负)
- 虚弱(攻击x0.75) / 易伤(受击x1.5) / 电击(回合结束扣血)
- 回合多抽 / 回合结束获得力量

范例卡牌:
- 打击/防御/重击/生存者/祭品/机器学习/灼伤/倾斜/全息影像/主宰/黑暗镣铐

UI 功能:
- 通用 CardBrowser 模态窗口（牌堆查看/选牌统一）
- 左下牌堆按钮 / 右侧战斗日志 / X费显示

### Phase 4: 卡牌库扩展
- 新增 10+ 张卡牌（含铁甲战士、静默猎人、故障机器人风格）
- 新增 2 种敌人（酸液史莱姆/尖刺史莱姆 + 史莱姆Boss）
- Boss 多阶段、Split 分裂机制
- 金币系统（gold）+ 商店购买卡牌
- 奖励系统（战斗胜利选卡/金币）
- 篝火系统（休息回血/升级卡牌）
- 游戏结束/通关界面

### Phase 5: 地图与 Roguelike 元素
- 随机地图生成（Map 系统，层级式节点图）
- 多种房间类型：战斗(⚔) / 精英(💀) / 篝火(🔥) / 商店(💰) / Boss(👑)
- GameController 完整游戏流程控制
- 地图界面渲染与节点选择

### Phase 6: 图形 UI 美化
- Emoji 图标映射（卡牌类型、敌人、Buff 效果）
- 调试控制台（Shift+~ 切换，支持运行时命令）
- 统一 pygame.display.flip() 到 main.py 主循环

## Git 协作约定

分支: main(稳定) / develop(集成) / feature-xxx / fix-xxx
Commit: type(scope): subject

## 开发路线

- [x] Phase 1: 底层骨架
- [x] Phase 2: 战斗循环
- [x] Phase 3: 卡牌词条与状态效果
- [x] Phase 4: 卡牌库扩展
- [x] Phase 5: 地图与 Roguelike 元素
- [x] Phase 6: 图形 UI 美化