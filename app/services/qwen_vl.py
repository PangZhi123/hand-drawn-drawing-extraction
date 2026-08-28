import base64
import json
from io import BytesIO

from json_repair import repair_json
from openai import BadRequestError, OpenAI
from PIL import Image


class QwenVLAnalyzer:
    def __init__(self, base_url: str, api_key: str, model: str, timeout: int,
                 max_tokens: int, prompt: str):
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
            {"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}},
                {"type": "text", "text": user_prompt},
            ]},
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
        raw = message.content or ""
        if "{" not in raw:
            reasoning = getattr(message, "reasoning_content", None) or ""
            if "{" in reasoning:
                raw = reasoning
        raw = raw or "{}"
        data = json.loads(repair_json(_json_object(raw)))
        data["_source"] = {"source_file": source_file, "page_number": page_number}
        data["_model"] = {"name": self.model}
        return data


def _json_object(text: str) -> str:
    start, end = text.find("{"), text.rfind("}")
    return text[start:end + 1] if start >= 0 and end >= start else "{}"
