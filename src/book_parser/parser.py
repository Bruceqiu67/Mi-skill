"""书解析模块：PDF/EPUB → 结构化文本 → 方法论骨架"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from src.utils.config import BookConfig
from src.utils.llm_client import MultiLLMClient


class BookParser:
    """将书文件解析为结构化章节文本"""

    SUPPORTED_EXTENSIONS = {".pdf", ".epub"}

    def __init__(self, config: BookConfig):
        self.config = config
        self._text_cache: Optional[dict[str, str]] = None  # {chapter_title: text}

    def extract_text(self) -> dict[str, str]:
        """返回 {章节标题: 正文} 映射"""
        if self._text_cache:
            return self._text_cache

        path = self.config.resolved_path
        if not path:
            # 先检查格式（即使文件不存在）
            ext = Path(self.config.path or "").suffix.lower()
            if ext and ext not in self.SUPPORTED_EXTENSIONS:
                raise ValueError(f"不支持的文件格式: {ext}，支持: {self.SUPPORTED_EXTENSIONS}")
            raise FileNotFoundError(
                f"书文件未找到: {self.config.path}. "
                f"请将书文件放在项目目录并更新 config/settings.local.yaml"
            )

        ext = path.suffix.lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"不支持的文件格式: {ext}，支持: {self.SUPPORTED_EXTENSIONS}")

        if ext == ".pdf":
            self._text_cache = self._parse_pdf(path)
        elif ext == ".epub":
            self._text_cache = self._parse_epub(path)

        return self._text_cache

    def _parse_pdf(self, path: Path) -> dict[str, str]:
        """PDF → 按 TOC 页面号直接分段（可靠，不依赖文本匹配）"""
        import fitz  # PyMuPDF

        doc = fitz.open(path)
        chapters: dict[str, str] = {}

        # 从目录提取 (页面号, 标题) 对
        toc = doc.get_toc()
        sections: list[tuple[int, str]] = []
        if toc:
            for level, title, page in toc:
                if level <= 2:
                    # PyMuPDF 页码从 1 开始
                    sections.append((page - 1, title.strip()))

        if not sections:
            # 无目录时整本书作为一章
            full_text = "\n".join(
                doc[i].get_text().strip() for i in range(doc.page_count)
                if doc[i].get_text().strip()
            )
            doc.close()
            return {"全书": full_text}

        # 按页面号分段
        for i, (start_page, title) in enumerate(sections):
            end_page = sections[i + 1][0] if i + 1 < len(sections) else doc.page_count
            text_parts = []
            for p in range(start_page, min(end_page, doc.page_count)):
                page_text = doc[p].get_text().strip()
                if page_text:
                    text_parts.append(page_text)
            if text_parts:
                chapters[title] = "\n".join(text_parts)

        doc.close()
        return chapters

    def _parse_epub(self, path: Path) -> dict[str, str]:
        """EPUB → 按章节分页"""
        try:
            import ebooklib
            from ebooklib import epub
        except ImportError:
            raise ImportError("需要安装 ebooklib: pip install ebooklib")

        try:
            from bs4 import BeautifulSoup
        except ImportError:
            raise ImportError("需要安装 beautifulsoup4: pip install beautifulsoup4")

        book = epub.read_epub(str(path))
        chapters: dict[str, str] = {}
        current_title = "正文"

        for item in book.get_items():
            if item.get_type() != ebooklib.ITEM_DOCUMENT:
                continue

            soup = BeautifulSoup(item.get_content(), "html.parser")
            text = soup.get_text(separator="\n").strip()
            if not text:
                continue

            title_tag = soup.find(["h1", "h2", "h3", "title"])
            chapter_title = current_title
            if title_tag:
                candidate = title_tag.get_text(strip=True)
                if candidate and len(candidate) < 200:
                    chapter_title = candidate

            if chapter_title in chapters:
                chapters[chapter_title] += "\n\n" + text
            else:
                chapters[chapter_title] = text

            current_title = chapter_title

        return chapters


class MethodologyExtractor:
    """从书中提取方法论骨架"""

    SYSTEM_PROMPT = """
