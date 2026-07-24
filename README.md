# 《杀戮尖塔》克隆版

一款用 Python 开发的类《杀戮尖塔》（Slay the Spire）Roguelike 卡牌游戏。
本项目采用结对编程方式开发，严格遵循模块化、MVC 分层与防御性编程原则。

## 开发原则

1. **极端模块化与高内聚低耦合**：禁止所有代码堆在一个文件，严格按 OOP 分离模块。
2. **数据与表现分离（MVC）**：核心逻辑（状态机、数值结算、卡牌效果）与 UI 表现层绝对解耦。优先跑通纯文本/终端战斗循环，再接入 UI。
3. **防御性编程**：关键逻辑（扣能量、目标选择、状态结算）使用 `assert` 与 `logging` 详尽记录，便于查错。

## 目录结构

```
slay_the_spire_clone/
├── main.py                # 入口：Phase 1 打印测试（无战斗循环）
├── README.md              # 项目说明与协作约定
├── requirements.txt       # Python 依赖
├── .gitignore
├── src/                   # 源代码主目录
│   ├── core/              # 【核心层】纯逻辑（Model），与 UI 无关
│   │   ├── entity.py      # Entity 基类（HP/护甲/Buff/受击结算）
│   │   ├── card.py        # Card 抽象基类（费用/名字/类型/抽象 play）
│   │   ├── player.py      # Player 类（能量 + 四类牌堆管理）
│   │   └── enemy.py       # Enemy 类（继承 Entity，预留意图/AI 钩子）
│   ├── data/              # 【数据层】具体卡牌/敌人定义（未来扩展）
│   ├── controllers/       # 【控制层】战斗流程控制（未来扩展）
│   └── views/             # 【表现层】UI 渲染（未来扩展）
└── tests/                 # 单元测试（未来扩展）
```

## 快速开始

```bash
# 进入项目目录
cd slay_the_spire_clone

# 运行 Phase 1 骨架测试（Windows cmd 中文乱码时指定 UTF-8）
python main.py
# 或
set PYTHONIOENCODING=utf-8 && python main.py
```

### 环境要求
- Python 3.10+（使用了 `X | None` 类型语法）
- Phase 1 仅使用标准库，无需额外依赖

## Git 协作约定

### 分支策略（轻量版 Git Flow）

| 分支 | 用途 | 规则 |
|------|------|------|
| `main` | 稳定可运行版本 | 只通过 PR 合入，禁止直接 push |
| `develop` | 开发集成分支 | 日常开发基准 |
| `feature/xxx` | 新功能分支 | 如 `feature/player-class` |
| `fix/xxx` | 修 bug 分支 | 如 `fix/block-calculation` |

### Commit 规范（Conventional Commits）

```
<type>(<scope>): <subject>

type:   feat / fix / docs / refactor / test / chore
scope:  模块名，如 core、player、card
示例:   feat(core): 实现 Entity 基类与受击结算
        fix(player): 修复能量超支断言失效
```

### 日常协作流程

```bash
# 开始工作前
git checkout develop && git pull origin develop
git checkout -b feature/your-task

# 工作中：频繁小提交
git add <具体文件> && git commit -m "feat(card): 添加抽象 play 方法"

# 推送并创建 PR
git push -u origin feature/your-task

# 合并后清理
git checkout develop && git pull && git branch -d feature/your-task
```

## 开发路线

- [x] **Phase 1**：底层骨架（Entity/Card/Player/Enemy 基类 + 打印测试）
- [ ] **Phase 2**：战斗循环控制器（回合状态机、敌人 AI、buff 结算）
- [ ] **Phase 3**：数据层（具体卡牌/敌人定义、卡组构建）
- [ ] **Phase 4**：终端 UI 表现层
- [ ] **Phase 5**：地图与 Roguelike 元素
- [ ] **Phase 6**：图形 UI（可选）