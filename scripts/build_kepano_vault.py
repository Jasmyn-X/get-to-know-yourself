# scripts/build_kepano_vault.py
"""把收藏库重建为 kepano 风格 Obsidian 知识库(0 token,纯本地)。

布局(kepano taxonomy):
  Clippings/<方向>/   1160 条收藏(kepano frontmatter: source/author/category链接/published)
  Categories/         18 个方向 MOC(含 Dataview 块 + 静态列表)
  References/         从高频标签自动生成的概念页(知识图谱的 hub 节点)
  Templates/          剪藏/笔记/日记模板(仅在缺失时创建)
  Notes/ Daily/       你自己写东西的空间(仅在缺失时创建,不覆盖)
  Home.md             主页仪表盘
  analysis/           方向分析报告 + 分布图(重生成)

读取 data/raw_collect.json + clusters.json + details/ + transcripts/。
可重复运行:转写完成、重跑聚类(刷新 clusters.json)后再次运行即用增强内容刷新整库。
运行: PYTHONPATH=. python scripts/build_kepano_vault.py
"""
import datetime as dt
import json
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.lib.taxonomy import CLUSTER_NAMES, GROUPS

DATA = Path("data")
VAULT = Path("vault")
CLIPPINGS = VAULT / "Clippings"
CATEGORIES = VAULT / "Categories"
REFERENCES = VAULT / "References"
TEMPLATES = VAULT / "Templates"
NOTES = VAULT / "Notes"
DAILY = VAULT / "Daily"
ANALYSIS = VAULT / "analysis"

CONCEPT_MIN = 4      # 标签出现 >=4 次才建概念页(过滤一次性长尾)
CONCEPT_CAP = 250    # 概念页数量上限
TODAY = dt.date.today().isoformat()
_ILLEGAL = re.compile(r'[\\/:*?"<>|\n\r\t#\^\[\]]+')


# ---------- 小工具 ----------
def safe_name(text: str, maxlen: int = 60) -> str:
    base = _ILLEGAL.sub("_", (text or "").strip()).strip("_") or "untitled"
    return base[:maxlen].rstrip() or "untitled"


def epoch_ms_to_date(ms):
    try:
        return dt.date.fromtimestamp(int(ms) / 1000).isoformat()
    except (TypeError, ValueError, OSError, OverflowError):
        return None


def yq(s: str) -> str:
    return '"' + str(s).replace('"', "'") + '"'


def liked_of(item: dict, detail: dict | None):
    if detail and detail.get("liked_count") is not None:
        try:
            return int(detail["liked_count"])
        except (TypeError, ValueError):
            pass
    raw = (item.get("interact_info") or {}).get("liked_count")
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def cover_of(item: dict):
    c = item.get("cover") or {}
    return c.get("url_default") or c.get("url_pre")


def url_of(item: dict) -> str:
    nid = item["note_id"]
    tok = item.get("xsec_token", "")
    return (f"https://www.xiaohongshu.com/explore/{nid}"
            f"?xsec_token={tok}&xsec_source=pc_user")


def load_details() -> dict:
    out = {}
    d = DATA / "details"
    if not d.exists():
        return out
    for f in d.glob("*.json"):
        try:
            out[f.stem] = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            pass
    return out


def load_transcript(note_id: str):
    f = DATA / "transcripts" / f"{note_id}.txt"
    if f.exists():
        t = f.read_text(encoding="utf-8").strip()
        return t or None
    return None


