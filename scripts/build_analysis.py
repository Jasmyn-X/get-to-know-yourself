# scripts/build_analysis.py
"""把语义聚类结果落地:给 18 个簇命名 → 给 1160 条打分类 → 重建 Obsidian 库
(按分类分文件夹 + 每分类 MOC 笔记)→ 生成方向分析报告 + 分布柱状图。
纯本地、0 token。运行: python scripts/build_analysis.py
"""
import datetime as dt
import json
import shutil
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.lib.collect_adapter import collect_item_to_note
from src.to_obsidian import render, safe_filename

# 簇 -> 分类名(人工命名,基于语义聚类的代表标题/高频词)
CLUSTER_NAMES = {
    0: "家装装修", 1: "平价好物", 2: "家常菜", 3: "减脂餐",
    4: "AI产品与独立开发", 5: "求职面试", 6: "旅行攻略", 7: "美妆化妆",
    8: "学习方法与效率工具", 9: "烘焙甜品", 10: "健身塑形", 11: "雅思英语",
    12: "情感与自我成长", 13: "AI编程ClaudeCode", 14: "自媒体副业",
    15: "编织手作", 16: "iPad数字笔记", 17: "AI视频漫剧",
}
# 高层方向归组(用于报告叙事)
GROUPS = {
    "AI / 技术折腾": ["AI编程ClaudeCode", "AI产品与独立开发", "AI视频漫剧",
                   "学习方法与效率工具", "iPad数字笔记"],
    "美食 / 吃": ["家常菜", "烘焙甜品", "减脂餐"],
    "求职 / 搞钱": ["求职面试", "自媒体副业"],
    "自我提升": ["情感与自我成长", "雅思英语"],
    "生活方式": ["健身塑形", "美妆化妆", "家装装修", "平价好物", "旅行攻略", "编织手作"],
}

DATA = Path("data")
VAULT = Path("vault")
NOTES_DIR = VAULT / "notes"
MOC_DIR = NOTES_DIR / "_分类"
ANALYSIS = VAULT / "analysis"


def _liked(r):
    try:
        return int(r.get("interact_info", {}).get("liked_count", "0"))
    except (TypeError, ValueError):
        return 0


def main():
    raw = json.loads((DATA / "raw_collect.json").read_text(encoding="utf-8"))
    clusters = json.loads((DATA / "clusters.json").read_text(encoding="utf-8"))
    labels = clusters["labels"]
    n = len(raw)
    now = dt.datetime.now()

    # 重建 notes 目录(按分类分文件夹)
    if NOTES_DIR.exists():
        shutil.rmtree(NOTES_DIR)
    NOTES_DIR.mkdir(parents=True)
    MOC_DIR.mkdir(parents=True)

    cat_members = defaultdict(list)  # cat -> [(title, stem, liked, rank, type)]
    for i, item in enumerate(raw):
        cat = CLUSTER_NAMES[labels[i]]
        note = collect_item_to_note(item, rank=i, fetched_at=now)
        note.categories = [cat]
        folder = NOTES_DIR / cat
        folder.mkdir(exist_ok=True)
        fn = safe_filename(note.title, note.id)
        (folder / fn).write_text(render(note), encoding="utf-8")
        cat_members[cat].append((note.title, fn[:-3], _liked(item), i, item.get("type")))

    # 每个分类的 MOC 索引笔记(供 Obsidian Graph View)
    for cat, members in cat_members.items():
        lines = [f"# {cat}", "", f"共 {len(members)} 条收藏。", ""]
        for title, stem, liked, _, _ in sorted(members, key=lambda m: m[2], reverse=True):
            lines.append(f"- [[{stem}|{title}]]  ❤️{liked}")
        (MOC_DIR / f"{cat}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # 统计
    counts = Counter(CLUSTER_NAMES[l] for l in labels)
    half = n // 2  # rank < half 视为“近期”(收藏列表越靠前=越新)
    recent_cat = Counter(CLUSTER_NAMES[labels[i]] for i in range(n) if i < half)
    older_cat = Counter(CLUSTER_NAMES[labels[i]] for i in range(n) if i >= half)

    def share(counter):
        tot = sum(counter.values()) or 1
        return {k: v / tot for k, v in counter.items()}

    rs, os_ = share(recent_cat), share(older_cat)
    trend = {cat: (rs.get(cat, 0) - os_.get(cat, 0)) for cat in counts}

    # 柱状图
    ANALYSIS.mkdir(parents=True, exist_ok=True)
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
    avg_liked = {cat: int(sum(m[2] for m in ms) / len(ms)) for cat, ms in cat_members.items()}
    vid_share = {cat: sum(1 for m in ms if m[4] == "video") / len(ms) for cat, ms in cat_members.items()}

    L = []
    L.append("# 小红书收藏方向分析报告")
    L.append("")
    L.append(f"> 数据: 近期抓取的 **{n} 条**收藏(标题级语义聚类,BGE-small-zh + KMeans18)。"
             f"生成于 {now:%Y-%m-%d}。")
    L.append("")
    L.append("![方向分布](方向分布.png)")
    L.append("")
    L.append("## 一、总体方向排行")
    L.append("")
    L.append("| 方向 | 收藏数 | 占比 | 视频占比 | 平均赞 |")
    L.append("|---|---:|---:|---:|---:|")
    for cat, c in counts.most_common():
        L.append(f"| [[_分类/{cat}\\|{cat}]] | {c} | {c/n*100:.1f}% | "
                 f"{vid_share[cat]*100:.0f}% | {avg_liked[cat]} |")
    L.append("")
    L.append("## 二、按大方向归组")
    L.append("")
    for g, cats_in in GROUPS.items():
        tot = sum(counts.get(c, 0) for c in cats_in)
        L.append(f"### {g} — 合计 {tot} 条 ({tot/n*100:.0f}%)")
        for c in sorted(cats_in, key=lambda x: counts.get(x, 0), reverse=True):
            L.append(f"- **{c}**: {counts.get(c,0)} 条(均赞 {avg_liked.get(c,0)})")
        L.append("")
    L.append("## 三、近期 vs 早先(用收藏先后近似时间)")
    L.append("")
    L.append("> 收藏列表越靠前=越近收藏。下面按列表前半/后半对比各方向占比变化。")
    L.append("")
    rising = sorted(trend.items(), key=lambda x: x[1], reverse=True)[:5]
    cooling = sorted(trend.items(), key=lambda x: x[1])[:5]
    L.append("**📈 近期上升中(更常收藏):**")
    for cat, d in rising:
        L.append(f"- {cat}  (+{d*100:.1f} 个百分点)")
    L.append("")
    L.append("**📉 早先更多(近期降温):**")
    for cat, d in cooling:
        L.append(f"- {cat}  ({d*100:.1f} 个百分点)")
    L.append("")
    L.append("## 四、说明与局限")
    L.append("")
    L.append("- 仅基于**标题**语义聚类;正文/视频逐字稿尚未纳入(后段增强会更准)。")
    L.append("- “时间趋势”用**收藏先后顺序**近似(收藏列表无精确时间字段)。")
    L.append("- 分类名为人工命名;每条可在 `vault/notes/<分类>/` 找到,Graph View 可看聚类。")
    (ANALYSIS / "方向分析报告.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    print(f"完成: {n} 条 -> {len(counts)} 个方向")
    print("报告: vault/analysis/方向分析报告.md")
    print("图表: vault/analysis/方向分布.png")
    print("Top 方向:", counts.most_common(6))


if __name__ == "__main__":
    main()
