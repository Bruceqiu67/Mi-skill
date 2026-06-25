"""配置模块单元测试"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from src.utils.config import Config, BookConfig, TwitterConfig, LLMConfig, OutputConfig


# ── 测试数据 ──

SAMPLE_CONFIG = {
    "book": {
        "path": "./data/book.pdf",
        "url": "",
    },
    "twitter": {
        "username": "testuser",
        "max_tweets": 100,
        "headless": True,
        "scroll_pause_ms": 1000,
    },
    "llm": {
        "api_base": "https://api.openai.com/v1",
        "model": "gpt-4o",
        "api_key": "sk-test123",
    },
    "output": {
        "dir": "./test_output",
    },
}


@pytest.fixture
def config_file():
    """创建临时配置文件"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as f:
        yaml.dump(SAMPLE_CONFIG, f, allow_unicode=True)
        path = f.name
    yield Path(path)
    os.unlink(path)


class TestConfig:
    def test_load_from_file(self, config_file):
        cfg = Config.load(config_file)
        assert cfg is not None
        assert isinstance(cfg, Config)

    def test_book_config(self, config_file):
        cfg = Config.load(config_file)
        assert cfg.book.path == "./data/book.pdf"
        assert cfg.book.url == ""
        assert cfg.book.is_configured() is False  # file doesn't exist

    def test_twitter_config(self, config_file):
        cfg = Config.load(config_file)
        assert cfg.twitter.username == "testuser"
        assert cfg.twitter.max_tweets == 100
        assert cfg.twitter.is_configured() is True

    def test_llm_config(self, config_file):
        cfg = Config.load(config_file)
        assert cfg.llm.model == "gpt-4o"
        assert cfg.llm.api_key == "sk-test123"
        assert cfg.llm.is_configured() is True

    def test_output_config(self, config_file):
        cfg = Config.load(config_file)
        assert cfg.output.dir == "./test_output"
        assert str(cfg.output.dir_path) == "test_output"

    def test_env_override(self, config_file):
        os.environ["LLM_API_KEY"] = "sk-env-key"
        os.environ["LLM_MODEL"] = "gpt-4o-mini"
        cfg = Config.load(config_file)
        assert cfg.llm.api_key == "sk-test123"  # YAML takes precedence
        assert cfg.llm.model == "gpt-4o"
        del os.environ["LLM_API_KEY"]
        del os.environ["LLM_MODEL"]


class TestBookConfig:
    def test_resolved_path_none_when_not_exists(self):
        cfg = BookConfig({"path": "./nonexistent/book.pdf"})
        assert cfg.resolved_path is None

    def test_not_configured_when_empty(self):
        cfg = BookConfig({"path": "", "url": ""})
        assert cfg.is_configured() is False

    def test_configured_by_url(self):
        cfg = BookConfig({"path": "", "url": "https://example.com/book.pdf"})
        assert cfg.is_configured() is True


class TestTwitterConfig:
    def test_not_configured_when_empty(self):
        cfg = TwitterConfig({"username": ""})
        assert cfg.is_configured() is False

    def test_default_values(self):
        cfg = TwitterConfig({"username": "user"})
        assert cfg.max_tweets == 6000
        assert cfg.headless is True
        assert cfg.scroll_pause_ms == 1500


class TestLLMConfig:
    def test_not_configured_when_no_key(self):
        cfg = LLMConfig({"api_key": ""})
        assert cfg.is_configured() is False

    def test_defaults(self):
        cfg = LLMConfig({})
        assert cfg.api_base == "https://api.openai.com/v1"
        assert cfg.model == "gpt-4o"


class TestOutputConfig:
    def test_defaults(self):
        cfg = OutputConfig({})
        assert cfg.dir == "./output"
        assert cfg.book_skeleton == "book_skeleton.md"
        assert cfg.tweet_findings == "tweet_findings.jsonl"
        assert cfg.cross_validation == "cross_validation.md"
        assert cfg.final_skill == "SKILL.md"