# ---------- 渲染 ----------
def render_clipping(title, url, item, cat, typ, liked, published, tags,
                    cover, desc, transcript, note_concepts, concept_stem) -> str:
    fm = ["---", f"title: {yq(title)}", f"source: {url}",
          f"author: {yq((item.get('user') or {}).get('nickname', ''))}",
          f'category: "[[{cat}]]"', f"type: {typ}"]
    if liked is not None:
        fm.append(f"liked_count: {liked}")
    if published:
        fm.append(f"published: {published}")
    fm.append(f"clipped: {TODAY}")
    if tags:
        fm.append("xhs_tags:")
        for t in tags[:30]:
            fm.append(f"  - {yq(t)}")
    fm.append("---")

    b = [f"# {title}", ""]
    meta = f"> [!info] 小红书剪藏 · [[{cat}]]"
    if liked is not None:
        meta += f" · ❤️{liked}"
    meta += f" · {typ}"
    b += [meta, ""]
    if cover:
        b += [f"![]({cover})", ""]
    if desc.strip():
        b += [desc.strip(), ""]
    if transcript:
        b += ["> [!quote]- 视频逐字稿"]
        b += ["> " + ln for ln in transcript.splitlines() if ln.strip()]
        b += [""]
    if note_concepts:
        links = " ".join(f"[[{concept_stem[t]}|{t}]]" for t in note_concepts)
        b += [f"**相关概念:** {links}", ""]
    b.append(f"[在小红书打开]({url})")
    return "\n".join(fm) + "\n\n" + "\n".join(b) + "\n"


def render_concept(tag, members) -> str:
    cats = sorted({m[3] for m in members})
    fm = ["---", "type: concept", f"clipping_count: {len(members)}", "categories:"]
    fm += [f'  - "[[{c}]]"' for c in cats]
    fm.append("---")
    head = "出现于 **%d** 条收藏,横跨方向: " % len(members) + " ".join(f"[[{c}]]" for c in cats)
    b = [f"# {tag}", "", head, "", "## 相关收藏"]
    for cstem, title, liked, c in sorted(members, key=lambda m: m[2], reverse=True):
        b.append(f"- [[{cstem}|{title}]]  ❤️{liked}  · [[{c}]]")
    return "\n".join(fm) + "\n\n" + "\n".join(b) + "\n"


def render_category(cat, members) -> str:
    members = sorted(members, key=lambda m: m[2], reverse=True)
    fm = ["---", "type: category", f"clipping_count: {len(members)}", "---"]
    b = [f"# {cat}", "", f"共 **{len(members)}** 条收藏。", "",
         "```dataview", 'TABLE liked_count AS "❤️", type AS "类型", published AS "发布"',
         f'FROM "Clippings/{cat}"', "SORT liked_count DESC", "```", "",
         "## 收藏列表(按赞排序)", ""]
    for cstem, title, liked, typ, _rank in members:
        b.append(f"- [[{cstem}|{title}]]  ❤️{liked}  · {typ}")
    return "\n".join(fm) + "\n\n" + "\n".join(b) + "\n"


# ---------- 脚手架(仅在缺失时写,不覆盖用户内容) ----------
def scaffold_if_absent():
    TEMPLATES.mkdir(parents=True, exist_ok=True)
    NOTES.mkdir(parents=True, exist_ok=True)
    DAILY.mkdir(parents=True, exist_ok=True)
    files = {
        TEMPLATES / "剪藏.md":
            "---\ntitle: \"{{title}}\"\nsource: \nauthor: \ncategory: \ntype: \n"
            "clipped: {{date}}\nxhs_tags:\n---\n\n# {{title}}\n\n",
        TEMPLATES / "笔记.md":
            "---\ntype: note\ncreated: {{date}}\ntags:\n---\n\n# {{title}}\n\n"
            "## 想法\n\n## 关联\n\n",
        TEMPLATES / "日记.md":
            "---\ntype: daily\ncreated: {{date}}\n---\n\n# {{date}}\n\n"
            "## 今天想做 / 学到\n\n## 关联收藏\n\n",
        NOTES / "_README.md":
            "# Notes(你自己的原子笔记)\n\n这里放**你自己的想法、复盘、计划**——"
            "区别于 Clippings(外部收藏)。\n用 `[[双链]]` 把笔记连到收藏或概念页上,"
            "图谱才会真正长出来。\n",
        DAILY / "_README.md":
            "# Daily(日记)\n\n每天一条,记录「今天想做什么 / 学到什么」,"
            "并用 `[[双链]]` 连到相关收藏。\n坚持几周后,Graph View 会显示你真实的关注轨迹。\n",
    }
    for path, content in files.items():
        if not path.exists():
            path.write_text(content, encoding="utf-8")


