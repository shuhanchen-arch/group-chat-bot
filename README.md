# group-chat-bot

QQ 群 AI 机器人：**NapCat**（登录 QQ 小号）+ **NoneBot2**（机器人逻辑），全部跑在你自己那台常开的机器上。

| 功能 | 触发方式 | 用的模型 | 限制 |
|---|---|---|---|
| 日常聊天 | `@机器人 内容` | 本地 Qwen 27B（:8080） | 不限次数 |
| 随机插话 | 群友普通消息，按概率（默认 10%）接话；管理员消息必回 | 本地 Qwen | 每群冷却 60 秒 |
| 高质量回答 | `/flash 内容`（或 `/f`） | DeepSeek V4.1 Flash | 每人每天 10 次（失败自动退回） |
| 生图 | `/画 描述`（默认工作流，如 Flux 3） | 本地 ComfyUI（:8188） | 默认不限，可按工作流设上限 |
| 指定工作流 | `/画 h3 描述` | ComfyUI 里的其他工作流 | 同上 |
| 查额度 | `/额度` | — | — |
| 清空上下文 | `/重置` | — | — |

- 次数按北京时间每天 0 点重置，存在 `data/quota.db`，重启不丢。
- `SUPERUSERS` 里的 QQ 号（你的大号）不受次数限制。
- 每个人在每个群里有独立的对话上下文（默认保留 6 轮）。
- 机器人人设是「大肥鱼」鲸鱼娘，随机插话时会参考群里最近 20 条消息，觉得没必要说话时会保持沉默。人设写在根目录的 `persona.txt`，修改后下一条回复就生效，不用重启。
- 本地显卡同一时间只跑一个任务（Qwen 聊天和 ComfyUI 生图排队），避免爆显存。
- 工作流输出视频（mp4/webm）时会以视频消息发送。

## 架构

```
QQ 小号 ── NapCat (Docker) ──反向 WebSocket (OneBot 11)──▶ NoneBot2 bot (Docker)
                                                              ├─▶ Qwen 27B（宿主机 :8080，本地聊天）
                                                              ├─▶ ComfyUI（宿主机 :8188，Flux 3 / H3 工作流）
                                                              └─▶ DeepSeek API（Flash，限次）
```

## 部署

前提：机器上已装好 Docker；Qwen 和 ComfyUI 继续直接跑在宿主机上。

**1. 让容器能访问宿主机上的服务**

机器人跑在 Docker 里，宿主机服务如果只监听 `127.0.0.1`，容器是访问不到的：
- Qwen（:8080）：llama.cpp 启动加 `--host 0.0.0.0`；vLLM 加 `--host 0.0.0.0`。
- ComfyUI（:8188）：启动加 `--listen 0.0.0.0`。

可以在宿主机上先确认接口正常：

```bash
curl http://127.0.0.1:8080/v1/models        # 能列出模型即可，顺便看清模型名
```

**2. 导出 ComfyUI 工作流**

按 [workflows/README.md](workflows/README.md) 把 Flux 3 和 H3 的工作流导出成 API 格式，
保存为 `workflows/flux.json`、`workflows/h3.json`，并把提示词改成 `{{prompt}}`。

**3. 配置**

```bash
cp .env.example .env
```

至少修改：`ONEBOT_ACCESS_TOKEN`、`SUPERUSERS`、`FLASH_API_KEY`（在 platform.deepseek.com 申请）。如果 Qwen 用的是 vLLM / Ollama，`LOCAL_MODEL` 要填上一步查到的模型名。

机器人监听 8090 端口（8080 已被 Qwen 占用），只在 Docker 内网使用，不对外暴露。

> DeepSeek V4.1 Flash 的模型名目前报道不一（`deepseek-flash` / `deepseek-v4.1-flash`），以 DeepSeek 官方文档为准填 `FLASH_MODEL`。

**4. 启动**

```bash
docker compose up -d --build
```

**5. 登录小号并连接机器人**

1. 浏览器打开 `http://<机器IP>:6099/webui`（compose 里默认只绑定本机，远程访问可用 SSH 端口转发）。登录 token 见 `docker compose logs napcat`。
2. 扫码登录 QQ 小号。
3. 在「网络配置」中新建 **WebSocket 客户端**（反向 WS）：
   - URL：`ws://bot:8090/onebot/v11/ws`
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

## 贡献者

- [@shuhanchen-arch](https://github.com/shuhanchen-arch)
