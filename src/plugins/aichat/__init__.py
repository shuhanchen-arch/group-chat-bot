import asyncio
from collections import defaultdict, deque

from nonebot import get_driver, get_plugin_config, logger, on_command, on_message
from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent,
    Message,
    MessageEvent,
    MessageSegment,
)
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata
from nonebot.rule import to_me

from .config import Config
from .llm import chat_completion, generate_image
from .quota import QuotaStore

HELP = (
    "用法：\n"
    "@我 + 内容：用本地模型聊天（不限次数）\n"
    "/flash 内容：用 DeepSeek V4.1 Flash 回答（每人每天限次）\n"
    "/画 描述：生成图片\n"
    "/额度：查看今天剩余次数\n"
    "/重置：清空你和我的对话记录"
)

__plugin_meta__ = PluginMetadata(
    name="AI 聊天",
    description="本地模型聊天 + DeepSeek Flash 限额 + 生图",
    usage=HELP,
    config=Config,
)

cfg = get_plugin_config(Config)
quota = QuotaStore(cfg.quota_db_path, cfg.quota_timezone)
superusers = get_driver().config.superusers

# 本地显卡同一时间只跑一个任务，避免爆显存
local_gpu = asyncio.Semaphore(1)
histories: dict[str, deque] = defaultdict(lambda: deque(maxlen=cfg.history_turns * 2))

KIND_FLASH = "flash"
KIND_IMAGE = "image"


def session_key(event: MessageEvent) -> str:
    group = event.group_id if isinstance(event, GroupMessageEvent) else "private"
    return f"{group}:{event.user_id}"


def is_superuser(event: MessageEvent) -> bool:
    return str(event.user_id) in superusers


def clip(text: str) -> str:
    if len(text) > cfg.max_reply_chars:
        return text[: cfg.max_reply_chars] + "…（太长已截断）"
    return text or "（模型没有返回内容）"


async def reply(matcher: Matcher, event: MessageEvent, content) -> None:
    await matcher.finish(MessageSegment.reply(event.message_id) + content)


async def ask(event: MessageEvent, text: str, use_flash: bool) -> str:
    key = session_key(event)
    history = histories[key]
    messages = [
        {"role": "system", "content": cfg.system_prompt},
        *history,
        {"role": "user", "content": text},
    ]
    if use_flash:
        answer = await chat_completion(
            cfg.flash_base_url, cfg.flash_api_key, cfg.flash_model, messages, cfg.request_timeout
        )
    else:
        async with local_gpu:
            answer = await chat_completion(
                cfg.local_base_url, cfg.local_api_key, cfg.local_model, messages, cfg.request_timeout
            )
    history.append({"role": "user", "content": text})
    history.append({"role": "assistant", "content": answer})
    return answer


flash_cmd = on_command("flash", aliases={"f"}, priority=5, block=True)
draw_cmd = on_command("画", aliases={"draw"}, priority=5, block=True)
quota_cmd = on_command("额度", priority=5, block=True)
reset_cmd = on_command("重置", priority=5, block=True)
chat = on_message(rule=to_me(), priority=10, block=True)


@flash_cmd.handle()
async def _(matcher: Matcher, event: MessageEvent, arg: Message = CommandArg()):
    text = arg.extract_plain_text().strip()
    if not text:
        await reply(matcher, event, "用法：/flash 你的问题")
    if not cfg.flash_api_key:
        await reply(matcher, event, "管理员还没有配置 FLASH_API_KEY")
    user = str(event.user_id)
    limit = 0 if is_superuser(event) else cfg.flash_daily_limit
    if not quota.try_consume(user, KIND_FLASH, limit):
        await reply(
            matcher, event, f"你今天的 {cfg.flash_daily_limit} 次 Flash 已用完，明天再来，或直接 @我 用本地模型"
        )
    try:
        answer = await ask(event, text, use_flash=True)
    except Exception as e:
        quota.refund(user, KIND_FLASH)
        logger.exception("flash 调用失败")
        await reply(matcher, event, f"Flash 调用失败（已退回次数）：{type(e).__name__}")
    left = "" if limit <= 0 else f"\n（今日剩余 {limit - quota.used(user, KIND_FLASH)} 次）"
    await reply(matcher, event, clip(answer) + left)


@draw_cmd.handle()
async def _(matcher: Matcher, event: MessageEvent, arg: Message = CommandArg()):
    prompt = arg.extract_plain_text().strip()
    if not prompt:
        await reply(matcher, event, "用法：/画 一只在月球上喝奶茶的猫")
    user = str(event.user_id)
    limit = 0 if is_superuser(event) else cfg.image_daily_limit
    if not quota.try_consume(user, KIND_IMAGE, limit):
        await reply(matcher, event, f"你今天的 {cfg.image_daily_limit} 次生图已用完")
    await matcher.send("收到，正在画…")
    try:
        async with local_gpu:
            image = await generate_image(
                cfg.image_backend,
                cfg.image_base_url,
                cfg.image_api_key,
                cfg.image_model,
                prompt,
                cfg.image_size,
                cfg.image_steps,
                cfg.request_timeout,
            )
    except Exception as e:
        quota.refund(user, KIND_IMAGE)
        logger.exception("生图失败")
        await reply(matcher, event, f"生图失败：{type(e).__name__}")
    await reply(matcher, event, MessageSegment.image(image))


@quota_cmd.handle()
async def _(matcher: Matcher, event: MessageEvent):
    if is_superuser(event):
        await reply(matcher, event, "你是管理员，不限次数")
    user = str(event.user_id)
    lines = [f"Flash：今日剩余 {max(cfg.flash_daily_limit - quota.used(user, KIND_FLASH), 0)}/{cfg.flash_daily_limit} 次"]
    if cfg.image_daily_limit > 0:
        used = quota.used(user, KIND_IMAGE)
        lines.append(f"生图：今日剩余 {max(cfg.image_daily_limit - used, 0)}/{cfg.image_daily_limit} 次")
    lines.append("本地模型聊天：不限次数")
    await reply(matcher, event, "\n".join(lines))


@reset_cmd.handle()
async def _(matcher: Matcher, event: MessageEvent):
    histories.pop(session_key(event), None)
    await reply(matcher, event, "对话记录已清空")


@chat.handle()
async def _(matcher: Matcher, event: MessageEvent):
    text = event.get_plaintext().strip()
    if not text:
        await reply(matcher, event, HELP)
    try:
        answer = await ask(event, text, use_flash=False)
    except Exception as e:
        logger.exception("本地模型调用失败")
        await reply(matcher, event, f"本地模型暂时不可用：{type(e).__name__}")
    await reply(matcher, event, clip(answer))
