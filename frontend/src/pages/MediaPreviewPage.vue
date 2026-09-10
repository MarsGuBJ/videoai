<template>
  <section class="content review-wide media-preview-page">
    <div class="review-titlebar"><div><h1>实时预览</h1><p>多设备、多分屏实时查看现场画面和音频内容，支持云台控制与预置点调用</p></div></div>
    <div class="media-console-grid">
      <aside class="panel media-resource-panel">
        <div class="media-resource-tabs"><button :class="{ active: activeResourceTab === 'monitor' }" @click="activeResourceTab = 'monitor'">监控点</button><button :class="{ active: activeResourceTab === 'favorite' }" @click="activeResourceTab = 'favorite'">收藏</button><button :class="{ active: activeResourceTab === 'history' }" @click="activeResourceTab = 'history'">场景</button></div>
        <input class="input" placeholder="搜索监控点名称/IP" aria-label="搜索监控点名称或IP" v-model="searchKeyword" />
        <div v-if="activeResourceTab === 'monitor'" class="media-playback-tree"><div class="media-panel-head"><b>监控资源</b><span class="hint-text">区域 / 监控点</span></div><div class="media-playback-tree-list exact-tree-list"><div v-for="region in displayRegions" :key="region.fullPath"><button class="exact-tree-area-row" :class="{ active: selectedRegion && selectedRegion.fullPath === region.fullPath }" :style="region.child ? 'padding-left:24px;' : ''" @click="toggleRegion(region)"><span>{{ expandedRegions[region.fullPath] ? '⌄' : '›' }} {{ region.name }}</span><span>{{ camerasForRegion(region).length }} 台设备</span></button><div v-if="expandedRegions[region.fullPath]" class="exact-tree-children"><button v-for="camera in camerasForRegion(region)" :key="camera.code" class="exact-tree-device" :class="{ active: selectedCamera && selectedCamera.code === camera.code }" draggable="true" title="点击放入当前窗口，或拖拽到目标窗口" @dragstart="onCameraDragStart($event, camera)" @click="selectCamera(camera, region)"><span>{{ camera.name }}</span><span class="link-blue" style="margin-left:auto;" :title="isFavorite(camera.code) ? '取消收藏' : '收藏'" @click.stop="toggleFavorite(camera.code)">{{ isFavorite(camera.code) ? '★' : '☆' }}</span></button></div></div><div v-if="!displayRegions.length" style="padding:12px;color:#888;">{{ searchKeyword ? '无匹配监控点' : '暂无监控点，请先在设备管理中添加设备' }}</div></div></div>
        <ul v-else-if="activeResourceTab === 'favorite'" class="media-resource-list"><li class="group">我的收藏</li><li v-for="camera in favoriteCameras" :key="camera.code" style="cursor:pointer;" @click="selectCameraById(camera.code)"><span class="online-dot">★</span>{{ camera.name }}<span class="link-red" style="margin-left:auto;" @click.stop="toggleFavorite(camera.code)">取消</span></li><li v-if="!favoriteCameras.length" style="color:#888;">暂无收藏，在监控点列表点击 ☆ 收藏</li></ul>
        <ul v-else class="media-plan-list"><li v-for="scene in sceneRecords" :key="scene.id" style="cursor:pointer;" title="点击还原该场景的全部视频流" @click="restoreScene(scene)"><template v-if="renamingSceneId === scene.id"><input class="input" v-model="renamingSceneName" style="width:100%;" @click.stop @keyup.enter="confirmRenameScene" @keyup.esc="cancelRenameScene" /><div style="display:flex;gap:10px;"><span class="link-blue" @click.stop="confirmRenameScene">确定</span><span class="link-red" @click.stop="cancelRenameScene">取消</span></div></template><template v-else><b>▦ {{ scene.name }}</b><span>{{ scene.time }}</span><div style="display:flex;gap:10px;"><span class="link-blue" @click.stop="startRenameScene(scene)">改名</span><span class="link-red" @click.stop="removeScene(scene)">删除</span></div></template></li><li v-for="record in historyRecords" :key="record.id + record.time" style="cursor:pointer;" @click="selectCameraById(record.id)"><b>{{ record.name }}</b><span>{{ record.time }}</span></li><li v-if="!sceneRecords.length && !historyRecords.length" style="color:#888;">暂无预览历史</li></ul>
      </aside>
      <section class="panel media-stage-panel">
        <div class="media-stage-toolbar"><div class="media-layout-buttons"><span>分屏</span><button v-for="count in [1, 4, 9, 16]" :key="count" :class="{ active: previewLayout === count }" @click="changeLayout(count)">{{ count }}</button></div><div class="media-control-buttons"><button class="btn" @click="saveScene">保存场景</button><select class="select" style="width:96px;" v-model="streamType" aria-label="码流类型" @change="onStreamTypeChange"><option value="main">主码流</option><option value="sub">子码流</option></select><button class="btn" @click="openModal('videoConfig')">视频参数</button><select class="select" style="width:96px;" v-model="videoFit" aria-label="画面比例" @change="onVideoFitChange"><option value="contain">原始比例</option><option value="cover">满屏窗口</option></select></div></div>
        <div class="media-video-grid" ref="videoGrid" :class="gridClass"><article v-for="(feed, index) in visibleFeeds" :key="feed ? feed.name + '-' + index : 'empty-' + index" class="media-video-tile" :class="{ selected: feed && selectedFeed === index, 'drop-hover': dropHoverIndex === index }" @click="feed && selectFeed(index)" @dragover.prevent="onTileDragOver(index)" @dragleave="onTileDragLeave(index)" @drop="onTileDrop($event, index)"><video-player v-if="feed && feed.camera" :ref="(el: any) => setPlayerRef(el, index)" :url="feedUrl(feed)" :fit="videoFit" :show-zoom-bar="!!feed.digitalZoom" /><div v-else class="media-video-empty">请从左侧选择一个监控点上屏</div><template v-if="previewLayout === 1 && feed"><button class="media-feed-switch prev" title="上一路" aria-label="上一路摄像头" @click.stop="switchFeed(-1)">‹</button><button class="media-feed-switch next" title="下一路" aria-label="下一路摄像头" @click.stop="switchFeed(1)">›</button></template><span class="media-video-clock">{{ now }}</span></article><button v-if="gridFullscreen" class="media-fullscreen-exit" title="取消全屏" aria-label="取消全屏" @click="exitGridFullscreen">⛶</button></div>
        <div class="media-stage-controls"><div class="media-control-buttons"><button class="media-icon-button" :title="ctrlPaused ? '播放' : '暂停'" @click="togglePlay">{{ ctrlPaused ? '▶' : '⏸' }}</button><button class="media-icon-button" title="停止" @click="stopSelected">■</button><button class="media-icon-button" :title="ctrlMuted ? '打开声音' : '静音'" @click="toggleSound">{{ ctrlMuted ? '静' : '♪' }}</button><button class="media-icon-button" title="抓拍" @click="snapshotSelected">▣</button><button class="btn" @click="openModal('quickReplay')">即时回放</button><button class="btn" @click="setRoute('mediaPlayback')">切至录像</button><button class="btn" :class="{ primary: selectedDigitalZoom }" @click="toggleDigitalZoom">电子放大</button><button class="btn" @click="snapshotSelected">保存截图</button></div><span class="media-network-state">{{ selectedFeedName ? '当前窗口：' + selectedFeedName : '点击窗口或左侧监控点选择一路设备' }}</span></div>
      </section>
      <aside class="panel media-ptz-panel">
        <div class="media-ptz-section"><div class="media-panel-head"><b>云台控制</b><span class="status-pill" :class="ptzLocked || !ptzSupported ? 'waiting' : 'pass'">{{ !ptzCamera ? '未选择设备' : !ptzSupported ? '设备不支持' : ptzLocked ? '已锁定' : '已解锁' }}</span></div><div class="media-ptz-wheel"><button class="up" :disabled="ptzDisabled" @click="ptz('up')">▲</button><button class="left" :disabled="ptzDisabled" @click="ptz('left')">◀</button><button class="center" :disabled="ptzDisabled" @click="ptz('stop')">●</button><button class="right" :disabled="ptzDisabled" @click="ptz('right')">▶</button><button class="down" :disabled="ptzDisabled" @click="ptz('down')">▼</button></div><div class="media-range-list"><label>云台步长<input type="range" min="1" max="10" v-model.number="ptzStep" :disabled="ptzDisabled" /></label></div><div class="media-control-buttons" style="margin-top:12px;"><button class="btn primary" :disabled="ptzDisabled" @click="ptzLocked = true">锁定云台</button><button class="btn" :disabled="!ptzLocked" @click="ptzLocked = false">解锁</button></div></div>
        <div class="media-ptz-section"><div class="media-range-list"><label>变倍<input type="range" min="0" max="10" v-model.number="zoomLevel" :disabled="ptzDisabled" @change="onZoomChange" /></label><label>变焦<input type="range" min="0" max="10" v-model.number="focusLevel" :disabled="ptzDisabled" /></label><label>光圈<input type="range" min="0" max="10" v-model.number="irisLevel" :disabled="ptzDisabled" /></label></div></div>
        <div class="media-ptz-section"><div class="media-panel-head"><b>预置点</b><button class="link-blue" :disabled="!ptzSupported" @click="addPreset">＋</button></div><ul class="media-preset-list"><li v-for="preset in currentPresets" :key="preset.id"><span>{{ preset.id }} {{ preset.name }}</span><button class="link-blue" :disabled="ptzDisabled" @click="callPreset(preset)">调用</button><button class="link-red" @click="removePreset(preset)">删除</button></li><li v-if="!currentPresets.length" style="color:#888;">{{ !ptzCamera ? '请先选择一路真实摄像头' : !ptzSupported ? '当前设备不支持云台控制' : '暂无预置点，点 ＋ 保存当前云台参数' }}</li></ul></div>
      </aside>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { api, cameraStreamUrl } from "../api";
