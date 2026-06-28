# scripts/recluster.py
"""用「标题 + 正文 + 标签 + 逐字稿」做 BGE 语义聚类(0 token,纯本地)。

相比旧版只用标题,这里把详情正文/标签/视频逐字稿都并入,聚类更准。
KMeans 的簇号是随机的,会打乱原有 CLUSTER_NAMES 映射,所以本脚本:
  1. 重聚类 -> 写 data/clusters.json (labels + summaries)
  2. 按「新簇成员在旧分类里的多数票」自动给每个新簇一个 proposed_name
  3. 输出 data/cluster_worksheet.txt 供人(agent)核对后更新 src/lib/taxonomy.py

运行: PYTHONPATH=. python scripts/recluster.py
"""
import os
# 模型已在本地 HF 缓存,强制离线:避免联网检查 adapter_config 时因网络中断而崩溃
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import glob
import json
import re
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.cluster import KMeans

from src.classify import tokenize
from src.lib.taxonomy import CLUSTER_NAMES

DATA = Path("data")
RAW = DATA / "raw_collect.json"
DETAILS = DATA / "details"
TRANSCRIPTS = DATA / "transcripts"
CLUSTERS = DATA / "clusters.json"
WORKSHEET = DATA / "cluster_worksheet.txt"

K = 18
SEED = 42
MODEL = "BAAI/bge-small-zh-v1.5"
DESC_CAP = 1200      # 正文截断(字符)
TX_CAP = 1500        # 逐字稿截断(字符,取头部,避免超长稿主导)


def build_text(item: dict, det: dict | None, transcript: str | None) -> str:
    parts = [item.get("display_title", "")]
    if det:
        if det.get("title"):
            parts.append(det["title"])
        if det.get("desc"):
            parts.append(det["desc"][:DESC_CAP])
        tags = det.get("tags") or []
        if tags:
            parts.append(" ".join(tags))
    if transcript:
        parts.append(transcript[:TX_CAP])
    return " ".join(p for p in parts if p).strip()


def load_inputs():
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    texts, titles = [], []
    enriched = 0
    for item in raw:
        nid = item["note_id"]
        det = None
        df = DETAILS / f"{nid}.json"
        if df.exists():
            try:
                det = json.loads(df.read_text(encoding="utf-8"))
            except Exception:
                det = None
        tf = TRANSCRIPTS / f"{nid}.txt"
        tx = tf.read_text(encoding="utf-8").strip() if tf.exists() else None
        if det or tx:
            enriched += 1
        texts.append(build_text(item, det, tx))
        titles.append((det.get("title") if det and det.get("title")
                       else item.get("display_title")) or "无标题")
    return raw, texts, titles, enriched


def summarize(labels, X, titles, texts):
    summaries = []
    for c in range(K):
        idx = np.where(labels == c)[0]
        if len(idx) == 0:
            summaries.append({"cluster": c, "size": 0, "top_terms": [], "reps": []})
            continue
        centroid = X[idx].mean(axis=0)
        sims = X[idx] @ centroid
        order = np.argsort(sims)[::-1]
        reps = [titles[idx[i]] for i in order[:10]]
        tc = Counter()
        for i in idx:
            tc.update(tokenize(texts[i]))
        top_terms = [t for t, _ in tc.most_common(12)]
        summaries.append({"cluster": int(c), "size": int(len(idx)),
                          "top_terms": top_terms, "reps": reps})
    return summaries


def load_old_names_by_id() -> dict:
    """从 vault/Clippings frontmatter 读 note_id -> 上次分类名(category 链接)。
    按 id 对齐,避免 raw_collect 顺序/数量变化时位置错位。"""
    out = {}
    for p in glob.glob("vault/Clippings/**/*.md", recursive=True):
        m = re.search(r"__([0-9a-zA-Z]{12,})\.md$", Path(p).name)
        if not m:
            continue
        cm = re.search(r'category:\s*"?\[\[([^\]]+)\]\]',
                       Path(p).read_text(encoding="utf-8"))
        if cm:
            out[m.group(1)] = cm.group(1)
    return out


def propose_names(labels, ids, old_name_by_id):
    """每个新簇 -> 成员上次分类名的多数票(按 note_id 对齐)。"""
    out = {}
    for c in range(K):
        idx = np.where(labels == c)[0]
        votes = Counter(old_name_by_id[ids[i]] for i in idx
                        if ids[i] in old_name_by_id)
        if not votes:
            out[c] = ("(新方向?)", 0.0)
            continue
        name, cnt = votes.most_common(1)[0]
        out[c] = (name, cnt / len(idx))
    return out


def write_worksheet(summaries, proposed):
    used = Counter(n for n, _ in proposed.values())
    lines = ["# 重聚类命名工作表(BGE: 标题+正文+标签+逐字稿)", ""]
    for s in sorted(summaries, key=lambda x: x["size"], reverse=True):
        c = s["cluster"]
        name, purity = proposed[c]
        flag = "  ⚠️重名(需人工区分)" if used[name] > 1 else ""
        lines.append(f"## 新簇 {c}  | {s['size']} 条 | 建议名: {name} "
                     f"(纯度 {purity*100:.0f}%){flag}")
        lines.append("  高频词: " + " ".join(s["top_terms"]))
        lines.append("  代表标题:")
        for r in s["reps"][:6]:
            lines.append(f"    - {r}")
        lines.append("")
    miss = [v for v in CLUSTER_NAMES.values() if v not in used]
    if miss:
        lines.append("# 旧分类未被任何新簇认领(可能被合并/拆分): " + ", ".join(miss))
    WORKSHEET.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    from sentence_transformers import SentenceTransformer

    raw, texts, titles, enriched = load_inputs()
    n = len(raw)
    print(f"加载 {n} 条,其中 {enriched} 条含正文/逐字稿。开始嵌入({MODEL})...")

    ids = [item["note_id"] for item in raw]
    old_name_by_id = load_old_names_by_id()

    model = SentenceTransformer(MODEL)
    X = model.encode(texts, batch_size=64, normalize_embeddings=True,
                     show_progress_bar=True).astype(np.float32)

    km = KMeans(n_clusters=K, random_state=SEED, n_init=10)
    labels = km.fit_predict(X)

    summaries = summarize(labels, X, titles, texts)
    proposed = (propose_names(labels, ids, old_name_by_id) if old_name_by_id
                else {c: ("(无旧分类)", 0.0) for c in range(K)})

    CLUSTERS.write_text(json.dumps(
        {"labels": labels.tolist(), "summaries": summaries},
        ensure_ascii=False, indent=2), encoding="utf-8")
    write_worksheet(summaries, proposed)

    print(f"完成: 写 {CLUSTERS} (labels {len(labels)}, {K} 簇)")
    print(f"命名工作表: {WORKSHEET}")
    sizes = sorted(((s["size"], proposed[s["cluster"]][0]) for s in summaries),
                   reverse=True)
    print("簇规模(建议名):", [(sz, nm) for sz, nm in sizes])


if __name__ == "__main__":
    main()
