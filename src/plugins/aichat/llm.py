import base64
import re

import httpx

_THINK_RE = re.compile(r"<think>.*?</think>", re.S)


class ApiError(Exception):
    pass


async def chat_completion(
    base_url: str, api_key: str, model: str, messages: list[dict], timeout: float
) -> str:
    """调用 OpenAI 兼容的 /chat/completions 接口。"""
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers=headers,
            json={"model": model, "messages": messages},
        )
    if resp.status_code != 200:
        raise ApiError(f"HTTP {resp.status_code}: {resp.text[:200]}")
    content = resp.json()["choices"][0]["message"].get("content") or ""
    # 本地推理模型（如 Qwen3）会把思考过程放在 <think> 标签里
    return _THINK_RE.sub("", content).strip()


async def generate_image(
    backend: str,
    base_url: str,
    api_key: str,
    model: str,
    prompt: str,
    size: str,
    steps: int,
    timeout: float,
) -> bytes:
    """返回 PNG/JPEG 图片字节。"""
    base_url = base_url.rstrip("/")
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    async with httpx.AsyncClient(timeout=timeout) as client:
        if backend == "sdwebui":
            width, height = (int(x) for x in size.lower().split("x"))
            resp = await client.post(
                f"{base_url}/sdapi/v1/txt2img",
                headers=headers,
                json={"prompt": prompt, "steps": steps, "width": width, "height": height},
            )
            if resp.status_code != 200:
                raise ApiError(f"HTTP {resp.status_code}: {resp.text[:200]}")
            return base64.b64decode(resp.json()["images"][0])

        if backend == "openai":
            payload = {"prompt": prompt, "size": size, "n": 1}
            if model:
                payload["model"] = model
            resp = await client.post(
                f"{base_url}/images/generations", headers=headers, json=payload
            )
            if resp.status_code != 200:
                raise ApiError(f"HTTP {resp.status_code}: {resp.text[:200]}")
            item = resp.json()["data"][0]
            if item.get("b64_json"):
                return base64.b64decode(item["b64_json"])
            img = await client.get(item["url"])
            img.raise_for_status()
            return img.content

    raise ApiError(f"未知的生图后端: {backend}")
