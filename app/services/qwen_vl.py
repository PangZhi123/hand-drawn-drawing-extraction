import base64
import json
import logging
from io import BytesIO
from typing import Any

from json_repair import repair_json
from openai import BadRequestError, OpenAI
from PIL import Image

logger = logging.getLogger(__name__)
EXPECTED_KEYS = {
    "fixed_key_data",
    "process_analysis",
    "additional_observations",
    "uncertain_items",
}
TOP_LEVEL_ALIASES = {
    "固定关键数据": "fixed_key_data",
    "过程分析": "process_analysis",
    "补充观察": "additional_observations",
    "不确定项": "uncertain_items",
}


class QwenVLAnalyzer:
    def __init__(
        self, base_url: str, api_key: str, model: str, timeout: int, max_tokens: int, prompt: str
    ):
        self.client = OpenAI(base_url=base_url, api_key=api_key, timeout=timeout)
        self.model = model
        self.max_tokens = max_tokens
        self.prompt = prompt

    def analyze(
        self,
        image: Image.Image,
        source_file: str,
        page_number: int,
        extraction_requirements: str | None,
    ) -> dict:
        buffer = BytesIO()
        image.convert("RGB").save(buffer, "JPEG", quality=92)
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        requirement = extraction_requirements.strip() if extraction_requirements else "无补充要求"
        user_prompt = (
            f"{self.prompt}\n\n本次补充提取要求：{requirement}\n"
            "补充要求只能调整提取重点，不得编造图中不存在的信息。"
        )
        messages = [
            {"role": "system", "content": "只输出标准JSON；证据不足时留空并列入不确定信息。"},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{encoded}"},
                    },
                    {"type": "text", "text": user_prompt},
                ],
            },
        ]
        request = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "max_tokens": self.max_tokens,
        }
        try:
            response = self.client.chat.completions.create(
                **request, response_format={"type": "json_object"}
            )
        except BadRequestError as exc:
            # 兼容不支持 response_format 的较旧 llama-server。
            if "response_format" not in str(exc).lower() and "json" not in str(exc).lower():
                raise
            response = self.client.chat.completions.create(**request)

        message = response.choices[0].message
        data, raw = _parse_message(message)
        if not EXPECTED_KEYS.intersection(data):
            # Do not silently discard a useful natural-language or differently shaped response.
            # It remains reviewable in the workbook while the raw shape is visible in logs.
            logger.warning("Model returned an unmapped response: %s", raw[:4000])
            observation: Any = data if data else raw.strip()
            data = {"additional_observations": [observation]} if observation else {}
        data["_source"] = {"source_file": source_file, "page_number": page_number}
        data["_model"] = {"name": self.model}
        return data


def _json_object(text: str) -> str:
    start, end = text.find("{"), text.rfind("}")
    return text[start : end + 1] if start >= 0 and end >= start else "{}"


def _parse_message(message: Any) -> tuple[dict, str]:
    """Parse OpenAI and Ollama message variants, including thinking responses."""
    values: list[str] = []
    dumped = message.model_dump() if hasattr(message, "model_dump") else {}
    extra = getattr(message, "model_extra", None) or {}
    for name in ("content", "reasoning_content", "reasoning"):
        value = getattr(message, name, None) or dumped.get(name) or extra.get(name)
        if isinstance(value, str) and value.strip() and value not in values:
            values.append(value)

    best: tuple[int, dict, str] | None = None
    for raw in values:
        if "{" not in raw:
            continue
        try:
            parsed = json.loads(repair_json(_json_object(raw)))
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if not isinstance(parsed, dict):
            continue
        parsed = _unwrap_result(parsed)
        parsed = {TOP_LEVEL_ALIASES.get(key, key): value for key, value in parsed.items()}
        score = len(EXPECTED_KEYS.intersection(parsed))
        if best is None or score > best[0]:
            best = (score, parsed, raw)
    if best:
        return best[1], best[2]
    return {}, next((value for value in values if value.strip()), "")


def _unwrap_result(data: dict) -> dict:
    """Accept common wrappers such as {\"data\": {expected schema...}}."""
    if EXPECTED_KEYS.intersection(data) or set(data).intersection(TOP_LEVEL_ALIASES):
        return data
    for key in ("data", "result", "output", "analysis"):
        child = data.get(key)
        if isinstance(child, dict) and (
            EXPECTED_KEYS.intersection(child) or set(child).intersection(TOP_LEVEL_ALIASES)
        ):
            return child
    return data
