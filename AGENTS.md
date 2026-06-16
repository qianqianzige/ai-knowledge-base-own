# AGENTS.md — AI 知识库项目

> 本文件是项目的"大脑"——OpenCode 启动时自动加载，指导所有 Agent 的行为。

## 项目定义

**AI Knowledge Base（AI 知识库）** 是一个自动化技术情报收集与分析系统。
它持续追踪 GitHub Trending、Hacker News、arXiv 等来源，将分散的技术资讯
转化为结构化、可检索的知识条目。

### 核心价值
- 每日自动采集 AI/LLM/Agent 领域的高质量技术文章与开源项目
- 通过 Agent 协作完成 **采集 → 分析 → 整理** 三阶段流水线
- 输出格式统一的 JSON 知识条目，便于下游应用消费

## 项目结构

```
v1-skeleton/
├── AGENTS.md                          # 项目记忆文件（本文件）
├── .env.example                       # 环境变量模板
├── README.md                          # 使用说明
├── .opencode/
│   ├── agents/
│   │   ├── collector.md               # 采集 Agent 角色定义
│   │   ├── analyzer.md                # 分析 Agent 角色定义
│   │   └── organizer.md               # 整理 Agent 角色定义
│   └── skills/
│       ├── github-trending/SKILL.md   # GitHub Trending 采集技能
│       └── tech-summary/SKILL.md      # 技术摘要生成技能
└── knowledge/
    ├── raw/                           # 原始采集数据（JSON）
    └── articles/                      # 整理后的知识条目（JSON）
```

## 编码规范

### 文件命名
- 原始数据：`knowledge/raw/{source}-{YYYY-MM-DD}.json`
  - 例：`knowledge/raw/github-trending-2026-03-17.json`
  - 例：`knowledge/raw/hackernews-top-2026-03-17.json`
- 知识条目：`knowledge/articles/{YYYY-MM-DD}-{slug}.json`
  - 例：`knowledge/articles/2026-03-17-openai-agents-sdk.json`
- 索引文件：`knowledge/articles/index.json`

### JSON 格式
- 使用 2 空格缩进
- 日期格式：ISO 8601（`YYYY-MM-DDTHH:mm:ssZ`）
- 字符编码：UTF-8
- 每个知识条目必须包含：`id`, `title`, `source`, `url`, `collected_at`, `summary`, `tags`, `relevance_score`

### 语言约定
- 代码、JSON 键名、文件名：英文
- 摘要、分析、注释：中文
- 标签（tags）：英文小写，用连字符分隔（如 `large-language-model`）

## 工作流规则

### 三阶段流水线

```
[Collector] ──采集──→ knowledge/raw/
                          │
[Analyzer]  ──分析──→ knowledge/raw/ (enriched)
                          │
[Organizer] ──整理──→ knowledge/articles/
```

### Agent 协作规则

1. **单向数据流**：Collector → Analyzer → Organizer，不可反向
2. **职责隔离**：每个 Agent 只操作自己权限范围内的文件
3. **幂等性**：重复运行同一天的采集不应产生重复条目
4. **质量门控**：Analyzer 评分低于 0.6 的条目，Organizer 应丢弃
5. **可追溯**：每个条目保留 `source_url` 和 `collected_at` 用于溯源

### Agent 调用方式

在 OpenCode 中使用 `@` 语法调用特定 Agent：

```
@collector 采集今天的 GitHub Trending 数据
@analyzer 分析 knowledge/raw/github-trending-2026-03-17.json
@organizer 整理今天所有已分析的原始数据
```

也可以在对话中要求主 Agent 依次委派子 Agent，实现流水线作业。

### 错误处理
- 网络请求失败时，记录错误并跳过该条目，不中断整体流程
- API 限流时，等待后重试，最多 3 次
- 数据格式异常时，写入 `knowledge/raw/errors-{date}.json` 供人工排查

