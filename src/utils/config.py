"""配置加载与管理 - 支持多 API 提供商"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import yaml


DEFAULT_CONFIG_PATH = Path("config/settings.yaml")
LOCAL_CONFIG_PATH = Path("config/settings.local.yaml")


class LLMProviderConfig:
    """单个 LLM 提供商配置"""

    def __init__(self, name: str, raw: dict):
        self.name = name
        self.api_base: str = raw.get("api_base", "")
        self.api_key: str = raw.get("api_key", "")
        self.model: str = raw.get("model", "")
        self.weight: int = int(raw.get("weight", 1))

    def is_configured(self) -> bool:
        return bool(self.api_base and self.api_key and self.model)


class MultiLLMConfig:
    """多 LLM 提供商配置"""

    def __init__(self, raw: dict):
        self.providers: list[LLMProviderConfig] = []
        for name, cfg in raw.items():
            if isinstance(cfg, dict) and "api_base" in cfg:
                self.providers.append(LLMProviderConfig(name, cfg))

    @property
    def configured_providers(self) -> list[LLMProviderConfig]:
        return [p for p in self.providers if p.is_configured()]

    def is_configured(self) -> bool:
        return len(self.configured_providers) > 0


class BookConfig:
    def __init__(self, raw: dict):
        self.path: str = raw.get("path", "")
        self.url: str = raw.get("url", "")

    @property
    def resolved_path(self) -> Optional[Path]:
        if self.path:
            p = Path(self.path)
            return p if p.exists() else None
        return None

    def is_configured(self) -> bool:
        return bool(self.resolved_path) or bool(self.url)


class TwitterConfig:
    def __init__(self, raw: dict):
        self.username: str = raw.get("username", "")
        self.max_tweets: int = int(raw.get("max_tweets", 6000))
        self.headless: bool = bool(raw.get("headless", True))
        self.scroll_pause_ms: int = int(raw.get("scroll_pause_ms", 1500))

    def is_configured(self) -> bool:
        return bool(self.username)


class OutputConfig:
    def __init__(self, raw: dict):
        self.dir: str = raw.get("dir", "./output")
        self.book_skeleton: str = raw.get("book_skeleton", "book_skeleton.md")
        self.tweet_findings: str = raw.get("tweet_findings", "tweet_findings.jsonl")
        self.cross_validation: str = raw.get("cross_validation", "cross_validation.md")
        self.final_skill: str = raw.get("final_skill", "SKILL.md")

    @property
    def dir_path(self) -> Path:
        return Path(self.dir)


class Config:
    """层级配置对象"""

    def __init__(self, raw: dict):
        self.raw = raw
        self.book = BookConfig(raw.get("book", {}))
        self.twitter = TwitterConfig(raw.get("twitter", {}))
        self.llm = MultiLLMConfig(raw.get("llm_providers", {}))
        self.output = OutputConfig(raw.get("output", {}))

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "Config":
        """加载配置，优先加载 local 覆盖"""
        config_path = path or LOCAL_CONFIG_PATH
        if not config_path.exists():
            config_path = DEFAULT_CONFIG_PATH

        if not config_path.exists():
            raise FileNotFoundError(
                f"配置文件未找到: {config_path}. "
                f"请从 config/settings.yaml 复制为 config/settings.local.yaml 并填入值"
            )

        with open(config_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        return cls(raw)
