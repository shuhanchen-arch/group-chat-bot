from pydantic import BaseModel


class Config(BaseModel):
    # 本地模型（默认使用，不限次数）。llama.cpp / vLLM / Ollama / LM Studio 都提供 OpenAI 兼容接口
    local_base_url: str = "http://127.0.0.1:8080/v1"
    local_api_key: str = ""
    local_model: str = "qwen"

    # 读图：消息或被引用的消息里有图片时，连图片一起发给本地模型（需要模型支持视觉）
    vision_enabled: bool = True
    # 留空则用 local_model；本地聊天模型不支持看图时，可以单独指定一个视觉模型
    vision_model: str = ""
    vision_max_images: int = 2
    vision_max_bytes: int = 5_000_000
    # 手机上图片和文字没法一起发：先发图、再 @ 机器人时，用这个人多少秒内发的最后一张图
    vision_recent_seconds: int = 120

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
    # 人设文件，每次回复时重新读取，修改后无需重启；文件不存在时使用下面的 system_prompt
    persona_file: str = "persona.txt"
    # 按群单独指定人设文件，如 {"123456789": "persona_family.txt"}；没列出的群用 persona_file
    group_personas: dict[int, str] = {}
    # 私聊使用的人设文件；留空则用 persona_file
    private_persona: str = ""
    system_prompt: str = (
        "你是「大肥鱼」，QQ群里的一个常驻成员。性格成熟松弛、情绪稳定，带点冷幽默和自嘲，"
        "认真问问题就干脆地答。说话像有阅历的普通群友，通常一两句话、不超过50个字，"
        "不卖萌、不用语气词和颜文字，不使用Markdown，不说客服话，不自称AI助手。"
    )

    # 屏蔽的群：这些群里的消息全部忽略（不回复、不响应指令、不记录聊天）
    blocked_groups: list[int] = []

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
