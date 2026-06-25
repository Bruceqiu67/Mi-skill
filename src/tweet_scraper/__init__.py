"""推特爬虫模块：Playwright 驱动的 X/Twitter 爬取"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Optional

from src.utils.config import TwitterConfig


class TweetScraper:
    """使用 Playwright 爬取 Twitter 用户的推文"""

    def __init__(self, config: TwitterConfig):
        self.config = config
        self._tweets: list[dict] = []

    def scrape(self, output_path: Optional[Path] = None) -> list[dict]:
        """爬取推文并返回"""
        username = self.config.username
        if not username:
            raise ValueError("Twitter 用户名未配置，请在 settings.local.yaml 中设置 twitter.username")

        from playwright.sync_api import sync_playwright

        max_tweets = self.config.max_tweets
        pause_ms = self.config.scroll_pause_ms

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.config.headless)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 1024},
            )
            page = context.new_page()

            # 访问用户 profile
            url = f"https://x.com/{username}"
            print(f"🌐 正在打开: {url}")
            page.goto(url, wait_until="networkidle", timeout=30000)
            time.sleep(3)

            # 滚动采集
            tweets = []
            seen_ids: set[str] = set()
            no_new_count = 0
            max_no_new = 5  # 连续 5 次无新推文则停止

            for scroll_round in range(100):  # 最大 100 轮
                if len(tweets) >= max_tweets:
                    print(f"✅ 已达目标数量: {max_tweets}")
                    break

                # 获取当前页面的推文
                new_tweets = self._extract_tweets(page, seen_ids)
                for t in new_tweets:
                    if len(tweets) < max_tweets:
                        tweets.append(t)

                print(f"📄 第 {scroll_round + 1} 轮: 已采集 {len(tweets)} 条")

                if not new_tweets:
                    no_new_count += 1
                    if no_new_count >= max_no_new:
                        print("⏹️  连续无新推文，停止采集")
                        break
                else:
                    no_new_count = 0

                # 向下滚动
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(pause_ms / 1000)

            browser.close()

        self._tweets = tweets

        # 保存到文件
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                for t in tweets:
                    f.write(json.dumps(t, ensure_ascii=False) + "\n")
            print(f"💾 已保存 {len(tweets)} 条推文到 {output_path}")

        return tweets

    def _extract_tweets(self, page, seen_ids: set[str]) -> list[dict]:
        """从页面中提取可见推文"""
        tweets = []

        try:
            # 等待推文容器加载
            page.wait_for_selector('[data-testid="tweet"]', timeout=5000)
        except Exception:
            return []

        elements = page.query_selector_all('[data-testid="tweet"]')

        for el in elements:
            tweet_data = self._parse_tweet_element(el)
            if tweet_data and tweet_data["id"] not in seen_ids:
                seen_ids.add(tweet_data["id"])
                tweets.append(tweet_data)

        return tweets

    def _parse_tweet_element(self, el) -> Optional[dict]:
        """解析单个推文元素"""
        try:
            # 推文文本
            text_el = el.query_selector('[data-testid="tweetText"]')
            text = text_el.inner_text() if text_el else ""

            if not text:
                return None

            # 推文 ID（用时间戳 + 文本 hash 生成稳定 ID）
            tweet_id = str(hash(text + str(time.time_ns())))
            # 也尝试从链接获取真实 ID
            link = el.query_selector("a[href*='/status/']")
            if link:
                href = link.get_attribute("href") or ""
                match = re.search(r"/status/(\d+)", href)
                if match:
                    tweet_id = match.group(1)

            # 时间
            time_el = el.query_selector("time")
            timestamp = time_el.get_attribute("datetime") if time_el else ""

            return {
                "id": tweet_id,
                "text": text.strip(),
                "timestamp": timestamp,
                "url": f"https://x.com/{self.config.username}/status/{tweet_id}",
            }

        except Exception:
            return None

    @staticmethod
    def load_from_file(path: Path) -> list[dict]:
        """从已保存的 JSONL 文件加载推文"""
        tweets = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    tweets.append(json.loads(line))
        return tweets
