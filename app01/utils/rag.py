"""制度知识库检索.

用 SQL 的 icontains 做关键词召回，再按命中词数量与标题权重排序，
为 T3 的"上下文注入"提供资料片段。
"""
import re

from django.db.models import Q

from app01 import models

# 无区分度的疑问词片段，避免把"什么""怎么"当成检索词
STOP_GRAMS = {
    "什么", "怎么", "怎样", "如何", "可以", "是否", "我们", "公司", "请问",
    "一下", "这个", "那个", "需要", "哪些", "多少", "多久", "为什么", "是不",
    "不是", "有没", "没有", "的话", "应该", "能否", "可以吗", "吗", "呢",
}

MAX_QUERY_TERMS = 16


def _candidate_terms(text, max_terms=MAX_QUERY_TERMS):
    """从中文问句中切出 2-3 字片段作为召回词."""
    terms = []
    seen = set()
    for run in re.findall(r"[\u4e00-\u9fa5]+", text or ""):
        for size in (2, 3):
            for start in range(max(0, len(run) - size + 1)):
                gram = run[start:start + size]
                if len(gram) < 2 or gram in STOP_GRAMS or gram in seen:
                    continue
                seen.add(gram)
                terms.append(gram)
    for word in re.findall(r"[A-Za-z]{2,}", text or ""):
        lower = word.lower()
        if lower not in seen:
            seen.add(lower)
            terms.append(lower)
    return terms[:max_terms]


def search_knowledge(question, limit=3):
    """返回与问题最相关的制度条目列表（可能为空）."""
    terms = _candidate_terms(question)
    if not terms:
        return []

    query = Q()
    for term in terms:
        query |= Q(title__icontains=term)
        query |= Q(keywords__icontains=term)
        query |= Q(content__icontains=term)

    rows = models.Knowledge.objects.filter(query, is_active=True)[:30]

    scored = []
    for row in rows:
        title = f"{row.title} {row.keywords}".lower()
        body = row.content.lower()
        score = sum(3 for term in terms if term in title)
        score += sum(1 for term in terms if term in body)
        if score:
            scored.append((score, row))
    scored.sort(key=lambda item: (-item[0], item[1].id))
    return [row for _, row in scored[:limit]]