def write_readme():
    txt = """# 📕 我的小红书收藏知识库 — 使用说明

本库由 `scripts/build_kepano_vault.py` 自动生成,采用 **kepano(Obsidian CEO)风格**结构。

## 文件夹
- **Clippings/** — 1160 条小红书收藏,按方向分子文件夹。每条带 kepano frontmatter
  (`source/author/category/published/liked_count/xhs_tags`)。
- **Categories/** — 18 个方向的 MOC(目录页),含 Dataview 表格 + 静态列表。
- **References/** — 从高频标签自动生成的**概念页**,是知识图谱的 hub:同一个概念把
  跨方向的收藏串起来。点开任意概念能看到它出现在哪些收藏/方向。
- **Notes/ Daily/** — 留给你自己写想法和日记的空间(脚本不会覆盖)。
- **Templates/** — 新建剪藏/笔记/日记的模板。
- **Home.md** — 主页仪表盘,从这里进入。
- **analysis/** — 方向分析报告 + 分布图。

## 建议启用的插件(在 Obsidian 里点 3 下)
1. **Dataview**:设置 → 第三方插件 → 关闭安全模式 → 浏览 → 搜 `Dataview` → 安装 → 启用。
   启用后 Categories/Home 里的 ```dataview``` 块会变成动态表格。
2. **Smart Connections**:同上搜 `Smart Connections` → 安装 → 启用。首次会下载一个
   **本地嵌入模型**(零 API key、纯本地),之后每条笔记右侧自动显示「语义相关笔记」,
   还能对整库提问。它会挖出跨方向的隐藏关联,自动给图谱织网。
3. (可选)**Templater**:配合 Templates/ 让新笔记自动套结构。

## 看图谱
左侧 → Graph View。Categories 和 References 会成为中心节点,
收藏围绕它们聚成簇——这就是你的「关注网络」。

## 刷新
重新抓取/重跑聚类后,运行 `PYTHONPATH=. python scripts/build_kepano_vault.py`
即可用最新内容刷新整库(Notes/Daily 不受影响)。
"""
    (VAULT / "README-知识库使用说明.md").write_text(txt, encoding="utf-8")


