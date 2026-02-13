from __future__ import annotations

import json
from dataclasses import dataclass

import httpx

from app.core.config import Settings


@dataclass
class AiExtractionResult:
    summary: str
    level: str
    hazard_type: str
    confidence: float


class AiExtractor:
    def __init__(self, settings: Settings):
        self.settings = settings

    def extract_bulletin(self, source_url: str, title: str, text: str) -> AiExtractionResult | None:
        if self.settings.ai_provider.lower() != "openai":
            return None
        if not self.settings.openai_api_key:
            return None

        prompt = (
            "你是气象公告信息抽取器。请从输入文本中提取并返回 JSON："
            "summary(<=60字), level(红色/橙色/黄色/蓝色/未知), hazard_type, confidence(0-1)。"
            "如果信息不足，给出保守结果。"
        )

        payload = {
            "model": self.settings.openai_model,
            "messages": [
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": f"source_url={source_url}\ntitle={title}\ntext={text[:3000]}",
                },
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }

        headers = {
            "Authorization": f"Bearer {self.settings.openai_api_key}",
            "Content-Type": "application/json",
        }

        with httpx.Client(timeout=self.settings.http_timeout_seconds) as client:
            response = client.post(
                f"{self.settings.openai_api_base.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            body = response.json()

        content = body.get("choices", [{}])[0].get("message", {}).get("content", "{}")
        parsed = json.loads(content)

        summary = str(parsed.get("summary", "")).strip()
        level = str(parsed.get("level", "未知")).strip() or "未知"
        hazard_type = str(parsed.get("hazard_type", "综合风险")).strip() or "综合风险"
        confidence_raw = parsed.get("confidence", 0.0)

        try:
            confidence = float(confidence_raw)
        except (TypeError, ValueError):
            confidence = 0.0

        confidence = max(0.0, min(1.0, confidence))
        if not summary:
            return None

        return AiExtractionResult(
            summary=summary,
            level=level,
            hazard_type=hazard_type,
            confidence=confidence,
        )
