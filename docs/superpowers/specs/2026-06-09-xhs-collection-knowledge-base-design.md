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
| 数据获取 | Cookie + Playwright 自动化抓取 | 复用 CookieCloud/Playwright 思路,可全自动、字段全 |
| 分类范围 | 本地 AI 自动发现分类 + 可选回写小红书专辑 | 主流程安全;回写隔离为独立高风险阶段 |
| 内容深度 | 标准版:元数据 + 正文 + 图片链接 + 精选评论 | 分析够准,抓取风险可控 |
| 视频逐字稿 | 下载音频轨 → 本地 faster-whisper | 零 token、零账号互动风险 |
| 分析产出 | .md 报告 + 可视化图表 | 直观,与知识库同体系 |
| 分析范围 | 近 2 年全量 + 按月/季趋势 | 既看整体方向,也看兴趣迁移 |
| 分类模型 | 本地嵌入聚类发现 + **Opus** 辅助(按簇批处理) | 质量优先;按簇调用控制 token |
| 分析模型 | **Haiku** 生成报告解读 | 总结性文字,够用且省 |
| 架构 | 方案 A:分阶段 Python 脚本 + 分析 Notebook | 每步可独立重跑、断点续传;回写天然隔离 |

## 3. 不做(YAGNI / 范围外)

- 不做一体化 CLI / yaml 全自动编排(方案 B)。
- 不做 Claude Code skill 驱动抓取(方案 C)。
- 不做交互式网页 dashboard(分析用静态报告 + 图表)。
- 不通过小红书 @问一问 生成逐字稿(账号互动风险高、不可控)。
- 不抓取超过 2 年的历史收藏(除趋势对比所需的时间统计)。

## 4. 管线总览与数据流

六个独立阶段,中间用 JSON 衔接,每步可单独重跑(`--resume`):

```
[0 auth]       建立登录态 (CookieCloud / 手动登录存 cookie)  → .secrets/cookies.json
[1 fetch]      遍历收藏夹 → 每条笔记元数据+正文(近2年/限速/续传) → data/raw_notes.json
[2 transcribe] 视频笔记: 下音频轨 → faster-whisper            → data/transcripts/{id}.txt
[3 to_obsidian] 合并渲染 .md (YAML frontmatter)               → vault/notes/*.md
[4 classify]   嵌入聚类自动发现分类 (+ Opus 按簇辅助)          → data/classified.json + 回写 .md tags
[5 analyze]    近2年方向 + 趋势 → 报告 + 图表 (Haiku 解读)     → vault/analysis/*
[6 writeback]  ★可选/手动: 分类回写小红书专辑 (默认 dry-run)
```

衔接原则:每阶段读上一阶段产物文件、写自己的产物文件,带断点续传;任何一步失败重跑不丢进度。

## 5. 目录结构

```
get-to-know-yourself/
├── config.yaml              # 限速、时间窗、模型、路径
├── .secrets/                # cookies.json (gitignore)
├── data/
│   ├── raw_notes.json       # 阶段1产物(单一事实源)
│   ├── transcripts/         # 阶段2产物
│   ├── classified.json      # 阶段4产物
│   └── errors.log
├── vault/                   # Obsidian 库根目录
│   ├── notes/               # 每条笔记一个 .md
│   ├── media/               # 封面/图片本地副本(可选)
│   └── analysis/            # 报告.md + 图表 png/html
├── src/
│   ├── fetch.py
│   ├── transcribe.py
│   ├── to_obsidian.py
│   ├── classify.py
│   ├── analyze.py
│   ├── writeback.py
│   └── lib/                 # cookie, ratelimit, schema, xhs_client, embedding
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
- 优先 CookieCloud 同步;否则手动浏览器登录一次并持久化 cookie 到 `.secrets/`。
- cookie 失效时**明确报错**提示重登,不静默失败。

### 阶段1 fetch
- Playwright 驱动登录态,遍历全部收藏夹 → 每条笔记。
- 近 2 年过滤: `collected_at >= today - 2y`。
- **限速(降封号核心)**: 请求间随机间隔(默认 3–8s),并发=1,参数在 config.yaml。
- 断点续传: 已抓 id 跳过。

### 阶段2 transcribe
- 仅 `type==视频`。取音频轨(yt-dlp/接口)→ faster-whisper(默认模型 `small`,中文)→ txt。
- 单条失败标记并记录,不阻塞整体。

### 阶段3 to_obsidian
- 渲染 .md(见第 8 节)。幂等:重跑覆盖生成,不重复追加。

### 阶段4 classify
- 默认: 中文 embedding 模型向量化 → 聚类(HDBSCAN/KMeans)自动发现簇。
- Opus 辅助(**按簇批处理,非按条**): 给每簇代表样本 → 簇命名、边界样本归类、低置信样本复核。
- 结果写回各 .md 的 `categories`/`tags`,并落 `data/classified.json`。

### 阶段5 analyze
- 近 2 年整体 Top 方向 + 占比。
- 趋势: 按月/季统计各方向数量曲线,识别"上升中/新出现"的方向。
- Haiku 生成文字解读;matplotlib/plotly 出图。
- 产出 `vault/analysis/方向分析报告.md` + 图表。

### 阶段6 writeback(可选,手动触发)
- 默认 **dry-run**: 仅打印"会把哪些笔记归入哪个专辑",不执行。
- `--apply` 才真正写;强限速;记录便于回滚。
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

Python 3.11 / Playwright / faster-whisper / sentence-transformers(中文嵌入)/
scikit-learn 或 hdbscan / matplotlib + plotly / Anthropic SDK(Opus + Haiku)/ PyYAML。

## 12. 合规与风险提示

此类抓取依赖逆向接口/模拟登录,属灰色地带,可能违反小红书用户协议并有账号风控/封号风险。
仅用于个人收藏的备份与整理,使用强限速、默认 dry-run 回写,不分发数据。
