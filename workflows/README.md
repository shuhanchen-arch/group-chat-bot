# ComfyUI 工作流

这里放从 ComfyUI 导出的 **API 格式**工作流，每个文件是一个可在群里调用的工作流：

| 文件 | 群里用法 |
|---|---|
| `flux.json` | `/画 一只猫`（默认工作流，由 `IMAGE_DEFAULT_WORKFLOW` 决定） |
| `h3.json` | `/画 h3 一只猫` |

## 导出步骤

1. 在 ComfyUI 里打开一个能正常出图的工作流。
2. 把正向提示词节点的文本改成 `{{prompt}}`，也可以带固定前缀，例如 `masterpiece, best quality, {{prompt}}`。
3. 菜单 **Workflow → Export (API)**（旧版界面要先在设置里开启 Dev mode，再点 **Save (API Format)**）。
4. 把导出的 json 放进本目录，文件名就是群里用的名字。文件修改后不用重启机器人。

注意：
- 所有名为 `seed` / `noise_seed` 的输入每次都会换成随机值，同样的描述也能生成不同的图。
- 工作流里必须有保存节点（SaveImage、SaveVideo 等）。输出是 mp4/webm 视频时，机器人会以视频消息发送。
- 普通 UI 格式（Save 出来的、含 `nodes` / `links` 的 json）不能用，一定要是 API 格式。
