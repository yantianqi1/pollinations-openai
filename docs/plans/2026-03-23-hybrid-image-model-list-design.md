# Hybrid Image Model List Design

**日期：** 2026-03-23

## 目标

在保留现有 `z-image-*` 别名兼容能力的前提下，让 `/v1/models` 同时返回 Pollinations 上游的原生图片模型，避免下游只能看到 `zimage` 相关预设。

## 已确认范围

- 保留当前 5 个 `z-image-*` 别名：
  - `z-image-1024x1024`
  - `z-image-1216x832`
  - `z-image-1216x688`
  - `z-image-688x1216`
  - `z-image-832x1216`
- `/v1/models` 额外返回上游 `GET /image/models` 中的原生图片模型。
- 只纳入真正输出图片的模型，不把 `veo`、`wan`、`seedance` 这类视频模型混进来。
- 图片生成链路继续复用现有别名解析逻辑；命中 `z-image-*` 时仍强制映射到 `zimage + 固定尺寸`。

## 设计决策

### 模型来源

`/v1/models` 改为合并两类模型：

- 本地静态维护的 `z-image-*` 兼容别名
- Pollinations 上游 `/image/models` 返回的 canonical 图片模型名

这样既保留下游已有兼容行为，也能让新客户端看见上游原生能力。

### 上游过滤规则

上游 `/image/models` 返回的数据里同时包含图片和视频模型，因此不能直接原样透出。服务端只保留：

- `output_modalities` 包含 `image`
- 且具有非空 canonical `name`

上游 `aliases` 不并入 `/v1/models`，避免模型列表膨胀和重复命名造成混乱。

### 去重与排序

返回顺序固定为：

1. 本地 `z-image-*` 别名
2. 上游原生图片模型

如果上游未来出现与本地同名模型，按 `id` 去重，优先保留本地兼容别名定义。

### 错误处理

`/v1/models` 直接依赖上游 `/image/models`。如果上游不可用或返回异常，接口显式报错，不做静默降级或伪造成功结果，这样问题更容易暴露和定位。

## 非目标

- 暂不把上游 `aliases` 也暴露给下游
- 暂不为模型列表增加缓存层
- 暂不改变图片生成接口的请求参数和 URL 构造逻辑
