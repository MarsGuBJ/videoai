# Migration Notes — Conventions for Page-Conversion Agents

This project is a mechanical port of the single-file Vue 3 prototype
`D:/pyprojects/offline-package/index.html` (Options API, global build) to
Vue 3 + Vite + TS. The shell (router, store, layout, overlays) is done.
Your job: convert ONE prototype page component into an SFC under `src/pages/`.
Preserve UI behavior and appearance exactly — this is a port, not a redesign.
No UI libraries, no Pinia, no axios.

## (a) File & component shape

- One SFC per page at `src/pages/<PrototypeComponentName>.vue`, named EXACTLY
  like the prototype component (e.g. `OverviewPage.vue`, `CameraListPage.vue`,
  `MediaDeviceWizardPage.vue`, `EventConfigSubscriptionsPage.vue`). The router
  (`src/router/index.ts`) already lazy-imports these exact paths.
- Options API, `<script lang="ts">` with `defineComponent`, `<template>` block.
  TS is loose (`strict: false`) — use `any` freely.
- Every page declares the full prototype `pageProps` array (prototype line 11423)
  and uses what it needs:

  ```ts
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  ```

  These are forwarded by `<router-view>` in `App.vue` as fallthrough attrs, so
  you MUST declare them as props to receive them.
- Keep `inject: [...]` declarations exactly as the prototype component declares
  them. `App.vue` provides: `setRoute`, `showToast`, `openResult`,
  `openReviewTask`, `openModal`, `clearImage`, `setTrackView`,
  `openVersionManager`, `openVersionDetail`, `openVersionPreview`,
  `openDeployDetail`, `openEventDetail` — all with the same signatures as the
  prototype. To satisfy `vue-tsc`, annotate injected members, e.g.
  `inject: { showToast: { from: "showToast", default: (m: string) => {} } }`
  or cast `(this as any).showToast(...)`.

## (b) Navigation

- Navigation is name-based via vue-router. Route name === prototype route key
  (`home`, `exact`, `mediaDeviceWizard`, `eventConfigSubscriptions`, ...), path
  is `/<routeName>`. `/` redirects to `/home`; catch-all redirects to `/`.
- **Chosen convention: call the injected `setRoute` exactly like the prototype
  does** — `this.setRoute("imageSearch", { prefill, imageCrop, selectedIndexes, trackView })`.
  App's `setRoute` handles the options (prefill / imageCrop / trackView /
  selectedResultIndexes), the pseudo-routes `newDeployTask` / `newAlgorithm` /
  `newVersion` (open modal + navigate), and then performs
  `router.push({ name: route })`. Do NOT reimplement that logic in pages.
- For plain jumps with no options, `this.$router.push({ name: "events" })` is
  also acceptable and equivalent.
- `state.route` is kept in sync with the current route name by App (watch on
  `$route.name`); pages may keep reading `this.state.route`.
- App re-mounts the page when navigating to the same route again
  (`state.routeVersion` is part of the `<router-view>` `:key`), same as the
  prototype. Don't add your own remount hacks.

## (c) Mock data

- **Chosen convention: read mock data via the prop — `this.store.<table>`**
  (e.g. `this.store.results`, `this.store.eventRows`, `this.store.navGroups`).
  It is the same reactive singleton (`reactive(...)`) that App passes down.
  Mutations through it are visible everywhere, as in the prototype.
- You MAY also `import { store } from "../store"` — it is the identical object —
  but prefer the prop for parity with the prototype.
- `src/store/index.ts` also exports the prototype's helper functions:
  `statusClass`, `levelClass`, `priorityClass`, `similarityColor`, `isActiveNav`.
  In templates/methods, `statusClass` / `levelClass` / `priorityClass` are
  additionally available as global properties (registered in `src/main.ts`,
  typed in `src/global.d.ts`) — call them bare exactly like the prototype does.
  Import `similarityColor` / `isActiveNav` from `"../store"` when needed.

## (d) Styles

- ALL prototype CSS is one global block, now at `src/styles/global.css`
  (imported once in `src/main.ts`). Every global class (`.btn`, `.nav-item`,
  `.status-pill`, CSS vars like `--blue`, ...) is already available everywhere.
- Pages therefore need **NO `<style>` block at all** in the normal case. Only
  add `<style scoped>` if you can point to genuinely component-specific CSS —
  the prototype has none, so expect to ship zero style blocks.