import type { PtzCommand } from "../api";
import { loadPlayerSettings, snapshotFileName } from "../utils/player-settings";
import { buildRegionTree, loadCustomRegions, normalizePath, type RegionNode } from "../utils/regions";
import VideoPlayer from "../components/VideoPlayer.vue";

const FAVORITES_KEY = "videoai.media.favorites";
const HISTORY_KEY = "videoai.media.previewHistory";
const PRESETS_KEY = "videoai.media.presets";
const SCENES_KEY = "videoai.media.scenes";
const HISTORY_LIMIT = 20;
const SCENE_LIMIT = 20;

type PresetParams = {
  step: number;
  zoom: number;
  focus: number;
  iris: number;
};

type CameraPreset = {
  id: number;
  name: string;
  params: PresetParams;
};

function statusLabel(status: string): string {
  const value = (status || "").toUpperCase();
  if (value === "RUNNING") return "在线";
  if (value === "STOPPED") return "离线";
  if (value === "DISABLED") return "停用";
  return "未成功连接";
}

function loadJson(key: string, fallback: any) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function saveJson(key: string, value: any) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // localStorage 不可用时忽略
  }
}

function formatTime(d: Date): string {
  const pad = (n: number) => n.toString().padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

export default defineComponent({
  name: "MediaPreviewPage",
  components: { VideoPlayer },
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  inject: {
    openModal: { from: "openModal", default: (name: string) => {} },
    setRoute: { from: "setRoute", default: (route: string, options?: any) => {} },
    showToast: { from: "showToast", default: (m: string) => {} },
  },
  data() {
    return {
      activeResourceTab: "monitor",
      searchKeyword: "",
      // 启动窗口来自视频参数设置（默认 2x2）
      previewLayout: loadPlayerSettings().startupLayout,
      selectedFeed: 0,
      streamType: "main",
      selectedRegion: null as RegionNode | null,
      selectedCamera: null as any,
      videoFit: "contain",
      gridFullscreen: false,
      ctrlPaused: false,
      ctrlMuted: true,
      ptzStep: 5,
      ptzLocked: false,
      zoomLevel: 5,
      focusLevel: 5,
      irisLevel: 5,
      prevZoomLevel: 5,
      startRequests: new Set<string>(),
      cameraList: [] as any[],
      regions: [] as RegionNode[],
      regionCameras: {} as Record<string, any[]>,
      expandedRegions: {} as Record<string, boolean>,
      feeds: [] as any[],
      playerRefs: {} as Record<number, any>,
      favoriteIds: loadJson(FAVORITES_KEY, []) as string[],
      historyRecords: loadJson(HISTORY_KEY, []) as any[],
      sceneRecords: loadJson(SCENES_KEY, []) as any[],
      renamingSceneId: "",
      renamingSceneName: "",
      presetsByCamera: loadJson(PRESETS_KEY, {}) as Record<string, CameraPreset[]>,
      dropHoverIndex: -1,
      now: formatTime(new Date()),
      nowTimer: null as number | null
    };
  },
  computed: {
    gridClass(): Record<string, boolean> {
      return {
        single: this.previewLayout === 1,
        "grid-9": this.previewLayout === 9,
        "grid-16": this.previewLayout === 16
      };
    },
    visibleFeeds(): any[] {
      const list: any[] = [];
      for (let i = 0; i < this.previewLayout; i += 1) {
        list.push(this.feeds[i] || null);
      }
      return list;
    },
    displayRegions(): RegionNode[] {
      if (!this.searchKeyword.trim()) return this.regions;
      return this.regions.filter(region => this.camerasForRegion(region).length > 0);
    },
    favoriteCameras(): any[] {
      return this.cameraList
        .filter(camera => this.favoriteIds.includes(camera.id))
        .map(camera => ({ name: camera.name, code: camera.id }));
    },
    selectedFeedName(): string {
      const feed = this.visibleFeeds[this.selectedFeed];
      return feed ? feed.name : "";
    },
    selectedDigitalZoom(): boolean {
      const feed = this.visibleFeeds[this.selectedFeed];
      return !!(feed && feed.digitalZoom);
    },
    ptzCamera(): any {
      if (this.selectedCamera && this.selectedCamera.camera) {
        return this.selectedCamera.camera;
      }
      const feed = this.visibleFeeds[this.selectedFeed];
      return feed && feed.camera ? feed.camera : null;
    },
    // 设备能力来自设备管理页的能力配置（ptzEnabled）：不支持云台的设备禁用全部云台/变倍/变焦/光圈控制
    ptzSupported(): boolean {
      const camera = this.ptzCamera;
      return !!(camera && camera.ptzEnabled);
    },
    ptzDisabled(): boolean {
      return this.ptzLocked || !this.ptzSupported;
    },
    currentPresets(): CameraPreset[] {
      const camera = this.ptzCamera;
      if (!camera) return [];
      return this.presetsByCamera[camera.id] || [];
    }
  },
  mounted() {
    this.loadCameras();
    this.nowTimer = window.setInterval(() => {
      this.now = formatTime(new Date());
    }, 1000);
    document.addEventListener("fullscreenchange", this.onFullscreenChange);
  },
  beforeUnmount() {
    if (this.nowTimer !== null) {
      window.clearInterval(this.nowTimer);
      this.nowTimer = null;
    }
    document.removeEventListener("fullscreenchange", this.onFullscreenChange);
  },
  watch: {
    // 设备管理页增删改设备或新增区域后，刷新监控点树
    "state.camerasVersion"() {
      this.loadCameras();
    }
  },
  methods: {
    async loadCameras() {
      try {
        const list = await api.cameras();
        this.cameraList = list || [];
        this.applyCameras(this.cameraList);
      } catch (e) {
        // 接口不可用时保留当前树
      }
    },
    // 监控点树与设备管理页共用同一套区域聚合逻辑：
    // 设备 area 按 "/" 分层 + localStorage 自定义区域（utils/regions.ts）
    applyCameras(list: any[]) {
      const regionCameras: Record<string, any[]> = {};
      for (const c of list) {
        // 与 buildRegionTree 的 fullPath 口径一致（" / " 连接、分段 trim），否则展开区域取不到设备
        const areaPath = normalizePath(c.area) || "未分配";
        if (!regionCameras[areaPath]) {
          regionCameras[areaPath] = [];
        }
        regionCameras[areaPath].push({
          name: c.name,
          code: c.id,
          type: c.protocol || c.streamName || "IPC",
          status: statusLabel(c.status),
          camera: c,
          areaPath
        });
      }
      const regions = buildRegionTree(Object.keys(regionCameras).flatMap((path) => regionCameras[path].map(() => path)), loadCustomRegions());
      const expanded: Record<string, boolean> = {};
      regions.forEach((region, index) => {
        expanded[region.fullPath] = index === 0;
      });
      this.regionCameras = regionCameras;
      this.regions = regions;
      this.expandedRegions = expanded;
      this.selectedRegion = null;
      this.selectedCamera = null;
      // 不默认上屏：打开页面时各窗口保持空窗并提示用户选择监控点；
      // 设备列表刷新时仅同步已上屏窗口的设备最新状态，设备已删除的窗口置空
      this.feeds = this.feeds
        .filter(Boolean)
        .map((feed: any) => {
          const camera = list.find((c: any) => feed.camera && c.id === feed.camera.id);
          return camera ? this.buildFeed(camera) : null;
        });
      if (this.selectedFeed >= this.feeds.length) this.selectedFeed = 0;
      this.ctrlPaused = false;
      this.ensureStarted();
      this.syncStreamTypeSelector();
    },
    buildFeed(camera: any) {
      const feed = {
        name: camera.name,
        meta: "",
        camera,
        streamType: "main",
        digitalZoom: false
      };
      feed.meta = this.feedMeta(feed);
      return feed;
    },
    feedMeta(feed: any): string {
      const camera = feed.camera;
      const streamLabel = feed.streamType === "sub" ? "子码流" : "主码流";
      return `${camera.protocol || camera.streamName || "IPC"} · ${statusLabel(camera.status)} · ${streamLabel}`;
    },
    // 顶层区域展开时显示其全部子孙区域的设备；搜索关键字按名称/IP 过滤
    camerasForRegion(region: RegionNode): any[] {
      const keyword = this.searchKeyword.trim().toLowerCase();
      const result: any[] = [];
      for (const path of Object.keys(this.regionCameras)) {
        if (path === region.fullPath || path.startsWith(region.fullPath + " / ")) {
          result.push(...this.regionCameras[path]);
        }
      }
      if (!keyword) return result;
      return result.filter(camera =>
        camera.name.toLowerCase().includes(keyword) ||
        String(camera.camera?.ip || "").toLowerCase().includes(keyword)
      );
    },
    ensureStarted() {
      for (const feed of this.visibleFeeds) {
        const c = feed && feed.camera;
        if (c && c.status !== "RUNNING" && !this.startRequests.has(c.id)) {
          this.startRequests.add(c.id);
          api.startCamera(c.id)
            .then((started: any) => {
              if (started) {
                Object.assign(c, started);
              }
            })
            .catch(() => undefined)
            .finally(() => this.startRequests.delete(c.id));
        }
      }
    },
    feedUrl(feed: any) {
      return feed && feed.camera ? cameraStreamUrl(feed.camera, feed.streamType) : undefined;
    },
    // 码流切换作用于当前选中窗口；子码流代理由后端按厂商约定（海康 101→102、大华 subtype=0→1）注册
    onStreamTypeChange() {
      const feed = this.visibleFeeds[this.selectedFeed];
      if (!feed || !feed.camera) {
        this.streamType = "main";
        this.showToast("当前窗口无视频流");
        return;
      }
      if (this.streamType === "sub") {
        if (!feed.camera.subStreamName) {
          this.streamType = "main";
          this.showToast("该设备不支持子码流");
          return;
        }
        if (feed.camera.objectDetectionEnabled) {
          this.streamType = "main";
          this.showToast("开启目标检测标注的画面仅支持主码流");
          return;
        }
        // 兜底：变更前已 RUNNING 的设备可能未注册子码流代理，重新 start 一次确保注册
        api.startCamera(feed.camera.id).catch(() => undefined);
      }
      feed.streamType = this.streamType;
      feed.meta = this.feedMeta(feed);
      this.ctrlPaused = false;
    },
    // 下拉框始终反映当前选中窗口的码流类型
    syncStreamTypeSelector() {
      const feed = this.visibleFeeds[this.selectedFeed];
      this.streamType = feed && feed.streamType === "sub" ? "sub" : "main";
    },
    changeLayout(count: number) {
      this.previewLayout = count;
      if (this.selectedFeed >= count) this.selectedFeed = 0;
      this.ensureStarted();
      this.syncStreamTypeSelector();
    },
    // 选择“满屏窗口”：按当前分屏布局（1/4/9/16 路）将视频宫格整体全屏；
    // 退出全屏（悬浮按钮 / Esc / 切回原始比例）后还原为原始比例
    onVideoFitChange() {
      if (this.videoFit === "cover") {
        const grid = this.$refs.videoGrid as HTMLElement | undefined;
        if (!grid || !grid.requestFullscreen) {
          this.videoFit = "contain";
          this.showToast("当前浏览器不支持全屏播放");
          return;
        }
        grid.requestFullscreen().catch(() => {
          this.videoFit = "contain";
          this.showToast("进入全屏失败");
        });
      } else if (document.fullscreenElement) {
        document.exitFullscreen().catch(() => undefined);
      }
    },
    onFullscreenChange() {
      this.gridFullscreen = document.fullscreenElement === this.$refs.videoGrid;
      if (!this.gridFullscreen && this.videoFit === "cover") {
        this.videoFit = "contain";
      }
    },
    exitGridFullscreen() {
      if (document.fullscreenElement) {
        document.exitFullscreen().catch(() => undefined);
      }
    },
    selectFeed(index: number) {
      this.selectedFeed = index;
      this.ctrlPaused = false;
      this.syncStreamTypeSelector();
    },
    // 单分屏时左右箭头按设备列表顺序切换当前窗口画面（循环）
    switchFeed(direction: number) {
      if (!this.cameraList.length) {
        this.showToast("暂无设备可切换");
        return;
      }
      const current = this.feeds[0] && this.feeds[0].camera;
      const currentIndex = current ? this.cameraList.findIndex(c => c.id === current.id) : -1;
      const total = this.cameraList.length;
      const nextIndex = (((currentIndex + direction) % total) + total) % total;
      const camera = this.cameraList[nextIndex];
      this.feeds.splice(0, 1, this.buildFeed(camera));
      this.selectedFeed = 0;
      this.ctrlPaused = false;
      this.recordHistory(camera);
      this.ensureStarted();
      this.syncStreamTypeSelector();
    },
    toggleRegion(region: RegionNode) {
      if (!this.selectedRegion || this.selectedRegion.fullPath !== region.fullPath) {
        this.selectedRegion = region;
        this.selectedCamera = null;
      }
      this.expandedRegions[region.fullPath] = !this.expandedRegions[region.fullPath];
    },
    // 选中的监控点放入当前选中窗口播放
    selectCamera(camera: any, region: RegionNode | null) {
      this.selectedRegion = region;
      this.selectedCamera = camera;
      const realCamera = camera.camera || this.cameraList.find(c => c.id === camera.code);
      if (!realCamera) return;
      const feed = this.buildFeed(realCamera);
      if (this.selectedFeed < this.feeds.length) {
        this.feeds.splice(this.selectedFeed, 1, feed);
      } else {
        this.feeds.push(feed);
      }
      this.ctrlPaused = false;
      this.recordHistory(realCamera);
      this.ensureStarted();
      this.syncStreamTypeSelector();
    },
    selectCameraById(id: string) {
      const camera = this.cameraList.find(c => c.id === id);
      if (!camera) {
        this.showToast("该设备已不存在");
        return;
      }
      this.selectCamera({ name: camera.name, code: camera.id, camera }, null);
    },
    // --- 监控点拖拽上屏 ---
    onCameraDragStart(event: DragEvent, camera: any) {
      if (!event.dataTransfer) return;
      event.dataTransfer.setData("text/plain", camera.code);
      event.dataTransfer.effectAllowed = "copy";
    },
    onTileDragOver(index: number) {
      this.dropHoverIndex = index;
    },
    onTileDragLeave(index: number) {
      if (this.dropHoverIndex === index) this.dropHoverIndex = -1;
    },
    onTileDrop(event: DragEvent, index: number) {
      event.preventDefault();
      this.dropHoverIndex = -1;
      const code = event.dataTransfer ? event.dataTransfer.getData("text/plain") : "";
      if (!code) return;
      const camera = this.cameraList.find((item) => item.id === code);
      if (!camera) {
        this.showToast("该设备已不存在");
        return;
      }
      this.playCameraAt(camera, index);
    },
    // 在指定窗口播放指定摄像头（拖拽上屏用；Vue 3 下数组下标赋值具备响应性）
    playCameraAt(camera: any, index: number) {
      this.feeds[index] = this.buildFeed(camera);
      this.selectedFeed = index;
      this.ctrlPaused = false;
      this.recordHistory(camera);
      this.ensureStarted();
      this.syncStreamTypeSelector();
    },
    // --- 场景保存 / 还原（localStorage 持久化） ---
    saveScene() {
      const cameraIds = this.visibleFeeds.map((feed) => (feed && feed.camera ? feed.camera.id : null));
      if (!cameraIds.some(Boolean)) {
        this.showToast("当前没有已播放的视频流，无法保存场景");
        return;
      }
      const count = cameraIds.filter(Boolean).length;
      const record = {
        id: `scene-${Date.now()}`,
        name: `场景 ${count} 路 · ${this.previewLayout} 分屏`,
        layout: this.previewLayout,
        cameraIds,
        time: formatTime(new Date())
      };
      this.sceneRecords = [record, ...this.sceneRecords].slice(0, SCENE_LIMIT);
      saveJson(SCENES_KEY, this.sceneRecords);
      this.showToast(`场景已保存（${count} 路视频流），在“场景”页签查看`);
    },
    restoreScene(record: any) {
      let missing = 0;
      this.feeds = (record.cameraIds || []).map((id: string | null) => {
        if (!id) return null;
        const camera = this.cameraList.find((item) => item.id === id);
        if (!camera) {
          missing += 1;
          return null;
        }
        return this.buildFeed(camera);
      });
      this.previewLayout = record.layout || Math.max(1, this.feeds.length);
      this.selectedFeed = 0;
      this.ctrlPaused = false;
      this.ensureStarted();
      this.syncStreamTypeSelector();
      this.showToast(missing ? `场景已还原，${missing} 路设备已不存在` : `场景已还原（${this.feeds.filter(Boolean).length} 路视频流）`);
    },
    // --- 场景改名 / 删除 ---
    startRenameScene(record: any) {
      this.renamingSceneId = record.id;
      this.renamingSceneName = record.name;
    },
    confirmRenameScene() {
      const name = this.renamingSceneName.trim();
      if (!name) {
        this.showToast("场景名称不能为空");
        return;
      }
      const record = this.sceneRecords.find((item: any) => item.id === this.renamingSceneId);
      if (record) {
        record.name = name;
        saveJson(SCENES_KEY, this.sceneRecords);
        this.showToast("场景名称已修改");
      }
      this.cancelRenameScene();
    },
    cancelRenameScene() {
      this.renamingSceneId = "";
      this.renamingSceneName = "";
    },
    removeScene(record: any) {
      if (!window.confirm(`确认删除场景「${record.name}」？`)) return;
      this.sceneRecords = this.sceneRecords.filter((item: any) => item.id !== record.id);
      saveJson(SCENES_KEY, this.sceneRecords);
      if (this.renamingSceneId === record.id) this.cancelRenameScene();
      this.showToast(`已删除场景：${record.name}`);
    },
    // --- 收藏 / 历史（localStorage 持久化） ---
    isFavorite(id: string): boolean {
      return this.favoriteIds.includes(id);
    },
    toggleFavorite(id: string) {
      if (this.isFavorite(id)) {
        this.favoriteIds = this.favoriteIds.filter(item => item !== id);
        this.showToast("已取消收藏");
      } else {
        this.favoriteIds = [...this.favoriteIds, id];
        this.showToast("已收藏");
      }
      saveJson(FAVORITES_KEY, this.favoriteIds);
    },
    recordHistory(camera: any) {
      const records = [
        { id: camera.id, name: camera.name, time: formatTime(new Date()) },
        ...this.historyRecords.filter(record => record.id !== camera.id)
      ].slice(0, HISTORY_LIMIT);
      this.historyRecords = records;
      saveJson(HISTORY_KEY, records);
    },
    // --- 播放控制（作用于当前选中窗口的 VideoPlayer） ---
    setPlayerRef(el: any, index: number) {
      if (el) {
        this.playerRefs[index] = el;
      } else {
        delete this.playerRefs[index];
      }
    },
    currentPlayer(): any {
      return this.playerRefs[this.selectedFeed] || null;
    },
    togglePlay() {
      const player = this.currentPlayer();
      if (!player) {
        this.showToast("当前窗口无视频流");
        return;
      }
      if (player.isPaused()) {
        player.resume();
        this.ctrlPaused = false;
      } else {
        player.pause();
        this.ctrlPaused = true;
      }
    },
    stopSelected() {
      const player = this.currentPlayer();
      if (!player) {
        this.showToast("当前窗口无视频流");
        return;
      }
      player.stop();
      this.ctrlPaused = true;
    },
    toggleSound() {
      const player = this.currentPlayer();
      if (!player) {
        this.showToast("当前窗口无视频流");
        return;
      }
      this.ctrlMuted = !this.ctrlMuted;
      player.setMuted(this.ctrlMuted);
      this.showToast(this.ctrlMuted ? "已静音" : "声音已打开");
    },
    snapshotSelected() {
      const player = this.currentPlayer();
      if (!player) {
        this.showToast("当前窗口无视频流");
        return;
      }
      // 抓图格式与命名规则来自视频参数设置
      const settings = loadPlayerSettings();
      const dataUrl = player.snapshot(settings.snapshotFormat === "PNG" ? "image/png" : "image/jpeg");
      if (!dataUrl) {
        this.showToast("抓拍失败：当前画面不可用");
        return;
      }
      const link = document.createElement("a");
      link.href = dataUrl;
      link.download = `${snapshotFileName(settings.namingRule, this.selectedFeedName)}.${settings.snapshotFormat === "PNG" ? "png" : "jpg"}`;
      link.click();
      this.showToast("抓拍图片已保存到下载目录");
    },
    toggleDigitalZoom() {
      const feed = this.visibleFeeds[this.selectedFeed];
      if (!feed || !feed.camera) {
        this.showToast("当前窗口无视频流");
        return;
      }
      feed.digitalZoom = !feed.digitalZoom;
      this.showToast(feed.digitalZoom ? "电子放大已开启，使用画面下方控制条缩放" : "电子放大已关闭");
    },
    // --- 云台控制 ---
    async ptz(command: PtzCommand, preset?: number) {
      if (this.ptzLocked) {
        this.showToast("云台已锁定，请先解锁");
        return;
      }
      const camera = this.ptzCamera;
      if (!camera) {
        this.showToast("请先选择一路真实摄像头");
        return;
      }
      if (!camera.ptzEnabled) {
        this.showToast("当前设备不支持云台控制");
        return;
      }
      try {
        await api.ptzControl(camera.id, { command, step: Number(this.ptzStep), preset });
      } catch (e: any) {
        this.showToast(`云台控制失败：${(e && e.message) || e}`);
      }
    },
    onZoomChange() {
      const delta = this.zoomLevel - this.prevZoomLevel;
      this.prevZoomLevel = this.zoomLevel;
      if (delta === 0) return;
      if (this.ptzLocked) {
        this.showToast("云台已锁定，请先解锁");
        return;
      }
      const camera = this.ptzCamera;
      if (!camera) {
        this.showToast("请先选择一路真实摄像头");
        return;
      }
      if (!camera.ptzEnabled) {
        this.showToast("当前设备不支持云台控制");
        return;
      }
      api.ptzControl(camera.id, { command: delta > 0 ? "zoom_in" : "zoom_out", step: Math.min(10, Math.abs(delta)) })
        .catch((e: any) => this.showToast(`变倍控制失败：${(e && e.message) || e}`));
    },
    // --- 预置点：保存/恢复当前云台控制参数（步长、变倍、变焦、光圈） ---
    addPreset() {
      const camera = this.ptzCamera;
      if (!camera || !camera.ptzEnabled) return;
      const list = [...(this.presetsByCamera[camera.id] || [])];
      let id = 1;
      while (list.some(preset => preset.id === id) && id < 255) id += 1;
      const preset: CameraPreset = {
        id,
        name: `预置点 ${id}`,
        params: {
          step: Number(this.ptzStep),
          zoom: this.zoomLevel,
          focus: this.focusLevel,
          iris: this.irisLevel
        }
      };
      list.push(preset);
      this.presetsByCamera = { ...this.presetsByCamera, [camera.id]: list };
      saveJson(PRESETS_KEY, this.presetsByCamera);
      this.showToast(`预置点「${preset.name}」已保存当前云台参数`);
    },
    async callPreset(preset: CameraPreset) {
      if (this.ptzLocked) {
        this.showToast("云台已锁定，请先解锁");
        return;
      }
      const camera = this.ptzCamera;
      if (!camera) {
        this.showToast("请先选择一路真实摄像头");
        return;
      }
      if (!camera.ptzEnabled) {
        this.showToast("当前设备不支持云台控制");
        return;
      }
      // 恢复保存的云台控制参数
      this.ptzStep = preset.params.step;
      this.zoomLevel = preset.params.zoom;
      this.prevZoomLevel = preset.params.zoom;
      this.focusLevel = preset.params.focus;
      this.irisLevel = preset.params.iris;
      try {
        await api.ptzControl(camera.id, { command: "preset_goto", preset: preset.id });
        this.showToast(`已调用预置点「${preset.name}」，云台参数已恢复`);
      } catch (e: any) {
        this.showToast(`已恢复预置点「${preset.name}」参数；设备预置点调用失败：${(e && e.message) || e}`);
      }
    },
    removePreset(preset: CameraPreset) {
      const camera = this.ptzCamera;
      if (!camera) return;
      const list = (this.presetsByCamera[camera.id] || []).filter(item => item.id !== preset.id);
      this.presetsByCamera = { ...this.presetsByCamera, [camera.id]: list };
      saveJson(PRESETS_KEY, this.presetsByCamera);
      this.showToast(`预置点「${preset.name}」已删除`);
    }
  }
});
</script>
