# src/classify.py
"""本地无监督聚类(jieba + TF-IDF + KMeans)发现收藏的主题方向。
0 token、纯本地。簇命名 / 方向解读交给上层(agent)读 clusters.json 后完成。
"""
import re

import jieba
import numpy as np
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer

# 常见中文停用词 + 小红书标题里的水词
_STOP = set("""
的 了 是 我 你 他 她 它 们 在 和 与 也 都 就 这 那 有 个 不 人 一 你们 我们
吗 吧 啊 呀 呢 哦 嘛 又 还 很 太 最 更 被 把 给 让 对 从 到 以 为 之 等 及
怎么 如何 这个 那个 什么 一个 真的 可以 终于 居然 竟然 原来 这样 一定 必须
教程 分享 推荐 合集 攻略 系列 干货 收藏 笔记 超 超级 巨 绝绝子 yyds 建议 全
""".split())


def tokenize(text: str) -> list[str]:
    text = re.sub(r"[^一-龥A-Za-z0-9]+", " ", text or "")
    out = []
    for t in jieba.lcut(text):
        t = t.strip()
        if not t or t in _STOP:
            continue
        if t.isascii() and t.isalpha():   # 保留英文词(AI, PPT...)
            out.append(t.lower())
        elif len(t) >= 2:                  # 中文保留长度>=2
            out.append(t)
    return out


def cluster_titles(titles: list[str], k: int = 16, seed: int = 42) -> tuple[list[int], list[dict]]:
    vec = TfidfVectorizer(tokenizer=tokenize, token_pattern=None,
                          max_df=0.5, min_df=3)
    X = vec.fit_transform(titles)
    km = KMeans(n_clusters=k, random_state=seed, n_init=10)
    labels = km.fit_predict(X)
    terms = vec.get_feature_names_out()

    summaries = []
    for c in range(k):
        idx = np.where(labels == c)[0]
        centroid = km.cluster_centers_[c]
        top_terms = [terms[i] for i in centroid.argsort()[::-1][:12]]
        sims = (X[idx] @ centroid)
        order = np.argsort(sims)[::-1]
        reps = [titles[idx[i]] for i in order[:10]]
        summaries.append({
            "cluster": int(c),
            "size": int(len(idx)),
            "top_terms": top_terms,
            "reps": reps,
        })
    summaries.sort(key=lambda s: s["size"], reverse=True)
    return labels.tolist(), summaries
