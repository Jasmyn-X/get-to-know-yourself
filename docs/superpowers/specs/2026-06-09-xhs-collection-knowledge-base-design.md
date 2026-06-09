# 小红书收藏夹 → Obsidian 知识库 + 兴趣方向分析 设计文档

- 日期: 2026-06-09
- 状态: 已批准设计,待实现计划
- 项目: get-to-know-yourself

## 1. 目标

把小红书个人收藏夹(近 2 年)的内容导出为结构化的 Obsidian Markdown 知识库,
自动发现主题分类,并分析近期高频收藏方向与兴趣迁移趋势。可选地把分类结果回写
到小红书收藏专辑。

成功标准:

1. 近 2 年收藏笔记完整落地为 `vault/notes/*.md`,含 YAML frontmatter。
2. 视频笔记带本地生成的逐字稿(零 LLM token)。
3. 笔记被自动聚类并打上主题分类/标签。
4. 生成"近 2 年方向分析报告 + 趋势图表"。
5. 提供可选、风险隔离的回写小红书专辑能力(默认 dry-run)。

## 2. 关键决策

| 维度 | 选择 | 理由 |
|---|---|---|
| 数据获取 | **xiaohongshu-cli 为主** + hc-tec Boards 方式补抓收藏专辑分组 | 复用成熟反检测/JSON 信封,少写脆弱逆向代码;补全 `folder` 分组 |
| 分类范围 | 本地 AI 自动发现分类 + 可选回写小红书专辑 | 主流程安全;回写隔离为独立高风险阶段 |
| 内容深度 | 标准版:元数据 + 正文 + 图片链接 + 精选评论 | 分析够准,抓取风险可控 |
| 视频逐字稿 | 下载音频轨 → 本地 faster-whisper(复用 hc-tec whisper skill) | 零 token、零账号互动风险 |
| 分析产出 | .md 报告 + 静态趋势图表 + **Obsidian 原生 Graph View 知识图谱** | 直观;知识图谱用 wikilink+MOC 免开发 |
| 分析范围 | 近 2 年全量 + 按月/季趋势 | 既看整体方向,也看兴趣迁移 |
| 嵌入/分类 | 本地 **BGE-small-zh** 嵌入 + **K-Means++** 聚类 + **Opus** 簇命名(按簇批处理) | 借鉴 RedNote_AI 架构;质量优先且 token 可控 |
| 分析模型 | **Haiku** 生成报告解读 | 总结性文字,够用且省 |
| 增量状态 | **SQLite** 记录已处理/已分类 | 借鉴 LclRobin;比 JSON 更适合增量重跑 |
| 架构 | 方案 A:分阶段 Python 脚本 + 分析 Notebook | 每步可独立重跑、断点续传;回写天然隔离 |

## 2.5 复用与参考的开源项目(2026-06-09 调研)

| 阶段 | 项目 | 复用内容 | 方式 |
|---|---|---|---|
| 0+1 | jackwener/xiaohongshu-cli | `xhs login/favorites/read/comments`,反检测,`ok/data/error` JSON 信封 | pip 安装,作底层引擎 |
| 1 | hc-tec/my-collection-skills | 收藏专辑/Boards 枚举;"读 hydrated state 而非脆弱 DOM"原则 | 补抓 `folder` 分组 |
| 1 | zhulin025/xiaohongshu-exporter | 范围分批(N..M)、暂停续传、本地缓存去重、失败重试 | 借鉴健壮性模式 |
| 2 | hc-tec `media-audio-download` + `whisper-transcribe-docker` | 音频下载 + faster-whisper | 直接复用 skill |
| 3 | bnchiang96/xiaohongshu-importer | Obsidian 字段集、按分类文件夹层级、媒体下载/外链开关、explore↔item URL 归一化 | 借鉴格式约定 |
| 3 | nonomil/XiaoHongshu_Collection | `input→fetch→enrich→write→report`;enrich 失败降级策略 | 借鉴降级策略 |
| 4 | aaaaaaaaaaaxi/RedNote_AI | BGE-small-zh 嵌入 + K-Means++ + LLM 簇命名,模块拆分 | 架构照搬(改 Python) |
| 4 | LclRobin/xhs-auto-organizer | SQLite 增量;LLM 分类 ≤50 条/批 | 借鉴状态管理 |
| 6 | LclRobin/xhs-auto-organizer | 回写=取消收藏→重新收藏→选专辑;专辑名须完全一致;首次 headless:false;debug 弹窗 DOM | 移植机制 |

## 3. 不做(YAGNI / 范围外)

- 不做一体化 CLI / yaml 全自动编排(方案 B)。
- 不做 Claude Code skill 驱动抓取(方案 C)。
- 不做交互式网页 dashboard 或 D3 知识图谱(知识图谱改用 Obsidian 原生 Graph View)。
- 不通过小红书 @问一问 生成逐字稿(账号互动风险高、不可控)。
- 不抓取超过 2 年的历史收藏(除趋势对比所需的时间统计)。

