# Mi-Skill：资金流逆向交易法

**从一本 710 页的交易书 + 603 条实战推文中蒸馏出的 AI 交易 Skill。**

- 书作者：Mistery（@Mimiwftt）
- 书内容：A 股交易方法论（基础认知、技术指标、仓位管理、主力行为、交易心理）
- 推文：2026 年 4–6 月实战交易记录

> 这个仓库的核心产物是 **[`SKILL.md`](./SKILL.md)**——一个可直接用于 AI 助手的交易分析 Skill。

---

## 📦 SKILL.md 内容速览

| 板块 | 内容 |
|------|------|
| **Persona** | 6 个核心特质（风险厌恶、逆向思维、资金导向、纪律至上、长期主义、独立思考） |
| **核心分析框架** | 四维资金流分析（宏观→中观→微观→执行） |
| **判断规则** | 27 条，分 5 类：仓位管理 / 进场 / 出场 / 风控 / 情绪，标注 **[书中]** / **[推文验证]** / **[推文补充]** |
| **实战案例** | 5 个（宿迁某股主升浪、恒指精准抄底、大盘诱多识别等） |
| **常见误区** | 7 个（频繁交易、追涨杀跌、迷信独立判断、机构抱团抄底等） |
| **核心心法** | 8 条（资金为王、逆向思维、买点决定一切、让主力先动等） |

## 🧠 它是怎么来的

```
书.pdf (710页, 303章)     @Mimiwftt (603条推文)
        │                        │
        ▼                        ▼
  逐章方法论骨架              LLM 开放式发现
  (672 概念, 192 框架,      (18 独特见解, 16 实战案例,
   623 规则)                 27 判断规则, 14 常见误区)
        │                        │
        └──────────┬─────────────┘
                   ▼
             交叉验证
         (3 家 LLM 并行蒸馏:
          DeepSeek + Kimi + MiniMax)
                   │
                   ▼
             SKILL.md
```

## 📂 仓库结构

```
├── 📄 SKILL.md                  ← 最终产物（资金流逆向交易法）
├── 📄 output/book_skeleton.md   ← 书籍方法论的完整骨架（283 章）
├── 📄 output/cross_validation.md  ← 书与推文的交叉验证报告
├── 📁 src/                       ← 蒸馏管线源代码
│   ├── book_parser/              ← PDF/EPUB 解析
│   ├── tweet_scraper/            ← 推文爬取（Playwright）
│   ├── distiller/                ← LLM 联合蒸馏引擎
│   ├── skill_renderer/           ← SKILL.md 渲染器
│   └── utils/                    ← 配置、LLM 客户端
├── 📁 tests/                     ← 27 个单元测试
└── 📄 README.md
```

## ⚙️ 自行运行

```bash
# 1. 安装依赖
pip install -e .
playwright install msedge

# 2. 配置 config/settings.local.yaml
#    （配置多 LLM API Key + 书文件路径）

# 3. 执行蒸馏
python -m src.cli run
```

## 📜 输出文件

| 文件 | 说明 |
|------|------|
| `SKILL.md` | **最终 AI Skill** |
| `output/book_skeleton.md` | 书的方法论骨架 JSON |
| `output/cross_validation.md` | 书 vs 推文交叉验证 |
| `output/tweet_findings.jsonl` | 推文 LLM 分析中间数据 |
| `output/raw_tweets.jsonl` | 原始推文数据 |

## 🔑 数据来源

- **书**：Mistery 所著 A 股交易指南（PDF，710 页）
- **推文**：[@Mimiwftt](https://x.com/Mimiwftt)（2026.04–06，603 条）
- **模型**：DeepSeek-chat、Moonshot-v1-32k、MiniMax-M3 并行蒸馏
