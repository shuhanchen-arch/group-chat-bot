import time

import nonebot
import pytest
from nonebot.adapters.onebot.v11 import Adapter, Bot, GroupMessageEvent, Message
from nonebot.adapters.onebot.v11.event import Sender
from nonebot.message import handle_event

nonebot.load_plugins("src/plugins")
from src.plugins import aichat  # noqa: E402

BOT_ID = "10000"


@pytest.fixture
def env(monkeypatch, tmp_path):
    sent = []
    calls = []

    async def fake_call_api(self, bot, api, **data):
        if api == "send_msg":
            sent.append(str(data["message"]))
        return {"message_id": 1}

    async def fake_chat(base_url, api_key, model, messages, timeout):
        calls.append(model)
        return f"答:{messages[-1]['content']}"

    monkeypatch.setattr(Adapter, "_call_api", fake_call_api)
    monkeypatch.setattr(aichat, "chat_completion", fake_chat)
    monkeypatch.setattr(aichat, "quota", aichat.QuotaStore(str(tmp_path / "q.db")))
    monkeypatch.setattr(aichat.cfg, "flash_api_key", "k")
    aichat.histories.clear()
    adapter = nonebot.get_adapter(Adapter)
    return Bot(adapter, BOT_ID), sent, calls


def group_msg(text: str, user_id: int = 1, to_me: bool = False) -> GroupMessageEvent:
    return GroupMessageEvent(
        time=int(time.time()), self_id=int(BOT_ID), post_type="message",
        sub_type="normal", user_id=user_id, message_type="group", message_id=42,
        message=Message(text), original_message=Message(text), raw_message=text,
        font=0, sender=Sender(user_id=user_id), to_me=to_me, group_id=100,
    )


async def test_flash_quota(env):
    bot, sent, calls = env
    for i in range(10):
        await handle_event(bot, group_msg(f"/flash 问题{i}"))
    assert len(calls) == 10 and set(calls) == {aichat.cfg.flash_model}
    assert "今日剩余 0 次" in sent[-1]
    await handle_event(bot, group_msg("/flash 再来"))
    assert len(calls) == 10
    assert "已用完" in sent[-1]
    # 别人不受影响，管理员不限
    await handle_event(bot, group_msg("/flash hi", user_id=2))
    await handle_event(bot, group_msg("/f hi", user_id=999))
    assert len(calls) == 12


async def test_local_chat_only_when_mentioned(env):
    bot, sent, calls = env
    await handle_event(bot, group_msg("随便聊聊"))
    assert calls == []
    await handle_event(bot, group_msg("你好", to_me=True))
    assert calls == [aichat.cfg.local_model]
    assert "答:你好" in sent[-1]
    # 带上下文
    await handle_event(bot, group_msg("继续", to_me=True))
    assert len(aichat.histories["100:1"]) == 4


async def test_flash_failure_refunds(env, monkeypatch):
    bot, sent, _ = env

    async def boom(*a, **k):
        raise RuntimeError("down")

    monkeypatch.setattr(aichat, "chat_completion", boom)
    await handle_event(bot, group_msg("/flash hi"))
    assert "已退回" in sent[-1]
    assert aichat.quota.used("1", "flash") == 0


async def test_draw_workflows(env, monkeypatch, tmp_path):
    bot, sent, _ = env
    wf_dir = tmp_path / "workflows"
    wf_dir.mkdir()
    (wf_dir / "flux.json").write_text("{}")
    (wf_dir / "h3.json").write_text("{}")
    monkeypatch.setattr(aichat.cfg, "comfyui_workflow_dir", str(wf_dir))
    monkeypatch.setattr(aichat.cfg, "image_default_workflow", "flux")
    monkeypatch.setattr(aichat.cfg, "image_limits", {"h3": 1})
    used = []

    async def fake_comfy(base_url, workflow, prompt, timeout):
        used.append(prompt)
        return (b"VID", "out.mp4") if prompt == "跳舞的猫" else (b"PNG", "out.png")

    monkeypatch.setattr(aichat, "comfyui_generate", fake_comfy)
    await handle_event(bot, group_msg("/画 一只猫"))
    assert "flux" in sent[-2] and "CQ:image" in sent[-1]
    await handle_event(bot, group_msg("/画 h3 跳舞的猫"))
    assert "h3" in sent[-2] and "CQ:video" in sent[-1]
    assert used == ["一只猫", "跳舞的猫"]
    # h3 每天 1 次
    await handle_event(bot, group_msg("/画 h3 再来"))
    assert "已用完" in sent[-1] and len(used) == 2
    # flux 不限
    await handle_event(bot, group_msg("/画 h3"))  # 只有工作流名没有描述，当作描述交给默认工作流
    assert used[-1] == "h3"
    await handle_event(bot, group_msg("/额度"))
    assert "h3：今日剩余 0/1 次" in sent[-1] and "flux：不限次数" in sent[-1]


async def test_draw_failure_refunds(env, monkeypatch, tmp_path):
    bot, sent, _ = env
    (tmp_path / "flux.json").write_text("{}")
    monkeypatch.setattr(aichat.cfg, "comfyui_workflow_dir", str(tmp_path))
    monkeypatch.setattr(aichat.cfg, "image_limits", {"flux": 2})

    async def boom(*a, **k):
        raise aichat.llm.ApiError("ComfyUI 生成超时")

    monkeypatch.setattr(aichat, "comfyui_generate", boom)
    await handle_event(bot, group_msg("/画 一只猫"))
    assert "ComfyUI 生成超时" in sent[-1]
    assert aichat.quota.used("1", "image:flux") == 0