## 4. 管线总览与数据流

六个独立阶段,中间用 JSON 衔接,每步可单独重跑(`--resume`):

```
[0 auth]       xiaohongshu-cli 登录 (xhs login / status)         → cli 自管 cookie
[1 fetch]      xhs favorites 平铺列表 + xhs read/comments 详情     → data/raw_notes.json
               + hc-tec Boards 方式补抓收藏专辑分组 (folder)
               (近2年过滤 / 限速 / SQLite 续传去重)
[2 transcribe] 视频笔记: 下音频轨 → faster-whisper (hc-tec skill) → data/transcripts/{id}.txt
[3 to_obsidian] 合并渲染 .md (YAML frontmatter + wikilink)        → vault/notes/<分类>/*.md
[4 classify]   BGE-small-zh 嵌入 → K-Means++ 聚类 → Opus 簇命名    → SQLite + 回写 .md tags/categories
[5 analyze]    近2年方向 + 趋势 → 报告 + 静态图表 (Haiku 解读)      → vault/analysis/*
               + 生成分类 MOC 笔记 → Obsidian Graph View 知识图谱
[6 writeback]  ★可选/手动: 取消收藏→重收藏→选专辑 (默认 dry-run)
```

衔接原则:每阶段读上一阶段产物文件、写自己的产物文件,SQLite 记录进度;任何一步失败重跑不丢进度。
降级策略(借鉴 nonomil):核心抓取失败 **fail loud**;enrich(OCR/转写/AI)失败 **fail soft** 降级标记,不阻塞整体。

## 5. 目录结构

```
get-to-know-yourself/
├── config.yaml              # 限速、时间窗、模型、路径
├── .secrets/                # cli cookie 备份等 (gitignore)
├── data/
│   ├── state.sqlite         # 已处理/已分类进度(增量、续传)
│   ├── raw_notes.json       # 阶段1产物(单一事实源)
│   ├── transcripts/         # 阶段2产物
│   ├── classified.json      # 阶段4产物
│   └── errors.log
├── vault/                   # Obsidian 库根目录
│   ├── notes/
│   │   ├── <分类>/          # 按分类的文件夹层级 (bnchiang96 约定)
│   │   └── _分类/           # 每个分类一个 MOC 索引笔记(供 Graph View)
│   ├── media/               # 封面/图片本地副本(下载/外链可切换)
│   └── analysis/            # 报告.md + 趋势图表 png/html
├── src/
│   ├── fetch.py             # 封装 xhs-cli favorites/read/comments + hc-tec boards
│   ├── transcribe.py        # 复用 hc-tec faster-whisper
│   ├── to_obsidian.py
│   ├── classify.py          # BGE-small-zh + KMeans++ + Opus 簇命名
│   ├── analyze.py
│   ├── writeback.py
│   └── lib/                 # xhs_client(cli 封装), boards, ratelimit, schema, embedding, store(SQLite)
├── notebooks/analysis.ipynb # 探索 + 出图
└── tests/
```

## 6. 数据 Schema

`data/raw_notes.json` 每条笔记:

```
id            笔记唯一 id
type          "图文" | "视频"
title         标题
author        作者
url           笔记链接
collected_at  收藏时间 (用于近2年过滤与趋势)
folder        小红书原收藏夹名
body_text     正文
image_urls[]  图片 URL 列表
video_url     视频地址 (视频笔记)
top_comments[] 精选评论
fetched_at    抓取时间
```

阶段4 分类后追加: `categories[]`, `tags[]`, `cluster_id`。

日期格式: `YYYY-MM-DD`(示例 `2025-08-12`),均为合成示例值。

## 7. 各阶段细节

### 阶段0 auth
- 用 `xhs login`(浏览器 cookie 抽取或 `--qrcode` 扫码)建立登录态,由 xiaohongshu-cli 自管。
- 用 `xhs status` 校验;`error.code == not_authenticated/verification_required` 时**明确报错**提示重登,不静默失败。

### 阶段1 fetch
- 主路径: `xhs favorites --json` 拉当前用户收藏平铺列表 → 对每条 `xhs read <id> --json` 取详情、`xhs comments <url> --all --json` 取精选评论。
- 补充: 用 hc-tec 的 Boards 方式枚举收藏专辑,回填每条的 `folder` 分组(CLI 平铺列表不含分组时)。
- 近 2 年过滤: `collected_at >= today - 2y`。
- **限速(降封号核心)**: 依赖 cli 自带反检测(高斯抖动/退避/验证码冷却),并在封装层再加请求间随机间隔与并发=1,参数在 config.yaml。
- 增量/续传: SQLite 记录已抓 id,二次运行只补新增(借鉴 zhulin025 的范围分批 + 缓存去重)。

