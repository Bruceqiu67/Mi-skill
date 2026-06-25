"""SKILL.md 渲染器：将蒸馏结果渲染为可用的 AI Skill"""

from __future__ import annotations

from pathlib import Path

from src.utils.llm_client import MultiLLMClient


class SkillRenderer:
    """将交叉验证结果渲染为 SKILL.md"""

    SKILL_WRITER_SYSTEM = """
你是专业的 Skill 文档撰写专家。你需要根据分析结果生成一个结构化的 SKILL.md。

SKILL.md 中你需要包含以下板块：

```
# 技能名称

## Persona
你是谁？你的角色定位、专业领域、核心特质。

## 核心分析框架（数据驱动，非预设）
你用来分析问题/做判断的结构化方法。
- 不预设任何指标（MACD/RSI 等）
- 基于数据特征做判断

## 判断规则
具体的决策标准和行动指南。
- 每个规则都包含：条件 → 行动
- 规则来源于既有方法论的验证

## 实战案例
真实的场景和应用。
- 每个案例包含：场景 → 行动 → 结果

## 常见误区/风险
容易犯的错误和风险警示。
```

输出风格：简洁、精确、可执行。使用第一人称（"我"）。不添加书中/推文中没有的内容。
    """.strip()

    def __init__(self, llm: MultiLLMClient):
        self.llm = llm

    def render(
        self,
        cross_validation: dict,
        book_skeletons: list[dict],
        tweet_findings: list[dict],
        persona_name: str = "分析专家",
        output_path: Path = Path("SKILL.md"),
    ) -> str:
        """渲染完整的 SKILL.md"""

        # 构建输入材料
        input_material = self._build_input_material(
            cross_validation, book_skeletons, tweet_findings
        )

        print("✍️  正在生成 SKILL.md...")
        skill_content = self.llm.chat(
            system=self.SKILL_WRITER_SYSTEM,
            user=(
                f"请根据以下研究材料，生成一份完整的 SKILL.md。\n\n"
                f"技能名称: {persona_name}\n\n"
                f"## 研究材料\n\n{input_material[:12000]}"
            ),
            temperature=0.4,
            max_tokens=8192,
        )

        # 写入文件
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(skill_content, encoding="utf-8")
        print(f"💾 SKILL.md 已保存到 {output_path}")

        return skill_content

    @staticmethod
    def _build_input_material(
        cross_validation: dict,
        book_skeletons: list[dict],
        tweet_findings: list[dict],
    ) -> str:
        """整合所有输入材料"""
        parts = []

        # 1. 交叉验证摘要
        parts.append("### 交叉验证结果")
        for key, value in cross_validation.items():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        parts.append(f"- {item.get('concept', item.get('book_claim', item.get('insight', item.get('gap', item.get('trait', '')))))}")
                    else:
                        parts.append(f"- {item}")
            elif isinstance(value, str):
                parts.append(f"- {key}: {value}")

        # 2. 推文案例精选
        cases = []
        for f in tweet_findings:
            cases.extend(f.get("cases", []))
        if cases:
            parts.append("\n### 精选实战案例")
            for case in cases[:15]:
                parts.append(f"- 场景: {case.get('situation', '')}")
                parts.append(f"  行动: {case.get('action', '')}")
                parts.append(f"  结果: {case.get('outcome', '')}")

        # 3. 常见误区
        mistakes = []
        for f in tweet_findings:
            mistakes.extend(f.get("common_mistakes", []))
        if mistakes:
            parts.append("\n### 常见误区与警示")
            for m in mistakes[:10]:
                parts.append(f"- ❌ {m.get('mistake', '')}")
                parts.append(f"  ⚠️ {m.get('warning', '')}")

        return "\n".join(parts)
