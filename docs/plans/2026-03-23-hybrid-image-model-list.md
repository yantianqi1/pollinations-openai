# Hybrid Image Model List Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Keep existing `z-image-*` compatibility aliases while exposing upstream Pollinations image models through `/v1/models`.

**Architecture:** Keep alias resolution in the existing preset module, add a small upstream image-model reader that fetches and filters canonical image models from Pollinations, then merge both sources in the models route. Use tests to lock the merged model-list behavior and ensure image generation alias mapping stays unchanged.

**Tech Stack:** FastAPI, httpx, Pydantic, unittest

---

### Task 1: Lock merged model-list behavior in tests

**Files:**
- Modify: `tests/test_pollinations_integration.py`

**Step 1: Write the failing test**

Add a test that mocks the upstream `/image/models` payload and asserts `/v1/models` returns:
- existing `z-image-*` aliases
- upstream image models such as `flux` and `gptimage`
- no video-only models such as `veo`

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_pollinations_integration.DownstreamModelAliasTest.test_list_models_merges_aliases_with_upstream_image_models -v`
Expected: FAIL because `/v1/models` currently returns only local alias presets.

**Step 3: Write minimal implementation**

Add upstream image-model fetch and filtering logic, then update `/v1/models` to merge the two model sources by `id`.

**Step 4: Run test to verify it passes**

Run the same command and confirm PASS.

### Task 2: Keep alias-based generation behavior unchanged

**Files:**
- Modify: `tests/test_pollinations_integration.py`
- Modify: `app/services/model_presets.py`
- Modify: `app/routers/models.py`
- Create: `app/services/upstream_models.py`

**Step 1: Re-run the alias mapping tests**

Run: `python3 -m unittest tests.test_pollinations_integration.DownstreamModelAliasTest -v`
Expected: Existing alias mapping test still passes after the new `/v1/models` implementation.

**Step 2: Adjust the implementation only if needed**

If the new merge logic accidentally changes alias ordering or ownership fields, update the implementation without touching image generation mapping.

**Step 3: Run the focused suite again**

Run the same command and confirm PASS.

### Task 3: Run full regression

**Files:**
- Modify: `app/routers/models.py`
- Modify: `tests/test_pollinations_integration.py`
- Create: `app/services/upstream_models.py`

**Step 1: Run the full integration suite**

Run: `python3 -m unittest tests.test_pollinations_integration -v`

**Step 2: Confirm expected behavior**

Expected:
- `/v1/models` includes local aliases and upstream image models
- video models are filtered out
- chat completions compatibility tests still pass
- image generation alias mapping still passes

**Step 3: Commit**

```bash
git add app/routers/models.py app/services/upstream_models.py tests/test_pollinations_integration.py docs/plans/2026-03-23-hybrid-image-model-list-design.md docs/plans/2026-03-23-hybrid-image-model-list.md
git commit -m "feat: merge upstream image models into model list"
```
