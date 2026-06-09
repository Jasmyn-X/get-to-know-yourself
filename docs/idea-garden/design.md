# 想法花园（Idea Garden）产品设计文档

**日期**: 2026-06-09  
**状态**: 已批准，待实现  
**项目类型**: 全新独立项目（与 XHS 提取管道完全隔离）  
**实现目录**: `<workspace>/idea-garden/`（独立 Next.js 项目）

---

## 一、产品概述

### 核心问题

拖延症的完整心理链条：

> 自发愿望 → 变成"任务" → 触发畏难和被控制的反抗 → 找借口 → 即时舒适获胜 → 自我谴责 → "明天加倍"的幻想 → 更大任务压力 → 更强逃避

传统效率工具在「任务→反抗」这一步加剧了问题。

### 设计哲学

> **启动了已经很好了。**

每一次打开即胜利，每一次启动即成长，每一次结束即完成而非失败。

### 产品定位

一个极简「实验助手」，不是效率软件。通过「实验许可证」机制，将「做任务」重新框架为「收集体验数据」，绕过心理反抗，降低启动门槛至接近零。

**目标用户**：有很多想法、启动困难、热情不持续、会自我谴责的创造者。  
**首发形态**：个人自用 Web App（PWA）。  
**后续形态**：对外公开产品。

---

## 二、核心功能

### 功能 1：想法孵化器（浮动气泡）

**目标**：让捕捉想法的成本趋近于零，不做任何判断和排序。

- 主屏下方展示最近若干浮动想法，气泡形态，无排序
- 捕捉路径：PWA 桌面快捷方式 / 手机主屏组件 → 打开即输入框 → 一句话 → 存入 → 关闭，全程 < 10 秒
- 捕捉时**只需一个字段**：想法内容。不问 why/fear/firstStep
- 想法状态流转：`floating → activating → in_experiment → archived`；或 `floating → frozen`

### 功能 2：实验许可证生成器

**目标**：用「实验」而非「目标」重新框架行动，消除失败感。

激活流程（全程点选，无需打字）：

```
选一个浮动想法
  → 3 个 why 选项（AI 生成）→ 点选
  → 4 个 fear 标签（枚举）→ 多选：怕累 / 怕没时间 / 怕做不好 / 怕坚持不住
  → 3 个 firstStep 选项（AI 生成，最小行动量级）→ 点选
  → 选陪伴物：植物 or 动物（见功能 5）
  → 拖动天数滑块（默认 7 天，选项：3 / 7 / 14 / 21）
  → 「实验许可证」卡片生成动画
  → 实验开始
```

许可证卡片文案模板：
> 我许可自己，进行一次关于「XX」的纯体验实验。目的只是收集「这件事是什么感觉」的数据。无论是否继续，实验都已成功。

### 功能 3：单任务实验区（每日签到）

**目标**：专注一件事，每天最小投入即可维持实验。

- 同时进行的实验数量：用户可设定（默认 1，超出时提示但不阻断）
- **三层签到路径**（用户自选深度）：

| 路径 | 时长 | 操作 | 反馈 |
|------|------|------|------|
| 最小 | 30 秒 | 点「今天已出发 ✓」 | 陪伴物动一下，连击数 +1 |
| 标准 | 1-2 分钟 | 输一句今日最小数据 | 陪伴物成长一级 |
| 深度 | 5 分钟 | 数据 + 能量感受 + 自由反思 | 解锁洞察卡片 |

- 每日一问占位文字示例（轮换）：「今天收集的最小数据是什么？」「有什么让你意外的发现？」「今天做了还是没做？都可以写」
- **绝不出现**：「你今天还没完成任务」类措辞

### 功能 4：荣耀档案馆（荣耀谢幕）

**目标**：用「已探索」替代「已放弃」，每次结束都是胜利。

冷却触发：
- 连续 3 天未签到，或用户主动点「结束实验」
- 系统温和提示：「你的实验进入了冷却期，要做个简短的回顾吗？」

荣耀谢幕流程（< 1 分钟）：

