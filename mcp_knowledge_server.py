#!/usr/bin/env python3
"""
MCP Knowledge Base Server
提供本地 AI 知识库的搜索与查询服务，使用 JSON-RPC 2.0 over stdio 协议。
无第三方依赖，仅使用 Python 标准库。

支持的工具：
  - search_articles: 按关键词搜索文章
  - get_article:    按 ID 获取文章完整内容
  - knowledge_stats: 返回知识库统计信息
"""

import json
import os
import sys
from collections import Counter
from typing import Any

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ARTICLES_DIR = os.environ.get(
    "KNOWLEDGE_ARTICLES_DIR",
    os.path.join(SCRIPT_DIR, "knowledge", "articles"),
)

SERVER_NAME = "knowledge-base-server"
SERVER_VERSION = "1.0.0"
PROTOCOL_VERSION = "2024-11-05"


def log(msg: str) -> None:
    """Write debug messages to stderr so stdout stays clean for JSON-RPC."""
    print(f"[mcp-server] {msg}", file=sys.stderr, flush=True)


def load_articles() -> list[dict[str, Any]]:
    """Load all article JSON files from the articles directory (excluding index.json)."""
    articles: list[dict[str, Any]] = []
    if not os.path.isdir(ARTICLES_DIR):
        log(f"articles directory not found: {ARTICLES_DIR}")
        return articles

    for filename in sorted(os.listdir(ARTICLES_DIR)):
        if filename == "index.json" or not filename.endswith(".json"):
            continue
        filepath = os.path.join(ARTICLES_DIR, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and "id" in data:
                articles.append(data)
        except (json.JSONDecodeError, OSError) as e:
            log(f"skip {filename}: {e}")
            continue

    return articles


# ─── Tool implementations ──────────────────────────────────────────────

def search_articles(keyword: str, limit: int = 5) -> list[dict[str, Any]]:
    """Search articles by keyword matching title, summary, and tags."""
    articles = load_articles()
    keyword_lower = keyword.lower()
    scored: list[tuple[int, dict[str, Any]]] = []

    for article in articles:
        title = (article.get("title") or "").lower()
        summary = (article.get("summary") or "").lower()
        tags = [t.lower() for t in (article.get("tags") or [])]

        score = 0
        if keyword_lower in title:
            score += 10
        if keyword_lower in summary:
            score += 5
        if any(keyword_lower in tag for tag in tags):
            score += 3

        if score > 0:
            scored.append((score, article))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [article for _, article in scored[:limit]]


def get_article(article_id: str) -> dict[str, Any] | None:
    """Get a single article by its unique ID."""
    articles = load_articles()
    for article in articles:
        if article.get("id") == article_id:
            return article
    return None


def knowledge_stats() -> dict[str, Any]:
    """Return knowledge base statistics."""
    articles = load_articles()

    # Source distribution
    source_counts: Counter[str] = Counter()
    tag_counts: Counter[str] = Counter()
    total_score = 0
    score_count = 0

    for article in articles:
        source = article.get("source", "unknown")
        source_counts[source] += 1

        for tag in (article.get("tags") or []):
            tag_counts[tag] += 1

        # Normalize score field (some use "score" 0-10, some use "relevance_score" 0-1)
        raw_score = article.get("relevance_score") or article.get("score")
        if raw_score is not None:
            score = raw_score / 10 if raw_score > 1 else raw_score
            total_score += score
            score_count += 1

    top_tags = tag_counts.most_common(20)

    return {
        "total_articles": len(articles),
        "source_distribution": dict(source_counts),
        "popular_tags": [{"tag": tag, "count": count} for tag, count in top_tags],
        "average_relevance": round(total_score / score_count, 2) if score_count else 0,
    }


# ─── MCP JSON-RPC handlers ─────────────────────────────────────────────

def build_tools_list() -> dict[str, Any]:
    return {
        "tools": [
            {
                "name": "search_articles",
                "description": (
                    "按关键词搜索知识库文章，匹配标题、摘要和标签。"
                    "返回匹配度最高的文章列表（含 id, title, source, summary, tags 字段）。"
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "keyword": {
                            "type": "string",
                            "description": "搜索关键词（支持中文或英文）",
                        },
                        "limit": {
                            "type": "integer",
                            "default": 5,
                            "description": "返回结果数量上限，默认 5",
                        },
                    },
                    "required": ["keyword"],
                },
            },
            {
                "name": "get_article",
                "description": (
                    "按文章 ID 获取完整内容，包含完整摘要、标签、评分等全部字段。"
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "article_id": {
                            "type": "string",
                            "description": "文章唯一标识 ID，例如 kb-2026-06-17-006 或 github-20260617-001",
                        },
                    },
                    "required": ["article_id"],
                },
            },
            {
                "name": "knowledge_stats",
                "description": (
                    "返回知识库统计信息：文章总数、来源分布、热门标签 Top 20、"
                    "平均相关性评分。"
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
        ]
    }


def handle_initialize(_msg_id: Any, _params: dict[str, Any]) -> dict[str, Any]:
    return {
        "protocolVersion": PROTOCOL_VERSION,
        "capabilities": {
            "tools": {},
        },
        "serverInfo": {
            "name": SERVER_NAME,
            "version": SERVER_VERSION,
        },
    }


def handle_tools_list(_msg_id: Any) -> dict[str, Any]:
    return build_tools_list()


def handle_tools_call(_msg_id: Any, params: dict[str, Any]) -> dict[str, Any]:
    tool_name = params.get("name", "")
    arguments = params.get("arguments", {})

    try:
        if tool_name == "search_articles":
            keyword = arguments.get("keyword", "")
            limit = int(arguments.get("limit", 5))
            if not keyword:
                raise ValueError("keyword 参数不能为空")
            results = search_articles(keyword, limit)
            text = json.dumps(results, ensure_ascii=False, indent=2)

        elif tool_name == "get_article":
            article_id = arguments.get("article_id", "")
            if not article_id:
                raise ValueError("article_id 参数不能为空")
            article = get_article(article_id)
            if article is None:
                text = json.dumps(
                    {"error": f"未找到 ID 为 {article_id} 的文章"},
                    ensure_ascii=False,
                )
            else:
                text = json.dumps(article, ensure_ascii=False, indent=2)

        elif tool_name == "knowledge_stats":
            stats = knowledge_stats()
            text = json.dumps(stats, ensure_ascii=False, indent=2)

        else:
            text = json.dumps(
                {"error": f"未知工具: {tool_name}"}, ensure_ascii=False
            )

    except Exception as e:
        text = json.dumps({"error": str(e)}, ensure_ascii=False)

    return {
        "content": [
            {"type": "text", "text": text}
        ]
    }


# ─── Main loop ─────────────────────────────────────────────────────────

def send_response(msg_id: Any, result: Any = None, error: dict | None = None) -> None:
    """Write a JSON-RPC 2.0 response to stdout."""
    response: dict[str, Any] = {"jsonrpc": "2.0", "id": msg_id}
    if error is not None:
        response["error"] = error
    else:
        response["result"] = result
    sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def main() -> None:
    """Read JSON-RPC messages from stdin, dispatch, and write responses to stdout."""
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")

    log(f"server starting, articles dir: {ARTICLES_DIR}")

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
        except json.JSONDecodeError as e:
            log(f"invalid JSON: {e}")
            continue

        msg_id = request.get("id")
        method = request.get("method", "")
        params = request.get("params", {})

        # Notifications have no id — no response needed
        if msg_id is None:
            log(f"notification: {method}")
            continue

        try:
            if method == "initialize":
                result = handle_initialize(msg_id, params)
            elif method == "tools/list":
                result = handle_tools_list(msg_id)
            elif method == "tools/call":
                result = handle_tools_call(msg_id, params)
            elif method == "resources/list":
                result = {"resources": []}
            elif method == "prompts/list":
                result = {"prompts": []}
            else:
                send_response(
                    msg_id,
                    error={
                        "code": -32601,
                        "message": f"Method not found: {method}",
                    },
                )
                continue

            send_response(msg_id, result=result)

        except Exception as e:
            log(f"internal error: {e}")
            send_response(
                msg_id,
                error={"code": -32603, "message": str(e)},
            )


if __name__ == "__main__":
    main()
