import base64
import json

import httpx
import pytest

from src.plugins.aichat import llm


def patch_client(monkeypatch, handler):
    real = httpx.AsyncClient

    def factory(*args, **kwargs):
        return real(*args, transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(llm.httpx, "AsyncClient", factory)


async def test_chat_strips_think(monkeypatch):
    def handler(request):
        assert request.url.path == "/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer k"
        assert json.loads(request.content)["model"] == "m"
        return httpx.Response(200, json={"choices": [{"message": {"content": "<think>x</think>\n你好"}}]})

    patch_client(monkeypatch, handler)
    out = await llm.chat_completion("http://h/v1/", "k", "m", [{"role": "user", "content": "hi"}], 5)
    assert out == "你好"


async def test_chat_error(monkeypatch):
    patch_client(monkeypatch, lambda r: httpx.Response(401, text="bad key"))
    with pytest.raises(llm.ApiError):
        await llm.chat_completion("http://h", "k", "m", [], 5)


async def test_image_sdwebui(monkeypatch):
    def handler(request):
        body = json.loads(request.content)
        assert request.url.path == "/sdapi/v1/txt2img"
        assert (body["width"], body["height"]) == (512, 768)
        return httpx.Response(200, json={"images": [base64.b64encode(b"PNG").decode()]})

    patch_client(monkeypatch, handler)
    assert await llm.generate_image("sdwebui", "http://h", "", "", "cat", "512x768", 20, 5) == (b"PNG", "image.png")


async def test_image_openai_url(monkeypatch):
    def handler(request):
        if request.url.path == "/v1/images/generations":
            return httpx.Response(200, json={"data": [{"url": "http://cdn/img.png"}]})
        return httpx.Response(200, content=b"IMG")

    patch_client(monkeypatch, handler)
    assert await llm.generate_image("openai", "http://h/v1", "k", "m", "cat", "1024x1024", 0, 5) == (b"IMG", "image.png")


WORKFLOW = {
    "3": {"class_type": "KSampler", "inputs": {"seed": 1, "steps": 20}},
    "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "masterpiece, {{prompt}}"}},
    "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "bot"}},
}


def test_fill_workflow():
    wf = llm.fill_workflow(WORKFLOW, "一只猫")
    assert wf["6"]["inputs"]["text"] == "masterpiece, 一只猫"
    assert WORKFLOW["6"]["inputs"]["text"] == "masterpiece, {{prompt}}"  # 原工作流不被修改
    with pytest.raises(llm.ApiError):
        llm.fill_workflow({"1": {"inputs": {"text": "no placeholder"}}}, "x")


async def test_comfyui(monkeypatch):
    polls = []

    def handler(request):
        path = request.url.path
        if path == "/prompt":
            body = json.loads(request.content)
            assert body["prompt"]["6"]["inputs"]["text"] == "masterpiece, cat"
            return httpx.Response(200, json={"prompt_id": "p1"})
        if path == "/history/p1":
            polls.append(1)
            if len(polls) < 2:
                return httpx.Response(200, json={})
            return httpx.Response(200, json={"p1": {
                "status": {"status_str": "success", "completed": True},
                "outputs": {
                    "8": {"images": [{"filename": "tmp.png", "subfolder": "", "type": "temp"}]},
                    "9": {"images": [{"filename": "bot_001.png", "subfolder": "s", "type": "output"}]},
                },
            }})
        if path == "/view":
            assert request.url.params["filename"] == "bot_001.png"
            assert request.url.params["subfolder"] == "s"
            return httpx.Response(200, content=b"PNG")
        return httpx.Response(404)

    patch_client(monkeypatch, handler)
    out = await llm.comfyui_generate("http://h:8188/", WORKFLOW, "cat", 5, poll_interval=0)
    assert out == (b"PNG", "bot_001.png")


async def test_comfyui_error(monkeypatch):
    def handler(request):
        if request.url.path == "/prompt":
            return httpx.Response(200, json={"prompt_id": "p1"})
        return httpx.Response(200, json={"p1": {"status": {"status_str": "error"}, "outputs": {}}})

    patch_client(monkeypatch, handler)
    with pytest.raises(llm.ApiError):
        await llm.comfyui_generate("http://h", WORKFLOW, "cat", 5, poll_interval=0)
