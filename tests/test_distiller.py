"""蒸馏引擎和 SKILL 渲染器单元测试"""

from __future__ import annotations

import pytest

from src.distiller.distiller import JointDistiller
from src.skill_renderer import SkillRenderer


class TestJointDistiller:
    def test_system_prompts_exist(self):
        """验证两个系统提示词都定义完整"""
        assert "JSON" in JointDistiller.TWEET_DISCOVERY_SYSTEM
        assert "used_frameworks" in JointDistiller.TWEET_DISCOVERY_SYSTEM
        assert "judgment_rules" in JointDistiller.TWEET_DISCOVERY_SYSTEM
        assert "cases" in JointDistiller.TWEET_DISCOVERY_SYSTEM
        assert "cross_validate" in JointDistiller.CROSS_VALIDATE_SYSTEM.lower() or \
               "JSON" in JointDistiller.CROSS_VALIDATE_SYSTEM

    def test_cross_validate_requires_JSON_output(self):
        assert "JSON" in JointDistiller.CROSS_VALIDATE_SYSTEM

    def test_compress_book_empty(self):
        result = JointDistiller._compress_book([])
        assert result == ""

    def test_compress_book_single_entry(self):
        skeletons = [{
            "_chapter": "第一章",
            "core_concepts": ["概念A: 定义"],
            "frameworks": [{"name": "框架X", "steps": ["步骤1", "步骤2"]}],
            "rules": [{"condition": "A发生", "action": "做B"}],
        }]
        result = JointDistiller._compress_book(skeletons)
        assert "第一章" in result
        assert "概念A" in result
        assert "框架X" in result
        assert "步骤1" in result
        assert "A发生" in result

    def test_compress_tweet_findings_empty(self):
        result = JointDistiller._compress_tweet_findings([])
        assert "推文发现汇总" in result


class TestSkillRenderer:
    def test_skill_writer_system_prompt(self):
        """验证 SKILL 渲染器提示词包含所有关键板块"""
        prompt = SkillRenderer.SKILL_WRITER_SYSTEM
        assert "Persona" in prompt
        assert "分析框架" in prompt
        assert "判断规则" in prompt
        assert "实战案例" in prompt
        assert "常见误区" in prompt