- Do not re-declare or "clean up" global classes.

## (e) Template conversion rules

- Copy the prototype component's `template:` backtick string verbatim into the
  SFC `<template>` block. The file contains NO `\`` escape sequences and no
  `${...}` inside template strings — `${...}` occurs only in JS code
  (methods/computed), which moves into `<script>` unchanged.
- HTML entities in template text such as `&#xf078;` (FontAwesome glyphs) work
  as-is in SFC templates — keep them.
- Keep kebab-case component tags (`<video-results>`, `<nav-sub-group>`), class
  names, `v-if`/`v-for`/`:class` bindings, and event wiring identical.
- In `<script>`: `data()`, `computed`, `methods`, lifecycle hooks port 1:1.
  Add `as any` / param types only where `vue-tsc` requires it.

## (f) Shared components

- `src/components/VideoResults.vue` and `src/components/ImageResults.vue`
  (built in parallel) — used by the search pages exactly as in the prototype;
  they take props `["store", "state"]`.
- `src/components/ImageCropDialog.vue` — App already mounts one instance for
  the drawer crop flow. If YOUR page renders its own crop dialog in the
  prototype, import it and wire it the same way the prototype does
  (props `open`, `item`, `action`, `itemIndex`; emits `close`, `confirm`).
- `src/components/SummaryCards.vue` — props `["cards"]`, used by e.g.
  VersionManagerPage.
- Layout (`AppSidebar`/`AppTopbar`/`NavSubGroup`) and `DrawerHost`/`ModalHost`/
  `SxinAgent` live at App level — pages never import them.

## (g) Real-API pages

- For pages that talk to the backend instead of mock data:
  `import { api, assetUrl, streamUrl, cameraStreamUrl } from "../api"` and
  `import VideoPlayer from "../components/VideoPlayer.vue"` (both built in
  parallel — assume they exist with exactly these exports).

## Known deviations from the prototype

- Topbar avatar image: the prototype referenced a source-prototype jpg that was
  not among the prepared assets; `AppTopbar.vue` uses `/prototype/portrait.jpg`.
- `SxinAgent` is an overlay panel (App-level `v-if="sxinOpen"`), NOT a route —
  there is no SxinAgentPage and no `sxin` entry in `store.routeNames`.
- The routes `media` and `cameraList` both render `CameraListPage.vue` (as in
  the prototype's `currentComponent` map).

## Route table (name → page component)

`/` → redirect `/home`. One route per name, path `/<name>`:

overview → OverviewPage · cameraList → CameraListPage · media → CameraListPage ·
mediaDeviceWizard → MediaDeviceWizardPage · mediaDeviceDetail → MediaDeviceDetailPage ·
mediaDeviceEdit → MediaDeviceEditPage · mediaAccessConfig → MediaAccessConfigPage ·
mediaPreview → MediaPreviewPage · mediaPlayback → MediaPlaybackPage ·
mediaWall → MediaWallPage · mediaAlarm → MediaAlarmPage · home → HomePage ·
exact → ExactSearchPage · localVideo → LocalVideoPage · textImage → TextImagePage ·
imageSearch → ImageSearchPage · quickDeploy → QuickDeployPage · track → TrackPage ·
monitorSearch → MonitorSearchPage · reviewTasks → ReviewTasksPage ·
reviewTypes → ReviewTypesPage · algorithms → AlgorithmsPage ·
versionManager → VersionManagerPage · versionDetail → VersionDetailPage ·
previewFile → PreviewFilePage · deployTasks → DeployTasksPage ·
deployTaskDetail → DeployTaskDetailPage · events → EventsPage ·
eventDetail → EventDetailPage · stats → StatsPage · eventConfig → EventConfigPage ·
eventConfigInfo → EventConfigInfoPage · eventConfigIngestion → EventConfigIngestionPage ·
eventConfigDedup → EventConfigDedupPage ·
eventConfigSubscriptions → EventConfigSubscriptionsPage ·
modelConfig → ModelConfigPage · resource → ResourcePage · logs → LogsPage ·
permissions → PermissionsPage

## Verification

`npx vue-tsc --noEmit -p tsconfig.json` (from `frontend/`). Until all pages and
parallel components land, TS2307 "Cannot find module '../pages/...'" errors are
expected. Your page must not add any OTHER error.
