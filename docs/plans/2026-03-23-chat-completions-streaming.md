# Chat Completions Streaming Compat Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add OpenAI-style SSE streaming compatibility for image-model chat completions so downstream clients that default to `stream=true` can consume the relay.

**Architecture:** Keep image generation synchronous and real, but wrap the final result in a short SSE sequence of `chat.completion.chunk` events plus `[DONE]`. Reuse the existing prompt extraction and shared image relay service so non-stream and stream stay consistent.

**Tech Stack:** FastAPI, StreamingResponse, Pydantic, unittest, httpx

---

### Task 1: Lock streaming response behavior in tests

**Files:**
- Modify: `tests/test_pollinations_integration.py`

**Step 1: Write the failing test**

Add a test that asserts `stream=true` returns:
- `200`
- `content-type` containing `text/event-stream`
- at least one `chat.completion.chunk`
- a final `data: [DONE]`

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_pollinations_integration.ChatCompletionCompatTest.test_chat_completions_streams_sse_chunks -v`
Expected: FAIL because the route currently returns `400`.

**Step 3: Write minimal implementation**

Add a chunk payload builder and SSE generator in the chat router.

**Step 4: Run test to verify it passes**

Run the same command and confirm PASS.

### Task 2: Verify full regression

**Files:**
- Modify: `app/routers/chat.py`
- Test: `tests/test_pollinations_integration.py`

**Step 1: Run the full targeted suite**

Run: `python3 -m unittest tests.test_pollinations_integration -v`

**Step 2: Confirm both stream and non-stream work**

Expected:
- non-stream chat returns `chat.completion`
- stream chat returns SSE chunks
- image generation tests still pass
