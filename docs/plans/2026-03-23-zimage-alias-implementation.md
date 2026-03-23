# Z-Image Alias Presets Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Expose only configured `z-image-*` aliases to downstream clients and map those aliases to upstream `zimage` requests with fixed sizes and `safe=false`.

**Architecture:** Add a dedicated preset-mapping module that owns alias definitions and resolution logic. Reuse that module in both `/v1/models` and `/v1/images/generations`, and keep URL construction responsible for emitting the final upstream query parameters.

**Tech Stack:** FastAPI, Pydantic, unittest, httpx

---

### Task 1: Lock the expected alias behavior in tests

**Files:**
- Modify: `tests/test_pollinations_integration.py`

**Step 1: Write the failing test**

Add tests that assert:
- the generated upstream URL includes `safe=false`
- `/v1/models` returns only the configured alias presets
- image generation maps `z-image-1216x832` to `zimage` and fixed size `1216x832`

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_pollinations_integration -v`
Expected: assertions fail because current code exposes upstream models directly, does not resolve alias presets, and does not append `safe=false`

**Step 3: Write minimal implementation**

Implement the preset mapping module, update routes to use it, and append `safe=false` in the upstream image URL builder.

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_pollinations_integration -v`
Expected: PASS

### Task 2: Remove obsolete upstream model-list passthrough

**Files:**
- Modify: `app/main.py`
- Modify: `app/services/pollinations.py`

**Step 1: Write the failing test**

The alias-list test from Task 1 already covers this behavior.

**Step 2: Run test to verify it fails**

Use the same command from Task 1.

**Step 3: Write minimal implementation**

Remove the unused upstream model cache warm-up path once `/v1/models` is served from local presets.

**Step 4: Run test to verify it passes**

Use the same command from Task 1.
