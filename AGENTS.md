# 1. 项目概述
本项目是一个自动化 AI 知识采集与整理系统，通过三个 Agent（采集者、分析者、整理者）协作，定期从 GitHub Trending、Hacker News、arXiv 等来源抓取最新 AI 领域知识，经分析后整理为 JSON 格式输出，使用 Git 进行版本控制。

# 2. 技术栈
| 类别 | 选型 |
|------|------|
| Agent 框架 | opencode |
| 大语言模型 | DeepSeek（deepseek-chat / deepseek-reasoner） |
| 输出格式 | JSON |
| 版本控制 | Git |
| 数据来源 | GitHub Trending、Hacker News、arXiv |

# 3. 项目结构
```
ai-knowledge-base/
├── agents/
│   ├── crawler_agent.py          # 采集者 Agent
│   ├── analyzer_agent.py         # 分析者 Agent
│   └── formatter_agent.py        # 整理者 Agent
├── skills/
│   ├── source_crawl.py           # 数据源抓取技能
│   ├── content_classify.py       # 内容分类技能
│   ├── summary_extract.py        # 摘要提取技能
│   ├── dedup_filter.py           # 去重过滤技能
│   └── json_schema_validate.py   # JSON Schema 校验技能
├── output/
│   ├── raw/                      # 采集者原始输出
│   │   └── {source}_{YYYY-MM-DD}_{git-short-hash}.json
│   ├── analyzed/                 # 分析者分析输出
│   │   └── analyzed_{YYYY-MM-DD}_{git-short-hash}.json
│   └── final/                    # 整理者最终输出
│       └── knowledge_{YYYY-MM-DD}_v{N}_{git-short-hash}.json
├── config/
│   └── sources.json              # 数据源配置
├── .gitignore
└── Agents.md
```
输出文件命名规范
| 阶段 | 命名格式 | 示例 |
|------|---------|------|
| 采集 | {source}_{date}_{git-short-hash}.json | arxiv_2026-04-24_a1b2c3d.json |
| 分析 | analyzed_{date}_{git-short-hash}.json | analyzed_2026-04-24_a1b2c3d.json |
| 最终 | knowledge_{date}_v{N}_{git-short-hash}.json | knowledge_2026-04-24_v1_a1b2c3d.json |

{git-short-hash}：当前 Git commit 的前7位哈希，确保输出可追溯至具体提交
v{N}：同日多次产出时递增的版本序号
# 4. Agent 角色说明
## 4.1 采集者（CrawlerAgent）
职责：从指定数据源抓取 AI 领域原始内容
数据源：GitHub Trending、Hacker News、arXiv（cs.AI、cs.LG）
输出：原始数据 JSON，写入 output/raw/
```
{
  "agent": "CrawlerAgent",
  "role": "crawler",
  "sources": ["github_trending", "hacker_news", "arxiv"],
  "skills": ["source_crawl"],
  "output_dir": "output/raw/",
  "output_format": "json"
}
```

## 4.2 分析者（AnalyzerAgent）
职责：对采集者的原始数据进行去重、分类、摘要提炼
处理逻辑：
调用 DeepSeek 模型生成内容摘要
按主题分类（模型、工具、论文、开源项目等）
去除重复或低质量条目，标注质量评分
输出：结构化分析结果 JSON，写入 output/analyzed/
```
{
  "agent": "AnalyzerAgent",
  "role": "analyzer",
  "model": "deepseek-chat",
  "skills": ["content_classify", "summary_extract", "dedup_filter"],
  "output_dir": "output/analyzed/",
  "output_format": "json"
}
```

## 4.3 整理者（FormatterAgent）
职责：将分析者的结构化数据转化为最终 JSON 输出，执行 Schema 校验，触发 Git 归档
输出：最终 JSON 文件，写入 output/final/
```
{
  "agent": "FormatterAgent",
  "role": "formatter",
  "skills": ["json_schema_validate"],
  "output_dir": "output/final/",
  "output_format": "json",
  "version_control": "git",
  "commit_message_format": "feat(knowledge): {date} v{version} update"
}
```

# 5. 工作流
```
CrawlerAgent（采集）
    └─→ output/raw/*.json
            └─→ AnalyzerAgent（分析）
                    └─→ output/analyzed/*.json
                            └─→ FormatterAgent（整理）
                                    └─→ output/final/*.json
                                    └─→ git add + git commit
```

# 6. 编码规范
·Agent 类名：XxxAgent（大驼峰），如 CrawlerAgent、AnalyzerAgent、FormatterAgent
· Skill 文件名：snake_case.py，如 source_crawl.py
- 方法名：snake_case，如 crawl_source()、analyze_content()、format_output()
- 常量名：UPPER_SNAKE_CASE，如 SOURCE_GITHUB = "github_trending"
· JSON 字段名：统一 snake_case
· 每个 Agent 职责单一，禁止跨角色直接耦合
Agent 间通信：仅通过 output/ 目录下的 JSON 文件传递数据，不允许内存直传
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
CrawlerAgent：每条采集数据必须包含 source、url、title、crawled_at 字段，缺失任一字段则丢弃该条目
AnalyzerAgent：为每条内容标注 quality_score（1-5分），低于 3 分的条目标记为 low_quality 并在最终输出中过滤
FormatterAgent：最终 JSON 必须通过 json_schema_validate 技能校验，校验失败则拒绝写入并触发告警
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
CrawlerAgent：同一 source + date 组合重复执行时，覆盖 output/raw/ 中的同名文件，不产生重复文件
AnalyzerAgent：基于 url 字段去重，同一 URL 的内容只保留最新一次分析结果
FormatterAgent：同日重复执行时递增版本号 v{N}，不覆盖已有版本；输出前检查 output/final/ 是否存在相同 content_hash 的文件，若存在则跳过
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
不阻塞流水线：单条数据异常不影响其余数据的正常处理
完整记录：所有异常写入 logs/{date}_errors.json，包含 trace_id、异常类型、错误信息、发生时间
异常标记：异常数据在输出 JSON 中携带 "status": "error" 和 "error_detail" 字段，不会混入正常数据
人工兜底：SchemaValidationError 和 GitCommitError 触发告警，需人工介入处理
