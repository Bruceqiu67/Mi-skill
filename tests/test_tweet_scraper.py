"""推特爬虫模块单元测试"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from src.tweet_scraper import TweetScraper
from src.utils.config import TwitterConfig


class TestTweetScraper:
    def test_load_from_file(self):
        """测试 JSONL 文件加载"""
        tweets = [
            {"id": "1", "text": "测试推文1", "timestamp": "2024-01-01"},
            {"id": "2", "text": "测试推文2", "timestamp": "2024-01-02"},
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
            for t in tweets:
                f.write(json.dumps(t, ensure_ascii=False) + "\n")
            path = f.name

        loaded = TweetScraper.load_from_file(Path(path))
        assert len(loaded) == 2
        assert loaded[0]["id"] == "1"
        assert loaded[1]["text"] == "测试推文2"

        import os
        os.unlink(path)

    def test_empty_file(self):
        """测试空文件"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
            path = f.name

        loaded = TweetScraper.load_from_file(Path(path))
        assert loaded == []

        import os
        os.unlink(path)

    def test_raises_on_no_username(self):
        """未配置用户名时抛出错误"""
        config = TwitterConfig({"username": ""})
        scraper = TweetScraper(config)
        with pytest.raises(ValueError, match="Twitter 用户名未配置"):
            scraper.scrape()
