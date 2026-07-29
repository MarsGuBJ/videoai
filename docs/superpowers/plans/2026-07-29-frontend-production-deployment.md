# Frontend Production Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Vite development server with an Nginx production image while preserving `http://10.10.3.100:5173` and same-origin streaming API access.

**Architecture:** Build the React application in a Node stage and copy only `dist` into an Nginx runtime stage. Nginx serves SPA routes and proxies `/api/` to the Compose backend with buffering disabled for long-lived FLV and MJPEG responses.

**Tech Stack:** React, TypeScript, Vite, Node.js built-in test runner, Docker multi-stage builds, Nginx, Docker Compose

---

## File Structure

- `frontend/tests/production-deployment.test.mjs`: dependency-free contract test for the production image and Nginx streaming proxy.
- `frontend/Dockerfile`: Node build stage and minimal Nginx runtime stage.
- `frontend/nginx.conf`: static file, SPA fallback, cache policy, and `/api/` proxy behavior.
- `frontend/.dockerignore`: excludes local dependencies and generated build output from the Docker context.

### Task 1: Add the production deployment contract

**Files:**
- Create: `frontend/tests/production-deployment.test.mjs`
- Test: `frontend/tests/production-deployment.test.mjs`

- [ ] **Step 1: Write the failing contract test**

```javascript
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const dockerfile = readFileSync(new URL('../Dockerfile', import.meta.url), 'utf8');
const nginx = readFileSync(new URL('../nginx.conf', import.meta.url), 'utf8');

test('frontend uses a production Nginx image', () => {
  assert.match(dockerfile, /FROM node:22 AS build/);
  assert.match(dockerfile, /RUN npm run build/);
  assert.match(dockerfile, /FROM nginx:1\.27-alpine/);
  assert.match(dockerfile, /COPY --from=build \/app\/dist \/usr\/share\/nginx\/html/);
  assert.doesNotMatch(dockerfile, /npm.*run.*dev/);
});

test('Nginx preserves port, SPA routes, and streaming API semantics', () => {
  assert.match(nginx, /listen 5173;/);
  assert.match(nginx, /try_files \$uri \$uri\/ \/index\.html;/);
  assert.match(nginx, /location \/api\//);
  assert.match(nginx, /proxy_pass http:\/\/backend:8081;/);
  assert.match(nginx, /proxy_buffering off;/);
  assert.match(nginx, /proxy_request_buffering off;/);
  assert.match(nginx, /proxy_read_timeout 3600s;/);
});

test('Nginx compresses production text assets without buffering streams', () => {
  assert.match(nginx, /gzip on;/);
  assert.match(nginx, /gzip_types text\/css application\/javascript application\/json image\/svg\+xml;/);
  assert.doesNotMatch(nginx, /gzip_types[^;]*video\/x-flv/);
});
```

- [ ] **Step 2: Run the test and verify RED**

Run from `frontend/`:

```bash
node --test tests/production-deployment.test.mjs
```

Expected: FAIL because `nginx.conf` does not exist and the current Dockerfile runs `npm run dev`.

### Task 2: Build the production frontend image

**Files:**
- Modify: `frontend/Dockerfile`
- Create: `frontend/nginx.conf`
- Create: `frontend/.dockerignore`
- Test: `frontend/tests/production-deployment.test.mjs`

- [ ] **Step 1: Replace the frontend Dockerfile**

```dockerfile
FROM node:22 AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN HTTP_PROXY= HTTPS_PROXY= http_proxy= https_proxy= ALL_PROXY= all_proxy= npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 5173
```

- [ ] **Step 2: Add the Nginx production configuration**

```nginx
server {
    listen 5173;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    gzip on;
    gzip_comp_level 6;
    gzip_min_length 1024;
    gzip_vary on;
    gzip_types text/css application/javascript application/json image/svg+xml;

    location = /index.html {
        add_header Cache-Control "no-cache";
    }

    location /assets/ {
        try_files $uri =404;
        add_header Cache-Control "public, max-age=31536000, immutable";
    }

    location /api/ {
        proxy_pass http://backend:8081;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
        proxy_request_buffering off;
        proxy_cache off;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

- [ ] **Step 3: Exclude local generated content from the image context**

```dockerignore
node_modules
dist
.vite
npm-debug.log*
```

- [ ] **Step 4: Run the focused test and verify GREEN**

Run from `frontend/`:

```bash
node --test tests/production-deployment.test.mjs
```

Expected: 3 tests pass.

- [ ] **Step 5: Run all frontend tests and production build**

Run from `frontend/`:

```bash
node --test tests/*.test.mjs
npm run build
docker build -t videoai-frontend-production-test .
```

Expected: all tests pass, Vite build exits `0`, and Docker creates an Nginx-based image.

- [ ] **Step 6: Inspect the built image contract**

```bash
docker image inspect videoai-frontend-production-test --format '{{json .Config.Cmd}} {{json .Config.ExposedPorts}}'
```

Expected: command is Nginx's default startup and exposed ports contain `5173/tcp`; no Vite development command is present.

### Task 3: Deploy and verify `10.10.3.100`

**Files:**
- Deploy: `frontend/Dockerfile`
- Deploy: `frontend/nginx.conf`
- Deploy: `frontend/.dockerignore`

- [ ] **Step 1: Back up the remote frontend deployment files**

Create a timestamped directory under `/home/public/videoai/backups/` and copy the current remote `frontend/Dockerfile`. Copy `frontend/nginx.conf` and `frontend/.dockerignore` only when they already exist.

Expected: backup paths remain on the remote server and no application data changes.

- [ ] **Step 2: Upload only the production frontend files**

Upload the three deployment files to `/home/public/videoai/frontend/` using temporary names followed by atomic rename.

Expected: remote `.env`, `docker-compose.yml`, source code, storage, and backend files remain unchanged.

- [ ] **Step 3: Build and recreate only the frontend service**

Run remotely:

```bash
cd /home/public/videoai
docker compose build frontend
docker compose up -d --no-deps --force-recreate frontend
```

Expected: `videoai-frontend-1` runs Nginx and remains bound to `10.10.3.100:5173`.

- [ ] **Step 4: Verify production static serving**

Run remotely:

```bash
curl -fsS http://10.10.3.100:5173/ > /tmp/videoai-index.html
curl -fsS -o /dev/null -w '%{http_code}' http://10.10.3.100:5173/live-preview
docker compose exec -T frontend nginx -t
docker compose exec -T frontend ps
```

Expected: index and SPA route return `200`, `nginx -t` succeeds, the process list contains Nginx, and index HTML does not reference `/@vite/client` or `/src/main.tsx`.

- [ ] **Step 5: Verify same-origin API and FLV streaming**

Run remotely:

```bash
curl -fsS -o /dev/null -w '%{http_code}' http://10.10.3.100:5173/api/cameras
timeout 15 curl -fsS http://10.10.3.100:5173/api/live/63c62157-31d8-4737-8169-6bbb9c724f15.live.flv | head -c 4 | od -An -tx1
```

Expected: camera API returns `200` and the stream begins with bytes `46 4c 56 01` (`FLV` plus version 1).

- [ ] **Step 6: Re-run the client-side symptom check**

Measure `/`, the emitted production JavaScript asset, `/api/cameras`, and the FLV endpoint from the workstation. Open `/live-preview` in the browser and verify the React root contains the live preview UI and video elements.

Expected: no Vite development module graph is requested, the page mounts, and visible camera streams begin loading. Remaining VPN packet loss must be reported separately if it still limits sustained playback.