### 阶段2 transcribe
- 仅 `type==视频`。复用 hc-tec `media-audio-download` + `whisper-transcribe-docker`(faster-whisper,默认模型 `small`,中文)→ txt。
- fail soft: 单条失败标记并记录,不阻塞整体。

### 阶段3 to_obsidian
- 渲染 .md(见第 8 节),按分类建文件夹 `vault/notes/<分类>/<标题>.md`(bnchiang96 约定)。
- explore↔item URL 归一化;媒体"本地下载 vs 外链"可在 config.yaml 切换。
- 幂等:重跑覆盖生成,不重复追加。

### 阶段4 classify
- 嵌入: 本地 BGE-small-zh 把每条笔记(标题+正文+逐字稿摘要)向量化。
- 聚类: K-Means++ 自动发现簇(借鉴 RedNote_AI);簇数可启发式/手动。
- Opus 辅助(**按簇批处理,非按条**): 给每簇代表样本 → 簇命名、边界样本归类、低置信样本复核。
- LLM 调用 ≤50 条/批(LclRobin)。结果写回各 .md 的 `categories`/`tags`/`cluster_id`,并落 `data/classified.json` + SQLite。

### 阶段5 analyze
- 近 2 年整体 Top 方向 + 占比。
- 趋势: 按月/季统计各方向数量曲线,识别"上升中/新出现"的方向。
- Haiku 生成文字解读;matplotlib/plotly 出静态图。
- 产出 `vault/analysis/方向分析报告.md` + 图表。
- **知识图谱(Obsidian 原生)**: 为每个分类生成 MOC 索引笔记(`vault/notes/_分类/<分类>.md`,链接该簇全部成员);笔记正文带 `[[_分类/<分类>]]` wikilink + tags。打开 Obsidian Graph View 即得可拖拽/缩放/按 tag 上色的力导向知识图谱,无需 D3。

### 阶段6 writeback(可选,手动触发)
- 机制(移植 LclRobin): 取消收藏 → 重新收藏 → 选择对应专辑(XHS 无直接"移动"API)。
- 约束: 专辑名必须与小红书已有专辑完全一致;首次须 `headless:false`;弹窗 DOM 易变,需保留诊断工具。
- 默认 **dry-run**: 仅打印"会把哪些笔记归入哪个专辑",不执行。
- `--apply` 才真正写;强限速;SQLite 记录便于回滚。
- 风险最高,完全独立,需显式调用。

## 8. Obsidian 笔记格式

```markdown
---
title: "露营装备清单"
author: "xxx"
xhs_url: https://...
type: 视频
collected_at: 2025-08-12
folder: "户外"
categories: [户外露营]
tags: [装备, 清单, 新手]
cluster_id: 7
---

# 露营装备清单

分类: [[_分类/户外露营]]   # wikilink → 供 Obsidian Graph View 聚类

{正文}

## 图片
![](media/xxx.jpg)   # 或外链

## 逐字稿            # 仅视频
{whisper 转写文本}

## 精选评论
- ...
```

## 9. 错误处理与风控

- **限速优先**: 串行 + 随机间隔,宁慢不封;参数全在 config.yaml。
- **fail loud**: cookie 失效、抓取被拦、转写失败均明确报错并写 `data/errors.log`,绝不静默跳过后谎报成功。
- **断点续传**: 每阶段记录已处理 id。
- **writeback 默认 dry-run**,`--apply` 才动账号。
- **隐私**: cookie 进 `.secrets/` 并 gitignore;不提交任何含登录态/个人数据的文件。

## 10. 测试策略

- 单元: schema 校验、近2年过滤、.md 渲染、趋势统计、限速器 —— fixture 假数据,不碰真网络。
- 集成: 用 1–2 条样例笔记 JSON 跑通 fetch→obsidian→classify→analyze。
- 真实抓取不进自动化测试(依赖账号);提供"小批量 5 条"手动 smoke 脚本。
- 覆盖率目标 80%(纯逻辑部分)。

## 11. 技术栈

Python 3.11 / **xiaohongshu-cli**(pip,作抓取引擎)/ Playwright(仅 hc-tec Boards 补抓 + 阶段6 回写)/
faster-whisper(复用 hc-tec skill)/ sentence-transformers + **BGE-small-zh** / scikit-learn(K-Means++)/
SQLite(增量状态)/ matplotlib + plotly / Anthropic SDK(Opus 簇命名 + Haiku 报告)/ PyYAML。
Obsidian Graph View 作知识图谱(无需额外依赖)。

## 12. 合规与风险提示

此类抓取依赖逆向接口/模拟登录,属灰色地带,可能违反小红书用户协议并有账号风控/封号风险。
仅用于个人收藏的备份与整理,使用强限速、默认 dry-run 回写,不分发数据。