```
感受标签（多选）→ 最爽瞬间（AI 建议句，一键采用或编辑）
  → 学到的（AI 建议句）→「已探索」印章盖下
  → 陪伴物最终动画 → 归入档案馆
  → 系统静默设置：3 个月后重新出现在灵感潜水池
```

归档后展示：档案馆是一排「书」的视觉，每本书代表一次实验，点开可回看。

### 功能 5：陪伴物（轻量养成）

**目标**：提供持续正反馈，不增加心理负担。

- 第一次激活实验时选择陪伴物类型：**植物**（花 / 仙人掌 / 竹 / 苔藓球）或 **动物**（猫 / 兔 / 龙猫 / 小怪）
- 成长阶段（5 级）：种子 → 发芽 → 小苗 → 开花 → 盛放
- 规则：
  - 每次签到 → 成长
  - 冷却期 → 休眠（蜷缩，**不死**，不惩罚）
  - 实验归档 → 陪伴物留在花园（可回看历史）
  - 新实验可选旧陪伴物继续或选新的
- 陪伴物不与「失败」挂钩，只响应正向行动

### 功能 6：灵感潜水池（平台收藏导入）

**目标**：通过分析收藏数据反推真实渴望，绕过「想太多」和「选择恐惧」。

**V1（MVP）**：文件导入
- 支持 JSON / CSV 上传（XHS pipeline 输出 / B 站手动导出 / 自定义格式）
- 上传 → 关键词聚类 → 主题气泡图
- 每个主题：点开看代表收藏 → 「一键生成实验候选」

**V2（后续）**：
- 小红书直连（复用 get-to-know-yourself 项目的 Python pipeline 输出 JSON）
- Bilibili 直连（bilibili-api + cookie 授权）

**V3（远期）**：
- 抖音（待社区出稳定方案）

**时间胶囊机制**：
- 归档满 3 个月的实验，若灵感池出现类似主题 → 浮现提示：「3 个月前你探索过 XX，现在又收藏了类似内容——要重新开始吗？」

### 功能 7：通知策略

- **情景化问候**（非命令）：基于收藏聚类推送 → 「你最近收藏了 12 个舞蹈视频，你在期待什么？」
- **柔和进度提示**：「实验第 5 天了，你的小苗在等你」
- **用户可设定**固定时间提醒（默认关）
- **绝不出现**：任务未完成类措辞

---

## 三、数据模型

```typescript
// 想法（捕捉时只需 content）
interface Idea {
  id: string
  content: string
  status: 'floating' | 'activating' | 'in_experiment' | 'frozen' | 'archived'
  capturedAt: string // ISO 8601
}

// 实验草稿（激活流中临时保存）
interface ExperimentDraft {
  id: string
  ideaId: string
  why: string           // 从 AI 建议中点选
  fearTags: FearTag[]   // 'tired' | 'no_time' | 'not_good_enough' | 'cant_persist'
  firstStep: string     // 从 AI 建议中点选
  durationDays: number  // 3 | 7 | 14 | 21
  companionType: 'plant' | 'animal'
  companionVariant: string // 'flower' | 'cactus' | 'bamboo' | 'moss' | 'cat' | 'rabbit' | 'totoro' | 'creature'
}

// 进行中的实验
interface Experiment {
  id: string
  ideaId: string
  draftId: string
  companionStage: 0 | 1 | 2 | 3 | 4 | 5
  startDate: string
  durationDays: number
  dailyLogs: DailyLog[]
  status: 'active' | 'cooling' | 'completed'
}

interface DailyLog {
  date: string
  minData: string | null  // 可为空（最小路径）
  energyTag: 'high' | 'medium' | 'low' | null
}

// 档案馆
interface Archive {
  id: string
  experimentId: string
  ideaId: string
  bestMoment: string
  learned: string
  restartStep: string
  exploredAt: string
  resurfaceAt: string  // exploredAt + 90 天
}

// 平台导入
interface PlatformImport {
  id: string
  source: 'xhs' | 'bilibili' | 'douyin' | 'file'
  importedAt: string
  rawData: string       // JSON 字符串，备用
  clusters: Cluster[]
  suggestions: string[] // 推荐实验候选
}

interface Cluster {
  name: string
  count: number
  topItems: string[]
}
```

