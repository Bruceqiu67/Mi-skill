# 📚🐦 书 + 推文联合蒸馏管线

将方法论书（PDF/EPUB）与 Twitter 实战推文联合蒸馏，自动生成可用的 **AI Skill (SKILL.md)**。

## 流程

```
书 (PDF/EPUB)                   推文 (Playwright 爬取)
     │                                │
     ▼                                ▼
  逐章提取方法论骨架              LLM 开放式发现
     │                                │
     └──────────┬────────────────────┘
                ▼
          联合交叉验证
                │
                ▼
           SKILL.md
  ├ Persona
  ├ 核心分析框架（数据驱动）
  ├ 判断规则
  ├ 实战案例
  └ 常见误区/风险
```

## 快速开始

### 1. 安装依赖

```bash
pip install -e .
playwright install chromium   # 安装 Playwright 浏览器
```

### 2. 配置

```bash
# 初始化本地配置
python -m src.cli init-config
# 编辑 config/settings.local.yaml
```

填入以下内容：

```yaml
book:
  path: "./data/book.pdf"      # 或 .epub

twitter:
  username: "目标账号"          # 不含 @
  max_tweets: 6000

llm:
  api_key: "sk-..."            # OpenAI API Key
  # 或使用环境变量: set LLM_API_KEY=sk-...
```

### 3. 运行

```bash
# 完整流程
python -m src.cli run

# 只采集推文（适合先跑采集，再分析）
python -m src.cli scrape-only

# 使用已有推文文件，跳过采集
python -m src.cli run --tweet-file output/raw_tweets.jsonl

# 跳过书或推文
python -m src.cli run --skip-book
python -m src.cli run --skip-tweets

# 检查配置状态
python -m src.cli status
```

## 输出

| 文件 | 说明 |
|------|------|
| `output/raw_tweets.jsonl` | 原始推文数据 |
| `output/book_skeleton.md` | 书的逐章方法论骨架 |
| `output/tweet_findings.jsonl` | 推文分析发现 |
| `output/cross_validation.md` | 联合交叉验证报告 |
| `output/SKILL.md` | 最终 AI Skill 文件 |

## 架构

```
src/
├── cli.py              # CLI 入口 (Click)
├── book_parser/
│   ├── __init__.py
│   └── parser.py       # PDF/EPUB 解析 + 方法论提取
├── tweet_scraper/
│   └── __init__.py     # Playwright 推文爬虫
├── distiller/
│   ├── __init__.py
│   └── distiller.py    # 联合蒸馏引擎
├── skill_renderer/
│   └── __init__.py     # SKILL.md 渲染器
└── utils/
    ├── config.py       # 配置管理
    └── llm_client.py   # LLM API 封装
```

## 支持的书格式

- **PDF** — 使用 PyMuPDF (fitz)，自动检测目录/章节
- **EPUB** — 使用 ebooklib + BeautifulSoup，按 HTML 文档分章

## 自定义设置

编辑 `config/settings.local.yaml`:

| 参数 | 说明 |
|------|------|
| `llm.api_base` | 支持 OpenAI 兼容 API（包括 ollama、vllm 等本地模型） |
| `llm.model` | 模型名称 |
| `twitter.scroll_pause_ms` | 滚动等待毫秒数（网速慢可调大） |
| `twitter.headless` | 是否无头模式（调试时可设为 false） |
