from pydantic import BaseModel


class Config(BaseModel):
    # 本地模型（默认使用，不限次数）。llama.cpp / vLLM / Ollama / LM Studio 都提供 OpenAI 兼容接口
    local_base_url: str = "http://127.0.0.1:8080/v1"
    local_api_key: str = ""
    local_model: str = "qwen"

    # 云端模型（限次数），默认 DeepSeek V4.1 Flash
    flash_base_url: str = "https://api.deepseek.com"
    flash_api_key: str = ""
    flash_model: str = "deepseek-flash"
    flash_daily_limit: int = 10

    # 生图 backend：
    #   "comfyui"：使用 comfyui_workflow_dir 里导出的 API 格式工作流
    #   "openai"：OpenAI 兼容的 /images/generations
    #   "sdwebui"：A1111 / Forge 的 /sdapi/v1/txt2img
    image_backend: str = "comfyui"
    image_base_url: str = "http://127.0.0.1:8188"
    comfyui_workflow_dir: str = "workflows"
    # /画 不指定工作流时使用的工作流名（文件名去掉 .json）
    image_default_workflow: str = "flux"
    image_timeout: float = 600.0
    image_api_key: str = ""
    image_model: str = ""
    image_size: str = "1024x1024"
    image_steps: int = 25
    # 0 表示不限次数；image_limits 可按工作流单独设置，如 {"h3": 3}
    image_daily_limit: int = 0
    image_limits: dict[str, int] = {}

    system_prompt: str = "你是一个QQ群里的AI助手，回答简洁友好，使用中文，不要使用Markdown格式。"
    # 每个人在每个群里保留的对话轮数
    history_turns: int = 6
    max_reply_chars: int = 1500
    request_timeout: float = 120.0
    quota_db_path: str = "data/quota.db"
    quota_timezone: str = "Asia/Shanghai"