# ---------- 报告 + 图表 ----------
def build_report_and_chart(n, cat_members, labels):
    counts = Counter({cat: len(ms) for cat, ms in cat_members.items()})
    avg_liked = {cat: int(sum(m[2] for m in ms) / len(ms)) for cat, ms in cat_members.items()}
    vid_share = {cat: sum(1 for m in ms if m[3] == "视频") / len(ms) for cat, ms in cat_members.items()}

    half = n // 2
    recent, older = Counter(), Counter()
    for cat, ms in cat_members.items():
        for m in ms:
            (recent if m[4] < half else older)[cat] += 1

    def share(counter):
        tot = sum(counter.values()) or 1
        return {k: v / tot for k, v in counter.items()}

    rs, os_ = share(recent), share(older)
    trend = {cat: rs.get(cat, 0) - os_.get(cat, 0) for cat in counts}

    # 柱状图
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
    plt.rcParams["axes.unicode_minus"] = False
    ordered = counts.most_common()
    cats = [c for c, _ in ordered][::-1]
    vals = [v for _, v in ordered][::-1]
    plt.figure(figsize=(10, 8))
    plt.barh(cats, vals, color="#d81e5b")
    for i, v in enumerate(vals):
        plt.text(v + 2, i, str(v), va="center", fontsize=9)
    plt.title("小红书收藏方向分布(共 %d 条)" % n)
    plt.xlabel("收藏数")
    plt.tight_layout()
    plt.savefig(ANALYSIS / "方向分布.png", dpi=130)
    plt.close()

    # 报告
    L = ["# 小红书收藏方向分析报告", "",
         f"> 数据: **{n} 条**收藏(标题+正文+标签语义聚类,BGE-small-zh + KMeans18)。生成于 {TODAY}。", "",
         "![[方向分布.png]]", "",
         "## 一、总体方向排行", "",
         "| 方向 | 收藏数 | 占比 | 视频占比 | 平均赞 |", "|---|---:|---:|---:|---:|"]
    for cat, c in counts.most_common():
        L.append(f"| [[{cat}]] | {c} | {c/n*100:.1f}% | {vid_share[cat]*100:.0f}% | {avg_liked[cat]} |")
    L += ["", "## 二、按大方向归组", ""]
    for g, cats_in in GROUPS.items():
        tot = sum(counts.get(c, 0) for c in cats_in)
        L.append(f"### {g} — 合计 {tot} 条 ({tot/n*100:.0f}%)")
        for c in sorted(cats_in, key=lambda x: counts.get(x, 0), reverse=True):
            L.append(f"- **[[{c}]]**: {counts.get(c,0)} 条(均赞 {avg_liked.get(c,0)})")
        L.append("")
    L += ["## 三、近期 vs 早先(用收藏先后近似时间)", "",
          "> 收藏列表越靠前=越近收藏。按列表前半/后半对比各方向占比变化。", ""]
    rising = sorted(trend.items(), key=lambda x: x[1], reverse=True)[:5]
    cooling = sorted(trend.items(), key=lambda x: x[1])[:5]
    L.append("**📈 近期上升中(更常收藏):**")
    L += [f"- {cat}  (+{d*100:.1f} 个百分点)" for cat, d in rising]
    L.append("")
    L.append("**📉 早先更多(近期降温):**")
    L += [f"- {cat}  ({d*100:.1f} 个百分点)" for cat, d in cooling]
    L += ["", "## 四、说明与局限", "",
          "- 分类名为人工命名;每条可在 `Clippings/<方向>/` 找到,Graph View 可看聚类。",
          "- 「时间趋势」用**收藏先后顺序**近似(收藏列表无精确时间字段)。"]
    (ANALYSIS / "方向分析报告.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    return counts


def build_home(n, counts, concept_members, concept_stem):
    top_concepts = sorted(concept_members.items(), key=lambda kv: len(kv[1]), reverse=True)[:20]
    L = ["# 🏠 知识库主页", "",
         f"我的小红书收藏知识库 · **{n} 条** · **{len(counts)} 个方向** · 生成于 {TODAY}", "",
         "> 建议先读 [[README-知识库使用说明]],并启用 Dataview / Smart Connections 两个插件。", "",
         "## 📊 方向总览", "", "![[方向分布.png]]", "",
         "完整分析见 [[方向分析报告]]。", "", "## 📂 各方向(按收藏数)", ""]
    for cat, c in counts.most_common():
        L.append(f"- [[{cat}]] — {c} 条")
    L += ["", "## 🔗 高频概念(知识图谱 hub)", ""]
    for tag, members in top_concepts:
        L.append(f"- [[{concept_stem[tag]}|{tag}]] — {len(members)} 条")
    L += ["", "## 🧭 动态视图(需 Dataview)", "",
          "**最近收藏(收藏列表靠前):**", "```dataview",
          'TABLE category, liked_count AS "❤️"', 'FROM "Clippings"',
          "SORT collect_rank ASC", "LIMIT 20", "```", "",
          "**最高赞收藏:**", "```dataview",
          'TABLE category, liked_count AS "❤️"', 'FROM "Clippings"',
          "SORT liked_count DESC", "LIMIT 20", "```", ""]
    (VAULT / "Home.md").write_text("\n".join(L) + "\n", encoding="utf-8")


# ---------- 主流程 ----------
def main():
    raw = json.loads((DATA / "raw_collect.json").read_text(encoding="utf-8"))
    labels = json.loads((DATA / "clusters.json").read_text(encoding="utf-8"))["labels"]
    details = load_details()
    n = len(raw)
    assert len(labels) == n, f"labels({len(labels)}) != raw({n})"

    # Pass 1: 标签频次 -> 决定概念集
    tag_count = Counter()
    for item in raw:
        det = details.get(item["note_id"])
        if not det:
            continue
        for tg in det.get("tags") or []:
            t = tg.strip()
            if t:
                tag_count[t] += 1
    concepts = [t for t, c in tag_count.most_common() if c >= CONCEPT_MIN][:CONCEPT_CAP]
    concept_set = set(concepts)
    concept_stem, seen = {}, set()   # seen 用小写比对,避开 Windows 大小写不敏感的文件名碰撞
    for t in concepts:
        s = orig = safe_name(t, 40)
        k = 1
        while s.lower() in seen:
            k += 1
            s = f"{orig}_{k}"
        concept_stem[t] = s
        seen.add(s.lower())

    # 重置生成目录(保留 Notes/Daily/Templates 用户内容)
    if (VAULT / "notes").exists():       # 清理旧版小写布局
        shutil.rmtree(VAULT / "notes")
    for d in (CLIPPINGS, CATEGORIES, REFERENCES, ANALYSIS):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)

    # Pass 2: 渲染 clippings,收集 MOC / 概念成员
    cat_members = defaultdict(list)        # cat -> [(stem,title,liked,typ,rank)]
    concept_members = defaultdict(list)    # tag -> [(stem,title,liked,cat)]
    for i, item in enumerate(raw):
        cat = CLUSTER_NAMES[labels[i]]
        note_id = item["note_id"]
        det = details.get(note_id)
        title = ((det.get("title") if det else None) or item.get("display_title") or "无标题").strip() or "无标题"
        liked = liked_of(item, det)
        typ = "视频" if item.get("type") == "video" else "图文"
        tags = [t.strip() for t in ((det.get("tags") if det else None) or []) if t.strip()]
        published = epoch_ms_to_date(det.get("time")) if det else None
        cover = cover_of(item)
        desc = (det.get("desc") if det else "") or ""
        transcript = load_transcript(note_id)
        note_concepts = [t for t in tags if t in concept_set]

        clip_stem = f"{safe_name(title)}__{note_id}"
        md = render_clipping(title, url_of(item), item, cat, typ, liked, published,
                             tags, cover, desc, transcript, note_concepts, concept_stem)
        folder = CLIPPINGS / cat
        folder.mkdir(exist_ok=True)
        (folder / f"{clip_stem}.md").write_text(md, encoding="utf-8")

        cat_members[cat].append((clip_stem, title, liked or 0, typ, i))
        for t in note_concepts:
            concept_members[t].append((clip_stem, title, liked or 0, cat))

    # 概念页
    for tag, members in concept_members.items():
        (REFERENCES / f"{concept_stem[tag]}.md").write_text(
            render_concept(tag, members), encoding="utf-8")

    # 方向 MOC
    for cat, members in cat_members.items():
        (CATEGORIES / f"{cat}.md").write_text(render_category(cat, members), encoding="utf-8")

    # 报告 + 图表 + 主页 + 脚手架 + README
    counts = build_report_and_chart(n, cat_members, labels)
    build_home(n, counts, concept_members, concept_stem)
    scaffold_if_absent()
    write_readme()

    tx = sum(1 for _ in (DATA / "transcripts").glob("*.txt")) if (DATA / "transcripts").exists() else 0
    print(f"完成: {n} 条收藏 -> {len(counts)} 方向 MOC, {len(concept_members)} 概念页, 转写命中 {tx} 条")
    print("入口: vault/Home.md  ·  说明: vault/README-知识库使用说明.md")


if __name__ == "__main__":
    main()
