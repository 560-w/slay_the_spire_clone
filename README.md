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
   +- data/                        # 数据层
   |  +- cards.py                  # 11种范例卡牌
   |  +- enemies.py                 # 2种敌人
   +- controllers/battle.py        # BattleController 战斗状态机
   +- views/
      +- pygame_view.py            # pygame 简易界面
      +- card_browser.py           # 通用卡牌浏览/选择模态窗口

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

## Git 协作约定

分支: main(稳定) / develop(集成) / feature-xxx / fix-xxx
Commit: type(scope): subject

## 开发路线

- [x] Phase 1: 底层骨架
- [x] Phase 2: 战斗循环
- [x] Phase 3: 卡牌词条与状态效果
- [ ] Phase 4: 卡牌库扩展
- [ ] Phase 5: 地图与 Roguelike 元素
- [ ] Phase 6: 图形 UI 美化
