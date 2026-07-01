"""Router 模式 — 基于意图分类的请求路由

两层分类策略:
1. 关键词快速匹配 — 零成本，覆盖常见场景
2. LLM 分类 — 处理模糊意图，确保不漏判
"""

import json
import os
import urllib.parse
import urllib.request
from typing import Callable

from workflows.model_client import chat, chat_json


# --- 处理器定义 ---

def github_search_handler(query: str) -> str:
    """GitHub 搜索处理器：搜索相关仓库并返回摘要"""
    search_query = query.replace("搜索", "").replace("github", "").strip()
    encoded_query = urllib.parse.quote(search_query)  # 处理空格、中文
    url = f"https://api.github.com/search/repositories?q={encoded_query}&sort=stars&per_page=5"
    headers = {"Accept": "application/vnd.github.v3+json"}

    token = os.getenv("GITHUB_TOKEN", "")
    if token:
        headers["Authorization"] = f"token {token}"

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        results = []
        for repo in data.get("items", []):
            results.append(
                f"- [{repo['full_name']}]({repo['html_url']}) "
                f"⭐{repo['stargazers_count']} — {repo.get('description', '')}"
            )
        return f"GitHub 搜索结果:\n" + "\n".join(results) if results else "未找到相关仓库"
    except Exception as e:
        return f"GitHub 搜索失败: {e}"


def knowledge_query_handler(query: str) -> str:
    """知识库查询处理器：从本地索引检索"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    index_path = os.path.join(base_dir, "knowledge", "articles", "index.json")

    if not os.path.exists(index_path):
        return "知识库为空，请先运行采集工作流。"

    with open(index_path, "r", encoding="utf-8") as f:
        index = json.load(f)
    articles = index.get("articles", []) if isinstance(index, dict) else index

    if not articles:
        return "知识库为空，请先运行采集工作流。"

    # 简单关键词匹配
    query_lower = query.lower()
    matches = [
        entry for entry in articles
        if query_lower in entry.get("title", "").lower()
        or query_lower in entry.get("category", "").lower()
    ]

    if matches:
        lines = [f"- {m['title']} (相关度: {m.get('relevance_score', '?')})" for m in matches[:10]]
        return f"找到 {len(matches)} 条相关知识:\n" + "\n".join(lines)
    return "未找到匹配的知识条目。"


def general_chat_handler(query: str) -> str:
    """通用对话处理器：LLM 直接回答"""
    result, _ = chat(query, system="你是一个专业的 AI 技术顾问。简洁、准确地回答。")
    return result


# --- 路由器核心 ---

HANDLERS: dict[str, Callable[[str], str]] = {
    "github_search": github_search_handler,
    "knowledge_query": knowledge_query_handler,
    "general_chat": general_chat_handler,
}

KEYWORD_RULES: list[tuple[list[str], str]] = [
    (["github", "仓库", "repo", "搜索项目", "trending"], "github_search"),
    (["知识库", "查询", "检索", "已收录", "knowledge"], "knowledge_query"),
]


def classify_intent(query: str) -> str:
    """意图分类：关键词匹配优先，LLM 兜底"""
    query_lower = query.lower()

    # 第一层: 关键词匹配（零成本）
    for keywords, intent in KEYWORD_RULES:
        if any(kw in query_lower for kw in keywords):
            return intent

    # 第二层: LLM 分类
    prompt = f"""请判断以下用户查询的意图类别。

查询: {query}

可选类别:
- github_search: 想搜索 GitHub 上的项目
- knowledge_query: 想查询已有的知识库内容
- general_chat: 一般性技术问题

请只返回类别名称。"""

    result, _ = chat(prompt, system="你是意图分类器。只返回类别名称。", max_tokens=50)
    intent = result.strip().lower()
    return intent if intent in HANDLERS else "general_chat"


def route(query: str) -> str:
    """路由器入口：分类意图并调用对应处理器"""
    intent = classify_intent(query)
    print(f"[Router] 意图: {intent}")
    return HANDLERS[intent](query)


# --- 测试入口 ---
if __name__ == "__main__":
    import sys
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "搜索最近的 AI Agent 框架"
    print(f"查询: {query}\n")
    print(route(query))