<<<<<<< HEAD
# 7. 多 Agent 协作规范
## 7.1 权限控制
| Agent | 可读目录 | 可写目录 | 禁止访问 |
|-------|---------|---------|---------|
| CrawlerAgent | config/ | output/raw/ | output/analyzed/、output/final/ |
| AnalyzerAgent | output/raw/、config/ | output/analyzed/ | output/final/ |
| FormatterAgent | output/analyzed/、config/ | output/final/ | output/raw/ |

每个 Agent 只能写入自己负责的输出目录
每个 Agent 只能读取上游 Agent 的输出目录
禁止任何 Agent 修改或删除上游已产出的文件
## 7.2 质量控制
- CrawlerAgent：每条采集数据必须包含 source、url、title、crawled_at 字段，缺失任一字段则丢弃该条目
- AnalyzerAgent：为每条内容标注 quality_score（1-5分），低于 3 分的条目标记为 low_quality 并在最终输出中过滤
- FormatterAgent：最终 JSON 必须通过 json_schema_validate 技能校验，校验失败则拒绝写入并触发告警
## 7.3 可追溯性
每个阶段的输出文件名包含 git-short-hash，可追溯至具体代码版本
每条数据在流转过程中携带 trace_id（格式：{date}_{source}_{seq}），贯穿采集→分析→整理全链路
FormatterAgent 在最终输出中保留 pipeline_meta 字段，记录各阶段的执行时间、Agent 版本、输入输出文件路径
```
{
  "pipeline_meta": {
    "trace_id": "2026-04-24_arxiv_001",
    "crawler": { "agent_version": "1.0.0", "output_file": "arxiv_2026-04-24_a1b2c3d.json", "executed_at": "2026-04-24T08:00:00Z" },
    "analyzer": { "agent_version": "1.0.0", "output_file": "analyzed_2026-04-24_a1b2c3d.json", "executed_at": "2026-04-24T08:05:00Z" },
    "formatter": { "agent_version": "1.0.0", "output_file": "knowledge_2026-04-24_v1_a1b2c3d.json", "executed_at": "2026-04-24T08:10:00Z" }
  }
}
```
## 7.4 幂等性
- CrawlerAgent：同一 source + date 组合重复执行时，覆盖 output/raw/ 中的同名文件，不产生重复文件
- AnalyzerAgent：基于 url 字段去重，同一 URL 的内容只保留最新一次分析结果
- FormatterAgent：同日重复执行时递增版本号 v{N}，不覆盖已有版本；输出前检查 output/final/ 是否存在相同 content_hash 的文件，若存在则跳过
# 8. 异常处理
## 8.1 异常分类
| 异常类型 | 说明 | 处理方式 |
|---------|------|---------|
| CrawlTimeoutError | 数据源请求超时 | 重试3次，间隔递增（5s/15s/30s），仍失败则跳过该源，记录日志 |
| CrawlRateLimitError | 触发数据源频率限制 | 暂停当前源采集，等待冷却期后重试，arXiv 遵守每3秒1次限制 |
| AnalysisModelError | DeepSeek 模型调用失败 | 重试2次，仍失败则将该条目标记为 analysis_failed，跳过不阻塞流水线 |
| SchemaValidationError | 最终 JSON 校验失败 | 拒绝写入 output/final/，将校验错误详情写入日志，通知人工介入 |
| GitCommitError | Git 提交失败 | 记录错误日志，文件保留在 output/final/，等待人工修复后重新提交 |

## 8.2 异常处理原则
- 不阻塞流水线：单条数据异常不影响其余数据的正常处理
- 完整记录：所有异常写入 logs/{date}_errors.json，包含 trace_id、异常类型、错误信息、发生时间
- 异常标记：异常数据在输出 JSON 中携带 "status": "error" 和 "error_detail" 字段，不会混入正常数据
- 人工兜底：SchemaValidationError 和 GitCommitError 触发告警，需人工介入处理
=======
## 技术栈
- **运行时**：OpenCode + LLM（DeepSeek / Qwen）
- **数据源**：GitHub API v3、Hacker News API (firebase)
- **输出格式**：JSON
- **版本管理**：Git
>>>>>>> 0045625 (Update AGENTS.md)
