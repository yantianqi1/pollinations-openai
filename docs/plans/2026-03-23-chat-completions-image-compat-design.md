# Chat Completions Image Compat Design

**日期：** 2026-03-23

## 目标

为图片模型补一个 `POST /v1/chat/completions` 兼容入口，让 `newapi` 在按 chat 路径转发 `z-image-*` 模型时不再得到 404。

## 设计

### 路由范围

- 新增 `POST /v1/chat/completions`
- 仅兼容图片生成场景，不扩展成通用文本模型接口
- `stream=true` 显式返回 400，避免伪流式兼容

### Prompt 提取

- 从 `messages` 中提取最后一条 `role=user` 的文本内容作为 prompt
- 支持两种输入：
  - 纯字符串 `content`
  - OpenAI 风格数组内容里的 `type=text`
- 如果没有可用用户文本，返回 400

### 生图复用

- 复用现有模型别名解析、尺寸解析、上游 Pollinations 请求和本地缓存逻辑
- 保持 `/v1/images/generations` 与 chat 兼容入口的行为一致

### 返回格式

- 返回 OpenAI 风格 `chat.completion`
- `assistant.content` 使用 Markdown 图片格式：`![image](<url>)`
- 保留 `model`、`choices`、`usage` 等常见字段，尽量兼容下游 chat 客户端

### 错误处理

- 上游 4xx 错误继续透传为 4xx
- 上游 5xx 或网络错误继续返回 502
- 不增加静默 fallback
