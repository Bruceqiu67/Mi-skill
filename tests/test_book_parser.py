"""书解析模块单元测试"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.book_parser.parser import BookParser, MethodologyExtractor


class TestBookParser:
    def test_supported_extensions(self):
        assert ".pdf" in BookParser.SUPPORTED_EXTENSIONS
        assert ".epub" in BookParser.SUPPORTED_EXTENSIONS

    def test_rejects_unsupported_format(self):
        """不支持 txt 格式"""
        from src.utils.config import BookConfig

        config = BookConfig({"path": "test.txt"})
        parser = BookParser(config)
        with pytest.raises(ValueError, match="不支持的文件格式"):
            parser.extract_text()

    def test_file_not_found(self):
        from src.utils.config import BookConfig

        config = BookConfig({"path": "./nonexistent/book.pdf"})
        parser = BookParser(config)
        with pytest.raises(FileNotFoundError):
            parser.extract_text()


class TestMethodologyExtractor:
    def test_system_prompt_has_required_sections(self):
        """验证系统提示词包含所有关键指令"""
        prompt = MethodologyExtractor.SYSTEM_PROMPT
        assert "核心概念" in prompt
        assert "分析框架" in prompt
        assert "判断规则" in prompt
        assert "工具/指标" in prompt
        assert "JSON" in prompt
