import asyncio
import base64
import copy
import random
import re
import uuid

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
) -> tuple[bytes, str]:
    """返回 (文件字节, 文件名)。"""
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
            return base64.b64decode(resp.json()["images"][0]), "image.png"

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
                return base64.b64decode(item["b64_json"]), "image.png"
            img = await client.get(item["url"])
            img.raise_for_status()
            return img.content, "image.png"

    raise ApiError(f"未知的生图后端: {backend}")


PROMPT_PLACEHOLDER = "{{prompt}}"
SEED_KEYS = ("seed", "noise_seed")
# ComfyUI 输出节点里可能放文件的字段：图片节点是 images，视频节点常见 gifs / videos / video
OUTPUT_KEYS = ("images", "gifs", "videos", "video")


def fill_workflow(workflow: dict, prompt: str) -> dict:
    """把 API 格式工作流里的 {{prompt}} 换成用户描述，并给所有种子换随机值。"""
    wf = copy.deepcopy(workflow)
    replaced = False
    for node in wf.values():
        inputs = node.get("inputs", {})
        for key, value in inputs.items():
            if isinstance(value, str) and PROMPT_PLACEHOLDER in value:
                inputs[key] = value.replace(PROMPT_PLACEHOLDER, prompt)
                replaced = True
            elif key in SEED_KEYS and isinstance(value, int):
                inputs[key] = random.randint(0, 2**48)
    if not replaced:
        raise ApiError(f"工作流里没有找到 {PROMPT_PLACEHOLDER} 占位符")
    return wf


async def comfyui_generate(
    base_url: str, workflow: dict, prompt: str, timeout: float, poll_interval: float = 1.0
) -> tuple[bytes, str]:
    """提交工作流到 ComfyUI，等待完成后下载第一个输出文件。"""
    base_url = base_url.rstrip("/")
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{base_url}/prompt",
            json={"prompt": fill_workflow(workflow, prompt), "client_id": uuid.uuid4().hex},
        )
        if resp.status_code != 200:
            raise ApiError(f"HTTP {resp.status_code}: {resp.text[:200]}")
        prompt_id = resp.json()["prompt_id"]

        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while True:
            history = (await client.get(f"{base_url}/history/{prompt_id}")).json()
            entry = history.get(prompt_id)
            if entry:
                status = entry.get("status", {})
                if status.get("status_str") == "error":
                    raise ApiError("ComfyUI 执行出错，请看 ComfyUI 控制台")
                if status.get("completed", True):
                    break
            if loop.time() > deadline:
                raise ApiError("ComfyUI 生成超时")
            await asyncio.sleep(poll_interval)

        for output in entry.get("outputs", {}).values():
            for key in OUTPUT_KEYS:
                for file in output.get(key) or []:
                    if not isinstance(file, dict) or "filename" not in file:
                        continue
                    if file.get("type", "output") != "output":
                        continue
                    view = await client.get(
                        f"{base_url}/view",
                        params={
                            "filename": file["filename"],
                            "subfolder": file.get("subfolder", ""),
                            "type": "output",
                        },
                    )
                    view.raise_for_status()
                    return view.content, file["filename"]
    raise ApiError("工作流没有输出文件（需要 SaveImage / SaveVideo 之类的保存节点）")
