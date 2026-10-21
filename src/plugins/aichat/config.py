from pydantic import BaseModel


class Config(BaseModel):
    # 本地模型（默认使用，不限次数）。Ollama / LM Studio / vLLM 都提供 OpenAI 兼容接口
    local_base_url: str = "http://127.0.0.1:11434/v1"
    local_api_key: str = "ollama"
    local_model: str = "qwen3:8b"

    # 云端模型（限次数），默认 DeepSeek V4.1 Flash
    flash_base_url: str = "https://api.deepseek.com"
    flash_api_key: str = ""
    flash_model: str = "deepseek-flash"
    flash_daily_limit: int = 10

    # 生图：backend 为 "openai"（/images/generations）或 "sdwebui"（A1111 / Forge 的 /sdapi/v1/txt2img）
    image_backend: str = "sdwebui"
    image_base_url: str = "http://127.0.0.1:7860"
    image_api_key: str = ""
    image_model: str = ""
    image_size: str = "1024x1024"
    image_steps: int = 25
    # 0 表示不限次数
    image_daily_limit: int = 0

    system_prompt: str = "你是一个QQ群里的AI助手，回答简洁友好，使用中文，不要使用Markdown格式。"
    # 每个人在每个群里保留的对话轮数
    history_turns: int = 6
    max_reply_chars: int = 1500
    request_timeout: float = 120.0
    quota_db_path: str = "data/quota.db"
    quota_timezone: str = "Asia/Shanghai"
