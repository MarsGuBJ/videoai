# SXin iframe URL Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Change the SXin assistant iframe to `http://10.10.3.100:2026/iot-os/sxin/#/mockLogin` and deploy the rebuilt frontend.

**Architecture:** Keep the existing hard-coded iframe pattern and replace only its `src`. Add a dependency-free Node source assertion so the exact deployment URL remains covered without introducing a frontend test framework.

**Tech Stack:** React, TypeScript, Vite, Node.js built-in test runner, Docker Compose

---

### Task 1: Add the URL regression assertion

**Files:**
- Create: `frontend/tests/sxin-url.test.mjs`
- Test: `frontend/tests/sxin-url.test.mjs`

- [ ] **Step 1: Write the failing test**

```javascript
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const appSource = await readFile(new URL('../src/App.tsx', import.meta.url), 'utf8');

test('SXin assistant iframe uses the deployed port 2026 URL', () => {
  assert.match(
    appSource,
    /src="http:\/\/10\.10\.3\.100:2026\/iot-os\/sxin\/#\/mockLogin"/,
  );
  assert.doesNotMatch(appSource, /192\.168\.11\.194:10997/);
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `node --test tests/sxin-url.test.mjs` from `frontend/`.

Expected: FAIL because `App.tsx` still contains `http://192.168.11.194:10997/iot-os/sxin/#/mockLogin`.

### Task 2: Replace the iframe URL

**Files:**
- Modify: `frontend/src/App.tsx:79`
- Test: `frontend/tests/sxin-url.test.mjs`

- [ ] **Step 1: Apply the minimal implementation**

Replace the iframe attribute with:

```tsx
src="http://10.10.3.100:2026/iot-os/sxin/#/mockLogin"
```

- [ ] **Step 2: Run the regression assertion**

Run: `node --test tests/sxin-url.test.mjs` from `frontend/`.

Expected: PASS, 1 test passed.

- [ ] **Step 3: Build the frontend**

Run: `npm run build` from `frontend/`.

Expected: TypeScript and Vite build complete successfully with exit code 0.

- [ ] **Step 4: Inspect the focused diff**

Run: `git diff -- frontend/src/App.tsx frontend/tests/sxin-url.test.mjs`.

Expected: the new test and only the intended iframe URL change attributable to this task. Do not commit the existing unrelated `App.tsx` working-tree changes.

### Task 3: Deploy and verify the target frontend

**Files:**
- Deploy: `frontend/src/App.tsx`
- Deploy: `frontend/tests/sxin-url.test.mjs`

- [ ] **Step 1: Confirm the target source matches before upload**

Compare SHA-256 for local and `/home/public/videoai/frontend/src/App.tsx` on `10.10.3.100`.

Expected: hashes match before the one-line local edit is uploaded, apart from the known URL change.

- [ ] **Step 2: Upload changed frontend files**

Upload the files to `/home/public/videoai/frontend/`, using a temporary filename followed by an atomic rename.

- [ ] **Step 3: Rebuild and recreate the frontend container**

Run on `10.10.3.100`:

```bash
cd /home/public/videoai
docker compose build frontend
docker compose up -d --no-deps frontend
```

Expected: `videoai-frontend-1` is running and bound to `10.10.3.100:5173`.

- [ ] **Step 4: Verify the deployment**

Run the source assertion on the server, request `http://10.10.3.100:5173/sxin-assistant`, inspect the emitted JavaScript bundle for the exact port `2026` URL, and confirm `http://10.10.3.100:2026/iot-os/sxin/` responds.

Expected: assertion passes, frontend returns HTTP 200, bundle contains the exact iframe URL, and the iframe target returns an HTTP response.
