# Chat Completions Streaming Compat Design

**日期：** 2026-03-23

## 目标

让图片模型在 `POST /v1/chat/completions` 且 `stream=true` 时返回 OpenAI 风格 SSE 流，兼容默认使用流式的下游客户端。

## 设计

### 流式策略

- 不做伪造成功，也不静默忽略 `stream=true`
- 仍然先完成真实生图，再输出 SSE 事件
- 这样不会伪装成 token 级流式，但能兼容要求 `text/event-stream` 的客户端

### 事件格式

- 返回 `text/event-stream`
- 输出 3 段：
  - 第一段：`delta.role=assistant`
  - 第二段：`delta.content=![image](...)`
  - 第三段：`finish_reason=stop`
- 结尾显式输出 `data: [DONE]`

### 错误处理

- 生图阶段仍复用现有错误处理
- 如果上游拒绝请求，仍返回对应 4xx/5xx，而不是开始半截流

### 非目标

- 不实现真正逐 token 生成
- 不实现图片生成中的中间进度流
