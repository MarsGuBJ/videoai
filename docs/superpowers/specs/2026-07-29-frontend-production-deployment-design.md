# Frontend Production Deployment Design

## Goal

Replace the frontend's Vite development server with a production Nginx container while preserving the public URL `http://10.10.3.100:5173`.

## Scope

- Build the React application with `npm run build` in a Node build stage.
- Serve only the generated `dist` directory from an Nginx runtime stage.
- Keep host and container port `5173` for the frontend service.
- Proxy same-origin `/api/` requests to `http://backend:8081`.
- Preserve all frontend routes and existing application behavior.
- Rebuild and restart only the `frontend` service on `10.10.3.100`.
- Do not modify the remote `.env`, backend services, camera data, or stream configuration.

## Architecture

The frontend image will use two Docker stages:

1. A `node:22` builder installs the locked dependencies and runs the existing TypeScript and Vite production build.
2. An `nginx:1.27-alpine` runtime copies `/app/dist` into the Nginx document root and listens on port `5173`.

Nginx will provide two request paths:

- Static and SPA requests use `try_files $uri $uri/ /index.html` so direct navigation to React routes continues to work.
- `/api/` requests proxy to the Compose backend service. Proxy buffering and response buffering are disabled, and the read timeout is extended for FLV and MJPEG streaming responses.
- JavaScript, CSS, JSON, and SVG responses use gzip compression; FLV responses remain uncompressed and unbuffered.

The browser will use relative `/api` URLs. The frontend service will no longer depend on a runtime `VITE_API_BASE_URL`, because Vite variables are compile-time values and Nginx does not consume the current environment entry.

## Error Handling

- Nginx returns its normal `502` response when the backend is unavailable while continuing to serve the frontend shell.
- Streaming connections are forwarded without response buffering so data is delivered as it arrives.
- Static assets use production cache headers; `index.html` remains revalidated so deployments are picked up without stale entry HTML.

## Verification

1. Add a dependency-free deployment contract test before changing production files. It must require a multi-stage image, an Nginx runtime, SPA fallback, same-origin API proxying, static text compression, disabled stream buffering, and port `5173`.
2. Run the test before implementation and confirm it fails because the current image runs `npm run dev` and has no Nginx configuration.
3. Implement the Dockerfile and Nginx configuration, then confirm the contract test and all existing frontend tests pass.
4. Run `npm run build` and build the frontend Docker image locally.
5. Deploy only the frontend production files and recreate only the remote `frontend` service.
6. Confirm the container command is Nginx, the service remains bound to `10.10.3.100:5173`, SPA routes and `/api/cameras` return `200`, no `/@vite/client` script is emitted, and a live FLV request returns the `FLV` header.

## Rollback

Restore the previous frontend Dockerfile and Compose frontend configuration, rebuild the earlier image, and recreate only the `frontend` service. No data rollback is required.
