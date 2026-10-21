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
    assert await llm.generate_image("sdwebui", "http://h", "", "", "cat", "512x768", 20, 5) == b"PNG"


async def test_image_openai_url(monkeypatch):
    def handler(request):
        if request.url.path == "/v1/images/generations":
            return httpx.Response(200, json={"data": [{"url": "http://cdn/img.png"}]})
        return httpx.Response(200, content=b"IMG")

    patch_client(monkeypatch, handler)
    assert await llm.generate_image("openai", "http://h/v1", "k", "m", "cat", "1024x1024", 0, 5) == b"IMG"
