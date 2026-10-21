# group-chat-bot

QQ 群 AI 机器人：**NapCat**（登录 QQ 小号）+ **NoneBot2**（机器人逻辑），全部跑在你自己那台常开的机器上。

| 功能 | 触发方式 | 用的模型 | 限制 |
|---|---|---|---|
| 日常聊天 | `@机器人 内容` | 本地模型（Ollama 等） | 不限次数 |
| 高质量回答 | `/flash 内容`（或 `/f`） | DeepSeek V4.1 Flash | 每人每天 10 次（失败自动退回） |
| 生图 | `/画 描述`（或 `/draw`） | 本地 SD WebUI / Forge，或任意 OpenAI 兼容生图接口 | 默认不限，可配置 |
| 查额度 | `/额度` | — | — |
| 清空上下文 | `/重置` | — | — |

- 次数按北京时间每天 0 点重置，存在 `data/quota.db`，重启不丢。
- `SUPERUSERS` 里的 QQ 号（你的大号）不受次数限制。
- 每个人在每个群里有独立的对话上下文（默认保留 6 轮）。
- 本地显卡同一时间只跑一个任务（聊天和生图排队），避免爆显存。

## 架构

```
QQ 小号 ── NapCat (Docker) ──反向 WebSocket (OneBot 11)──▶ NoneBot2 bot (Docker)
                                                              ├─▶ Ollama（宿主机，本地聊天模型）
                                                              ├─▶ SD WebUI / Forge（宿主机，本地生图）
                                                              └─▶ DeepSeek API（Flash，限次）
```

## 部署

前提：机器上已装好 Docker；Ollama 和（可选的）SD WebUI 直接装在宿主机上。

**1. 准备本地模型**

```bash
ollama pull qwen3:8b        # 按显存选：8G 显存 qwen3:8b，16G+ 可以试 qwen3:14b
```

Ollama 默认只监听 127.0.0.1，容器访问不到，需要设置 `OLLAMA_HOST=0.0.0.0` 后重启 Ollama。
SD WebUI / Forge 启动参数要加 `--api --listen`。

**2. 配置**

```bash
cp .env.example .env
```

至少修改：`ONEBOT_ACCESS_TOKEN`、`SUPERUSERS`、`FLASH_API_KEY`（在 platform.deepseek.com 申请）、`LOCAL_MODEL`。

> DeepSeek V4.1 Flash 的模型名目前报道不一（`deepseek-flash` / `deepseek-v4.1-flash`），以 DeepSeek 官方文档为准填 `FLASH_MODEL`。

**3. 启动**

```bash
docker compose up -d --build
```

**4. 登录小号并连接机器人**

1. 浏览器打开 `http://<机器IP>:6099/webui`（compose 里默认只绑定本机，远程访问可用 SSH 端口转发）。登录 token 见 `docker compose logs napcat`。
2. 扫码登录 QQ 小号。
3. 在「网络配置」中新建 **WebSocket 客户端**（反向 WS）：
   - URL：`ws://bot:8080/onebot/v11/ws`
   - Token：与 `.env` 里的 `ONEBOT_ACCESS_TOKEN` 相同
   - 消息格式：`array`
4. `docker compose logs -f bot` 看到 `OneBot V11 | Bot xxx connected` 即成功。

## 关于小号风控（务必看）

这个号之前接过机器人，已经有被标记的可能，以下能降低被冻结的概率：

- 一直在**同一台机器、同一网络**上登录，不要频繁换 IP 或换设备；compose 里固定了容器 hostname / MAC，`napcat/qq` 目录要保留（里面是登录数据）。
- 不要随意升级 NapCat 镜像里的 QQ 版本，升级前先看 NapCat release 说明。
- 机器人只在被 @ 或使用命令时回复，不主动刷屏；不要拉进太多群或很大的群。
- 不要用它加好友、群发、发广告链接。
- 即使做到以上几点，个人号机器人仍可能被冻结——这是这条技术路线固有的风险。

## 开发

```bash
pip install -e ".[dev]"
pytest
```

配置项都在 `src/plugins/aichat/config.py`，对应 `.env` 中的同名大写变量。
