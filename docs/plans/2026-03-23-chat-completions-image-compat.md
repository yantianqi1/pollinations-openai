# Chat Completions Image Compat Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a minimal OpenAI-compatible `POST /v1/chat/completions` endpoint for image models so `newapi` can call this relay without changing its own routing.

**Architecture:** Add a dedicated chat schema module plus a chat router that extracts a prompt from `messages`, reuses shared relay image generation logic, and returns an OpenAI-style chat completion containing the generated image URL in Markdown form.

**Tech Stack:** FastAPI, Pydantic, unittest, httpx

---

### Task 1: Lock chat compatibility behavior in tests

**Files:**
- Modify: `tests/test_pollinations_integration.py`

**Step 1: Write the failing test**

Add tests that assert:
- `POST /v1/chat/completions` accepts `z-image-*` with string `messages[].content`
- the route returns `200` with `object=chat.completion`
- the assistant content contains the cached image URL
- `stream=true` returns `400`

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_pollinations_integration.ChatCompletionCompatTest -v`
Expected: FAIL because the route does not exist yet.

**Step 3: Write minimal implementation**

Add chat schemas, route, prompt extraction, and shared image generation reuse.

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_pollinations_integration.ChatCompletionCompatTest -v`
Expected: PASS

### Task 2: Reuse image generation flow across routes

**Files:**
- Create: `app/services/relay_image.py`
- Modify: `app/routers/images.py`
- Modify: `app/routers/chat.py`

**Step 1: Write the failing test**

Use the chat compatibility test from Task 1 plus existing image generation tests.

**Step 2: Run tests to verify current failure**

Run: `python3 -m unittest tests.test_pollinations_integration -v`

**Step 3: Write minimal implementation**

Move alias resolution, Pollinations fetch, cache store, and relay URL assembly into a shared service used by both image and chat routes.

**Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_pollinations_integration -v`
Expected: PASS
