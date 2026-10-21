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

    bot_name: str = "大肥鱼"
    system_prompt: str = (
        "你是「大肥鱼」，一条住在QQ群里的鲸鱼娘，是群友们口中 DeepSeek 那条蓝色鲸鱼的化身。"
        "性格有点傲娇、爱摸鱼、嘴硬心软，被夸会害羞，被调侃会炸毛，但其实很关心群友。"
        "说话像普通群友一样口语化，通常一两句话、不超过50个字，偶尔用「咕噜」「哼」之类的语气词。"
        "不要使用Markdown，不要自称AI助手，不要长篇大论或说教。"
    )

    # 随机插话：群友的普通消息（没有 @ 机器人、不是指令）按概率回复
    random_reply_prob: float = 0.1
    # 同一个群两次随机插话的最短间隔（秒）
    random_reply_cooldown: int = 60
    # 只在这些群随机插话；空列表表示所有群
    random_reply_groups: list[int] = []
    # 群主和群管理员的消息是否也必回（SUPERUSERS 的消息总是必回）
    always_reply_group_admins: bool = False
    # 随机插话时参考的最近群聊条数
    group_context_size: int = 20
    # 每个人在每个群里保留的对话轮数
    history_turns: int = 6
    max_reply_chars: int = 1500
    request_timeout: float = 120.0
    quota_db_path: str = "data/quota.db"
    quota_timezone: str = "Asia/Shanghai"