---

## 四、页面路由

```
/                    主屏（陪伴物 + 签到 + 浮动想法气泡）
/capture             快捷捕捉（PWA 快捷方式入口，极简）
/activate            激活实验流（多步引导）
/experiment          当前实验详情 + 签到
/garden              花园总览（所有陪伴物历史）
/archive             档案馆（历次实验回顾）
/archive/[id]        单次实验详情
/pool                灵感潜水池（收藏导入 + 聚类展示）
/pool/import         导入流程
/settings            通知偏好 + 陪伴物上限设置
```

---

## 五、技术栈

| 层 | 选型 | 理由 |
|----|------|------|
| 框架 | Next.js 15 App Router | 全栈，个人→公开路径顺畅 |
| 数据库 | better-sqlite3（本地）/ Turso（部署） | 零配置启动，可无缝迁移 |
| UI 组件 | shadcn/ui | 可定制，不像默认模板 |
| 动画 | Framer Motion | 陪伴物成长动画 |
| PWA | next-pwa | 支持桌面快捷方式 / 离线 |
| AI 辅填 | Claude API（Haiku 4.5） | 生成 why/firstStep 建议句，成本低 |
| 聚类分析 | 复用 get-to-know-yourself Python pipeline 输出 JSON，或 Node.js 侧 simple-statistics + jieba-wasm |
| 样式 | Tailwind CSS + CSS 自定义属性 | 设计 token 集中管理 |

---

## 六、视觉方向

- **气质**：介于治愈系和轻游戏之间，温暖但有趣
- **色彩**：暖色基调，避免冷硬极简；陪伴物用自然色系
- **交互**：气泡浮现、卡片打印机动效、印章盖下、陪伴物微动画
- **文案语气**：像一个不评判的朋友，不说「你应该」，只说「你可以」

---

## 七、项目结构

```
idea-garden/                  ← 独立项目，与 get-to-know-yourself 隔离
├── app/
│   ├── page.tsx              主屏
│   ├── capture/page.tsx      快捷捕捉
│   ├── activate/page.tsx     激活流
│   ├── experiment/page.tsx   当前实验
│   ├── garden/page.tsx       花园总览
│   ├── archive/page.tsx      档案馆
│   ├── pool/page.tsx         灵感潜水池
│   └── settings/page.tsx     设置
├── components/
│   ├── companion/            陪伴物动画组件
│   ├── idea-bubble/          想法气泡
│   ├── experiment-card/      实验许可证卡片
│   └── ui/                   shadcn 基础组件
├── lib/
│   ├── db.ts                 SQLite 连接
│   ├── ai.ts                 Claude API 调用（建议句生成）
│   └── cluster.ts            聚类分析
├── actions/                  Server Actions
└── public/
    └── manifest.json         PWA manifest
```

---

## 八、与现有项目的关系

| 项目 | 职责 | 关系 |
|------|------|------|
| `get-to-know-yourself` | XHS 收藏提取 → 知识库 / Obsidian | 独立运行，可选数据来源 |
| `idea-garden` | 想法捕捉 → 实验管理 → 档案 | 独立项目 |
| 集成点 | XHS pipeline 输出的 JSON 文件 | 由用户手动上传到灵感潜水池（V1），或直连（V2） |

---

## 九、MVP 范围

### 第一期（核心体验）
- 功能 1：想法孵化器
- 功能 2：实验许可证生成器（含 AI 辅填）
- 功能 3：单任务实验区（三层签到）
- 功能 4：荣耀档案馆
- 功能 5：陪伴物基础版（植物/动物，5 级成长）
- PWA 支持

### 第二期
- 功能 6：灵感潜水池（文件导入 V1）
- 时间胶囊重新浮现
- 深度反思 + 洞察卡片

### 后续
- XHS / Bilibili 直连
- 对外公开（用户系统）
