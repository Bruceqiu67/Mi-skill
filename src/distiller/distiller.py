"""联合蒸馏引擎：将书方法论骨架与推文实战发现交叉验证"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from src.utils.llm_client import MultiLLMClient


class JointDistiller:
    """
    三步蒸馏：

    1. 书方法论骨架 ← BookParser + MethodologyExtractor
    2. 推文开放式发现 ← LLM 分析推文集
    3. 交叉验证 ← 比对书和推文，发现差异/补充/修正
    """

    def __init__(self, llm: MultiLLMClient):
        self.llm = llm

    # ── 步骤 2: 推文发现 ──

    TWEET_DISCOVERY_SYSTEM = """
你是一个行为分析专家。你的任务是从一系列推文中发现隐性知识。

不要预设任何框架。保持开放，让数据说话。

请分析以下推文集，输出 JSON:
{
  "used_frameworks": [
    {"name": "框架名", "frequency": "高频/中频/低频", "description": "她如何使用"}
  ],
  "judgment_rules": [
    {"condition": "什么条件下", "action": "她怎么做", "evidence_count": 出现次数}
  ],
  "unique_insights": [
    "书中没有，但推文里独有的见解"
  ],
  "corrections": [
    {"claim": "书中的观点", "revised": "推文中如何修正/细化"}
  ],
  "cases": [
    {"situation": "场景描述", "action": "她实际做了什么", "outcome": "结果", "tweet_snippet": "推文原文片段"}
  ],
  "common_mistakes": [
    {"mistake": "常见错误", "warning": "她的警示"}
  ]
}
    """.strip()

    def discover_from_tweets(self, tweets: list[dict], batch_size: int = 50) -> list[dict]:
        """分批对推文进行开放式发现，返回每批的分析结果"""
        batches = []
        findings = []

        for i in range(0, len(tweets), batch_size):
            batch = tweets[i:i + batch_size]
            batches.append(batch)

        print(f"🔍 正在分析 {len(tweets)} 条推文（{len(batches)} 批）...")

        for idx, batch in enumerate(batches):
            tweet_texts = "\n---\n".join(
                f"[{t.get('timestamp', '')}] {t['text']}"
                for t in batch
            )

            try:
                result = self.llm.chat_json(
                    system=self.TWEET_DISCOVERY_SYSTEM,
                    user=f"请分析以下 {len(batch)} 条推文:\n\n{tweet_texts[:12000]}",
                    temperature=0.4,
                )
                findings.append(result)
            except Exception as e:
                findings.append({
                    "_batch": idx,
                    "_error": str(e),
                    "used_frameworks": [],
                    "judgment_rules": [],
                    "unique_insights": [],
                    "corrections": [],
                    "cases": [],
                    "common_mistakes": [],
                })

            print(f"  ✓ 第 {idx+1}/{len(batches)} 批完成")

        return findings

    # ── 步骤 3: 交叉验证 ──

    CROSS_VALIDATE_SYSTEM = """
你是一名知识审计专家。你有两份材料：
1. 书中的方法论骨架（结构化知识）
2. 从推文中分析出的实战发现（实战知识）

请进行交叉验证，输出 JSON:
{
  "confirmed": [
    {"concept": "书中概念", "evidence": "推文中多少次验证", "confidence": "高/中/低"}
  ],
  "modified": [
    {"book_claim": "书中说法", "tweet_revision": "推文中的修正", "significance": "重大/细微"}
  ],
  "new_from_tweets": [
    {"insight": "书中没有的全新内容", "source": "来自推文", "importance": "高/中/低"}
  ],
  "contradictions": [
    {"book": "书中观点", "tweet": "推文观点", "analysis": "为什么有差异"}
  ],
  "gap_filled": [
    {"gap": "书中未覆盖的领域", "tweet_fill": "推文如何补充"}
  ],
  "persona_traits": [
    {"trait": "她的核心特质/风格", "evidence": "来自推文的证据"}
  ]
}
    """.strip()

    def cross_validate(
        self,
        book_skeletons: list[dict],
        tweet_findings: list[dict],
    ) -> dict:
        """联合交叉验证"""
        # 压缩书骨架
        book_summary = self._compress_book(book_skeletons)
        # 压缩推文发现
        tweet_summary = self._compress_tweet_findings(tweet_findings)

        prompt = (
            f"## 书的方法论骨架\n\n{book_summary[:6000]}\n\n"
            f"## 推文实战发现\n\n{tweet_summary[:6000]}"
        )

        return self.llm.chat_json(
            system=self.CROSS_VALIDATE_SYSTEM,
            user=prompt,
            temperature=0.3,
        )

    @staticmethod
    def _compress_book(skeletons: list[dict]) -> str:
        """将多章骨架压缩为摘要"""
        lines = []
        for s in skeletons:
            lines.append(f"### {s.get('_chapter', '')}")
            for concept in s.get("core_concepts", []):
                lines.append(f"- 概念: {concept}")
            for fw in s.get("frameworks", []):
                lines.append(f"- 框架: {fw.get('name', '')}: {' → '.join(fw.get('steps', []))}")
            for rule in s.get("rules", []):
                lines.append(f"- 规则: 如果{rule.get('condition', '')} → {rule.get('action', '')}")
        return "\n".join(lines)

    @staticmethod
    def _compress_tweet_findings(findings: list[dict]) -> str:
        """将多批推文发现压缩"""
        merged = {
            "used_frameworks": {},
            "judgment_rules": [],
            "unique_insights": set(),
            "corrections": [],
            "cases": [],
            "common_mistakes": [],
        }

        for f in findings:
            for fw in f.get("used_frameworks", []):
                name = fw.get("name", "")
                if name:
                    merged["used_frameworks"][name] = merged["used_frameworks"].get(name, 0) + 1
            merged["judgment_rules"].extend(f.get("judgment_rules", []))
            for insight in f.get("unique_insights", []):
                merged["unique_insights"].add(insight)
            merged["corrections"].extend(f.get("corrections", []))
            merged["cases"].extend(f.get("cases", []))
            merged["common_mistakes"].extend(f.get("common_mistakes", []))

        lines = ["## 推文发现汇总"]
        lines.append("\n### 使用框架")
        for name, count in sorted(merged["used_frameworks"].items(), key=lambda x: -x[1]):
            lines.append(f"- {name} (提及 {count} 批次)")
        lines.append("\n### 独特见解")
        for insight in merged["unique_insights"]:
            lines.append(f"- {insight}")
        lines.append(f"\n### 判断规则 ({len(merged['judgment_rules'])} 条)")
        for rule in merged["judgment_rules"][:20]:
            lines.append(f"- 当{rule.get('condition', '')} → {rule.get('action', '')}")
        lines.append(f"\n### 实战案例 ({len(merged['cases'])} 个)")
        for case in merged["cases"][:10]:
            lines.append(f"- {case.get('situation', '')} → {case.get('action', '')} ({case.get('outcome', '')})")
        lines.append(f"\n### 常见误区 ({len(merged['common_mistakes'])} 条)")
        for m in merged["common_mistakes"][:10]:
            lines.append(f"- ❌ {m.get('mistake', '')} → ⚠️ {m.get('warning', '')}")

        return "\n".join(lines)
