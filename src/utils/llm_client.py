"""OpenAI-compatible LLM 客户端 - 多提供商并行"""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from openai import OpenAI

from src.utils.config import LLMProviderConfig, MultiLLMConfig


class SingleLLMClient:
    """单个 LLM 提供商客户端"""

    def __init__(self, config: LLMProviderConfig, timeout: int = 60):
        self.config = config
        self._client = OpenAI(
            base_url=config.api_base,
            api_key=config.api_key,
            timeout=timeout,
            max_retries=2,
        )

    def chat(self, system: str, user: str, temperature: float = 0.3,
             max_tokens: int = 4096) -> str:
        resp = self._client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content or ""

    def chat_json(self, system: str, user: str, temperature: float = 0.3) -> dict:
        resp = self._client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content or "{}"
        return json.loads(raw)


class MultiLLMClient:
    """多 LLM 提供商并行客户端"""

    def __init__(self, config: MultiLLMConfig):
        providers = config.configured_providers
        if not providers:
            raise ValueError("没有可用的 LLM 提供商，请检查配置")
        self.clients: list[SingleLLMClient] = [
            SingleLLMClient(p) for p in providers
        ]
        self._round_robin = 0

    @property
    def provider_names(self) -> list[str]:
        return [c.config.name for c in self.clients]

    @property
    def count(self) -> int:
        return len(self.clients)

    def get_next(self) -> SingleLLMClient:
        """轮询获取下一个客户端"""
        client = self.clients[self._round_robin % len(self.clients)]
        self._round_robin += 1
        return client

    def chat(self, system: str, user: str, temperature: float = 0.3,
             max_tokens: int = 4096) -> str:
        """轮询调用"""
        return self.get_next().chat(system, user, temperature, max_tokens)

    def chat_json(self, system: str, user: str, temperature: float = 0.3) -> dict:
        """轮询调用"""
        return self.get_next().chat_json(system, user, temperature)

    def parallel_map(self, items: list[dict], system_prompt: str,
                     temperature: float = 0.3, max_workers: int = 3,
                     delay: float = 0.3) -> list[dict]:
        """
        并行处理多个任务。
        items: [{"id": "任务ID", "content": "用户提示词"}, ...]
        返回: [{"id": ..., "result": {...dict}, "provider": "...", "error": None}, ...]
        """
        results = [None] * len(items)

        def process(idx: int, item: dict) -> tuple[int, dict]:
            client = self.clients[idx % len(self.clients)]
            try:
                result = client.chat_json(
                    system=system_prompt,
                    user=item["content"],
                    temperature=temperature,
                )
                if delay > 0:
                    time.sleep(delay)
                return idx, {"id": item["id"], "result": result,
                             "provider": client.config.name, "error": None}
            except Exception as e:
                return idx, {"id": item["id"], "result": None,
                             "provider": client.config.name, "error": str(e)}

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [pool.submit(process, i, item) for i, item in enumerate(items)]
            for future in as_completed(futures):
                idx, result = future.result()
                results[idx] = result

        return results