你是一个专业的知识蒸馏专家。你的任务是从一本书的章节内容中提取方法论骨架。

请分析以下章节内容，提取：
1. **核心概念** — 本章定义的关键术语和概念
2. **分析框架** — 她用来分析/判断的结构化方法
3. **判断规则** — 具体的决策标准（如果 X 则 Y）
4. **工具/指标** — 她使用的具体工具、指标、参数

输出格式为 JSON:
{
  "chapter_title": "...",
  "core_concepts": ["概念1: 简短定义", ...],
  "frameworks": [{"name": "框架名", "steps": ["步骤1", ...]}],
  "rules": [{"condition": "当...时", "action": "应该..."}],
  "tools": [{"name": "工具名", "usage": "如何使用", "params": "关键参数"}]
}
    """.strip()

    def __init__(self, llm: MultiLLMClient):
        self.llm = llm

    def extract(self, chapters: dict[str, str], batch_size: int = 30) -> list[dict]:
        """分批并行多模型逐章提取方法论"""

        # 过滤短章节，构造并行任务
        items = []
        for title, text in chapters.items():
            if len(text) < 200:
                continue
            items.append({
                "id": title,
                "content": f"## {title}\n\n{text[:8000]}",
            })

        if not items:
            return []

        # 为失败重试保留内容映射
        chapter_content = {item["id"]: item["content"] for item in items}

        total = len(items)
        n_models = self.llm.count
        print(f"  并行蒸馏 {total} 个章节, 每批 {batch_size} 个 "
              f"(模型: {', '.join(self.llm.provider_names)})", flush=True)

        all_results = []
        for batch_start in range(0, total, batch_size):
            batch = items[batch_start:batch_start + batch_size]
            batch_num = batch_start // batch_size + 1
            n_batches = (total + batch_size - 1) // batch_size

            print(f"\n  批次 {batch_num}/{n_batches} ({len(batch)} 章节)...", flush=True)

            batch_results = self.llm.parallel_map(
                items=batch,
                system_prompt=self.SYSTEM_PROMPT,
                temperature=0.3,
                max_workers=n_models,
                delay=0.3,
            )

            # 处理失败的任务（重试一次用不同模型）
            for pr in batch_results:
                if pr["error"]:
                    print(f"    [{pr['provider']}] {pr['id'][:30]}: 失败({pr['error'][:60]})"
                          f" 重试...", flush=True)
                    try:
                        content = chapter_content.get(pr["id"], "")
                        if content:
                            client = self.llm.get_next()
                            result = client.chat_json(
                                system=self.SYSTEM_PROMPT,
                                user=content,
                                temperature=0.3,
                            )
                            result["_chapter"] = pr["id"]
                            result["_provider"] = client.config.name + "(retry)"
                            pr["result"] = result
                            pr["error"] = None
                    except Exception as e2:
                        pr["error"] = str(e2)

            # 汇总批次结果
            for pr in batch_results:
                if pr["error"]:
                    print(f"  ╳ [{pr['provider']}] {pr['id'][:30]}: {pr['error'][:80]}", flush=True)
                    all_results.append({
                        "_chapter": pr["id"],
                        "_error": pr["error"],
                        "_provider": pr["provider"],
                        "core_concepts": [],
                        "frameworks": [],
                        "rules": [],
                        "tools": [],
                    })
                else:
                    r = pr["result"]
                    r["_chapter"] = pr["id"]
                    r["_provider"] = pr["provider"]
                    all_results.append(r)
                    concepts = len(r.get("core_concepts", []))
                    frameworks = len(r.get("frameworks", []))
                    rules = len(r.get("rules", []))
                    print(f"  ✓ [{pr['provider']}] {pr['id'][:30]}: "
                          f"{concepts}概念 {frameworks}框架 {rules}规则", flush=True)

        return all_results
