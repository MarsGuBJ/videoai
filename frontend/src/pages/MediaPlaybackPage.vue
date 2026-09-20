<template>
  <section class="content review-wide media-playback-page">
    <div class="review-titlebar"><div><h1>录像回放</h1><p>按空间、设备与时间快速检索历史录像，支持时间轴定位、同步回放、分段回放和录像下载</p></div><div class="segmented"><button class="btn" @click="openRecordDownload">录像下载</button><button class="btn primary" @click="goLivePreview">切换实况</button></div></div>
    <div class="media-console-grid playback">
      <aside v-show="showSider" class="panel media-resource-panel">
        <input class="input" placeholder="搜索监控点名称/IP" aria-label="搜索监控点名称或IP" v-model="searchKeyword" />
        <div class="media-playback-tree"><div class="media-panel-head"><b>录像资源</b><span class="hint-text">区域 / 监控点 · 共 {{ totalCameraCount }} 台设备</span></div><div class="media-playback-tree-list exact-tree-list"><div v-for="region in displayRegions" :key="region.fullPath"><button class="exact-tree-area-row" :class="{ active: selectedRegion && selectedRegion.fullPath === region.fullPath }" :style="region.child ? 'padding-left:24px;' : ''" @click="toggleRegion(region)"><span>{{ isRegionExpanded(region) ? '⌄' : '›' }} {{ region.name }}</span><span>{{ regionCount(region) }} 台设备</span></button><div v-if="isRegionExpanded(region)" class="exact-tree-children"><button v-for="camera in camerasForRegion(region)" :key="camera.code" class="exact-tree-device" :class="{ active: selectedCamera && selectedCamera.code === camera.code }" @click="selectCamera(camera, region)"><span>{{ camera.name }}</span><span>{{ camera.status }}</span></button></div></div><div v-if="!displayRegions.length" style="padding:12px;color:#888;">{{ searchKeyword ? '无匹配监控点' : '暂无录像资源，请先在设备管理中添加设备' }}</div></div></div>
        <div class="media-record-query"><div class="media-resource-tabs" style="margin-bottom:0;"></div><label>开始时间<input class="input" type="datetime-local" v-model="queryStart" /></label><label>结束时间<input class="input" type="datetime-local" v-model="queryEnd" /></label><button class="btn primary" :disabled="searching" @click="searchRecordings">{{ searching ? '查询中…' : '录像查询' }}</button><ul v-if="segments.length" class="media-plan-list"><li :class="{ active: !!activeSegment }" style="cursor:pointer;" @click="playMergedResult"><b>{{ formatSegmentTime(segments[0].startTime) }} ~ {{ formatSegmentTime(segments[segments.length - 1].endTime, true) }}</b><span>{{ segments[0].cameraName || (selectedCamera && selectedCamera.name) || '' }}</span></li></ul><p v-else-if="searchError" class="hint-text">{{ searchError }}</p><p v-else-if="searched && !searching" class="hint-text">该时段无录像</p></div>
      </aside>
      <section class="panel media-stage-panel">
        <div class="media-playback-player playback-player-fill">
          <playback-player
            ref="playbackPlayerShell"
            :stream-url="playbackStreamUrl"
            :title="playbackCameraName"
            :playing="playbackPlaying"
            :speed="Number(speed)"
            :current-ms="currentPlaybackMs"
            :range-start-ms="rangeStartMs"
            :range-end-ms="rangeEndMs"
            :segments="timelineSegments"
            :muted="muted"
            :show-sidebar="showSider"
            :mask-text="playbackMaskText"
            @seek="onPlayerSeek"
            @toggle-play="togglePlayback"
            @speed-step="onSpeedStep"
            @speed-reset="onSpeedReset"
            @mute-toggle="toggleMute"
            @capture="capturePlayback"
            @close="closePlayback"
            @toggle-sidebar="showSider = !showSider"
          ></playback-player>
        </div>
      </section>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { api } from "../api";
import type { RecordingSegment, RegionTreeNode } from "../api";
import { deviceStatusLabel, deviceStatusRank } from "../utils/device-status";
import { flattenRegionTree, loadRegionTree, normalizePath, type RegionNode } from "../utils/regions";
import PlaybackPlayer from "../components/playback/PlaybackPlayer.vue";
import type { TimelineSegment } from "../components/playback/PlaybackTimeline.vue";

// 区域节点来自后端区域树（sortOrder 顺序）；设备占用的路径不在树中时（含「未分配」）按前缀补齐到末尾。
// count 口径：所有节点均统计整个子树的设备合计（父节点仅显示统计数字，子节点的设备不并入父节点）。
function regionsFromTree(tree: RegionTreeNode[] | null, regionCameras: Record<string, any[]>): RegionNode[] {
  const subtreeCount = (path: string) =>
    Object.keys(regionCameras)
      .filter((p) => p === path || p.startsWith(path + " / "))
      .reduce((sum, p) => sum + regionCameras[p].length, 0);
  const regions: RegionNode[] = (tree ? flattenRegionTree(tree) : []).map((item) => ({
    name: item.name,
    fullPath: item.fullPath,
    child: item.depth > 0,
    count: subtreeCount(item.fullPath)
  }));
  const seen = new Set(regions.map((region) => region.fullPath));
  const missing: string[] = [];
  for (const path of Object.keys(regionCameras)) {
    let prefix = "";
    for (const segment of path.split(" / ")) {
      prefix = prefix ? `${prefix} / ${segment}` : segment;
      if (!seen.has(prefix) && !missing.includes(prefix)) missing.push(prefix);
    }
  }
  missing.sort((a, b) => a.localeCompare(b, "zh"));
  missing.forEach((fullPath) => {
    seen.add(fullPath);
    const segments = fullPath.split(" / ");
    regions.push({
      name: segments[segments.length - 1],
      fullPath,
      child: segments.length > 1,
      count: subtreeCount(fullPath)
    });
  });
  return regions;
}

/** 拉流状态排序权重：拉流中在前，其后已停止/停用/未启动。 */
function statusRank(status: string): number {
  const value = (status || "").toUpperCase();
  if (value === "RUNNING") return 0;
  if (value === "STOPPED") return 1;
  if (value === "OFFLINE") return 1;
  if (value === "DISABLED") return 2;
  return 3;
}

function pad2(value: number): string {
  return String(value).padStart(2, "0");
}

// datetime-local 输入与后端录像接口的时间均按北京时间（本地时区）解析与格式化
function toLocalDateTimeValue(date: Date): string {
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}T${pad2(date.getHours())}:${pad2(date.getMinutes())}`;
}

function toLocalIsoSeconds(ms: number): string {
  const date = new Date(ms);
  return `${toLocalDateTimeValue(date)}:${pad2(date.getSeconds())}`;
}

function parseLocalMs(value?: string): number {
  const ms = value ? new Date(value).getTime() : NaN;
  return Number.isNaN(ms) ? 0 : ms;
}

// 参考站（iSecure Center）回放工具栏倍速档位
const SPEED_LEVELS = [0.25, 0.5, 1, 2, 4];

export default defineComponent({
  name: "MediaPlaybackPage",
  components: { PlaybackPlayer },
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  inject: {
    openModal: { from: "openModal", default: (type: string, item?: any) => {} },
    setRoute: { from: "setRoute", default: (route: string, options?: any) => {} },
    showToast: { from: "showToast", default: (m: string) => {} }
  },
  data() {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    return {
      speed: 1 as number,
      showSider: true,
      muted: true,
      queryStart: toLocalDateTimeValue(today),
      queryEnd: toLocalDateTimeValue(now),
      searching: false,
      searched: false,
      searchError: "",
      searchKeyword: "",
      segments: [] as RecordingSegment[],
      activeSegment: null as RecordingSegment | null,
      playbackPlaying: false,
      playbackBusy: false,
      playbackCurrent: 0,
      playbackDuration: 0,
      playbackTimer: null as number | null,
      scrubbing: false,
      streamBaseMs: 0,
      streamStartedAt: 0,
      selectedCamera: null as any,
      selectedRegion: null as RegionNode | null,
      playbackStreamUrl: undefined as string | undefined,
      regions: [] as RegionNode[],
      regionCameras: {} as Record<string, any[]>,
      expandedRegions: {} as Record<string, boolean>
    };
  },
  computed: {
    // 搜索时仅显示子树内有命中设备的区域节点
    displayRegions(): RegionNode[] {
      if (!this.searchKeyword.trim()) return this.regions;
      return this.regions.filter((region) => this.regionCount(region) > 0);
    },
    // 全部设备总数（面板头部右侧展示）
    totalCameraCount(): number {
      return (Object.values(this.regionCameras) as any[][]).reduce((sum, list) => sum + list.length, 0);
    },
    // 查询结果合并为一条：整体起点 = 首段开始时间，整体终点 = 末段结束时间
    rangeStartMs(): number {
      return this.segments.length ? parseLocalMs(this.segments[0].startTime) : 0;
    },
    rangeEndMs(): number {
      return this.segments.length ? parseLocalMs(this.segments[this.segments.length - 1].endTime) : 0;
    },
    // 当前回放位置 ≈ 合并结果起点 + 全局进度秒数
    currentPlaybackMs(): number {
      return this.segments.length ? this.rangeStartMs + this.playbackCurrent * 1000 : 0;
    },
    playbackCameraName(): string {
      return this.selectedCamera ? this.selectedCamera.name : "";
    },
    playbackMaskText(): string {
      if (this.playbackStreamUrl) return "";
      if (!this.selectedCamera) return "选择左侧摄像头并查询录像，点击录像结果开始回放";
      if (!this.segments.length) return "该时段无录像";
      return "点击左侧录像结果开始回放";
    },
    // 时间轴录像段：查询结果直接映射为 {startMs, endMs}
    timelineSegments(): TimelineSegment[] {
      return this.segments.map((segment) => ({
        startMs: parseLocalMs(segment.startTime),
        endMs: parseLocalMs(segment.endTime)
      }));
    }
  },
  mounted() {
    this.loadCameras();
  },
  watch: {
    // 设备管理页增删改设备或新增区域后，刷新录像资源树
    "state.camerasVersion"() {
      this.loadCameras();
    }
  },
  methods: {
    async loadCameras() {
      let tree: RegionTreeNode[] | null = null;
      try {
        tree = await loadRegionTree();
      } catch {
        // 区域接口不可用时按设备 area 兜底聚合
      }
      try {
        const cameras = await api.cameras();
        this.applyCameras(cameras || [], tree);
        this.playPendingPlayback();
      } catch (error) {
        // 后端不可用时保留当前树
      }
    },
    // 录像资源树的区域顺序来自后端区域树（utils/regions.ts loadRegionTree），
    // 设备按 area 全路径（" / " 连接、分段 trim）挂到对应区域节点下
    applyCameras(cameras: any[], tree: RegionTreeNode[] | null) {
      const regionCameras: Record<string, any[]> = {};
      for (const cam of cameras) {
        // 与区域树 fullPath 口径一致，否则展开区域取不到设备
        const areaPath = normalizePath(cam.area) || "未分配";
        if (!regionCameras[areaPath]) regionCameras[areaPath] = [];
        regionCameras[areaPath].push({
          id: cam.id,
          name: cam.name,
          code: cam.id,
          ip: cam.ip,
          type: cam.protocol || cam.streamApp || "IPC",
          status: deviceStatusLabel(cam),
          onlineStatus: cam.onlineStatus,
          statusRaw: cam.status,
          streamName: cam.streamName,
          image: this.store.img.car,
          areaPath
        });
      }
      for (const list of Object.values(regionCameras)) {
        // 先按设备可达性（在线→未探测→离线），再按拉流状态，最后按名称
        list.sort((a, b) => deviceStatusRank(a) - deviceStatusRank(b)
          || statusRank(a.statusRaw) - statusRank(b.statusRaw)
          || a.name.localeCompare(b.name, "zh"));
      }
      const regions = regionsFromTree(tree, regionCameras);
      const expanded: Record<string, boolean> = {};
      regions.forEach((region, index) => {
        expanded[region.fullPath] = index === 0;
      });
      this.regionCameras = regionCameras;
      this.regions = regions;
      this.expandedRegions = expanded;
      this.selectedRegion = null;
      this.selectedCamera = null;
    },
    // 每个区域节点只显示直接挂载的设备，子区域的设备不并入父节点（父节点仅显示子树合计数）；
    // 搜索关键字按名称/IP 过滤
    camerasForRegion(region: RegionNode): any[] {
      const keyword = this.searchKeyword.trim().toLowerCase();
      const result: any[] = this.regionCameras[region.fullPath] || [];
      if (!keyword) return result;
      return result.filter((camera) =>
        camera.name.toLowerCase().includes(keyword) ||
        String(camera.ip || "").toLowerCase().includes(keyword)
      );
    },
    // 节点设备数 = 整个子树的设备合计（含所有子孙区域）；搜索时统计子树内命中数
    regionCount(region: RegionNode): number {
      const keyword = this.searchKeyword.trim().toLowerCase();
      let total = 0;
      for (const path of Object.keys(this.regionCameras)) {
        if (path !== region.fullPath && !path.startsWith(region.fullPath + " / ")) continue;
        const list = this.regionCameras[path];
        total += keyword
          ? list.filter((camera) =>
              camera.name.toLowerCase().includes(keyword) ||
              String(camera.ip || "").toLowerCase().includes(keyword)
            ).length
          : list.length;
      }
      return total;
    },
    // 搜索时资源树节点全部展开，便于直接看到命中的监控点
    isRegionExpanded(region: RegionNode): boolean {
      return !!this.expandedRegions[region.fullPath] || !!this.searchKeyword.trim();
    },
    // 即时回放「切至历史录像」带入的回放参数（state.playbackQuery）：
    // 选中设备 → 按即时回放的时间段检索 → 从同一位置直接播放该录像片段
    async playPendingPlayback() {
      const pending = this.state.playbackQuery;
      if (!pending || !pending.cameraId) return;
      this.state.playbackQuery = null;
      let target: any = null;
      for (const path of Object.keys(this.regionCameras)) {
        target = this.regionCameras[path].find((camera: any) => camera.id === pending.cameraId) || target;
      }
      if (!target) {
        this.showToast("该设备已不存在");
        return;
      }
      // 查询框同步显示带入的时间段（datetime-local 精度到分钟，仅作展示）
      this.queryStart = toLocalDateTimeValue(new Date(pending.startMs));
      this.queryEnd = toLocalDateTimeValue(new Date(pending.endMs));
      const region = this.regions.find(r => r.fullPath === target.areaPath) || null;
      this.selectedRegion = region;
      this.selectedCamera = target;
      if (region) this.expandedRegions[region.fullPath] = true;
      this.resetPlayback();
      this.searching = true;
      this.searched = false;
      this.searchError = "";
      this.segments = [];
      try {
        // 检索用秒级精度的原始时间段，避免 datetime-local 分钟精度截断漏段
        const result = await api.searchRecordings({ cameraId: target.id, startTime: toLocalIsoSeconds(pending.startMs), endTime: toLocalIsoSeconds(pending.endMs) });
        this.segments = ((result && result.data) || []).slice().sort((a, b) => parseLocalMs(a.startTime) - parseLocalMs(b.endTime));
        this.searched = true;
        if (!this.segments.length) {
          this.showToast("该时段无录像");
          return;
        }
        // 合并结果整体回放：从带入的回放起点开始（全局进度，段间自动接续）
        this.playbackDuration = Math.max(0, Math.round((this.rangeEndMs - this.rangeStartMs) / 1000));
        const offset = Math.max(0, Math.round((pending.startMs - this.rangeStartMs) / 1000));
        this.startPlaybackAt(offset);
      } catch (error) {
        // 摄像头不存在（404）/未绑定 NVR（400）等，直接展示后端错误消息
        this.searched = true;
        this.searchError = error instanceof Error ? error.message : String(error);
        this.showToast(`录像查询失败：${this.searchError}`);
      } finally {
        this.searching = false;
      }
    },
    stopProgressTimer() {
      if (this.playbackTimer) window.clearInterval(this.playbackTimer);
      this.playbackTimer = null;
    },
    startProgressTimer() {
      this.stopProgressTimer();
      this.playbackTimer = window.setInterval(() => {
        if (!this.playbackPlaying || this.scrubbing) return;
        // 倍速流进度 = 起流位置 + 墙钟秒数 × 倍速（全局进度，相对合并结果起点）
        const elapsed = Math.floor(((Date.now() - this.streamStartedAt) / 1000) * Number(this.speed));
        const positionMs = this.streamBaseMs + elapsed * 1000;
        this.playbackCurrent = Math.max(0, Math.min(this.playbackDuration, Math.round((positionMs - this.rangeStartMs) / 1000)));
        if (this.activeSegment && positionMs >= parseLocalMs(this.activeSegment.endTime)) {
          // 段尾自动接续下一段（重新起流，全局进度连续）；无下一段才停止
          const currentIndex = this.segments.indexOf(this.activeSegment);
          const next = currentIndex >= 0 && currentIndex + 1 < this.segments.length ? this.segments[currentIndex + 1] : null;
          if (next) {
            this.startPlaybackAt(Math.round((parseLocalMs(next.startTime) - this.rangeStartMs) / 1000));
          } else {
            this.playbackCurrent = this.playbackDuration;
            this.playbackPlaying = false;
            this.stopProgressTimer();
          }
        }
      }, 1000);
    },
    resetPlayback() {
      this.stopProgressTimer();
      this.playbackPlaying = false;
      this.playbackBusy = false;
      this.playbackCurrent = 0;
      this.playbackDuration = 0;
      this.activeSegment = null;
      this.playbackStreamUrl = undefined;
    },
    async searchRecordings() {
      if (!this.selectedCamera) {
        this.showToast("请先在左侧选择摄像头");
        return;
      }
      if (!this.queryStart || !this.queryEnd) {
        this.showToast("请选择查询的开始与结束时间");
        return;
      }
      if (parseLocalMs(this.queryStart) >= parseLocalMs(this.queryEnd)) {
        this.showToast("开始时间必须早于结束时间");
        return;
      }
      this.searching = true;
      this.searched = false;
      this.searchError = "";
      this.segments = [];
      try {
        const result = await api.searchRecordings({ cameraId: this.selectedCamera.id, startTime: this.queryStart, endTime: this.queryEnd });
        // 多段录像按开始时间排序后合并展示为一条结果
        this.segments = ((result && result.data) || []).slice().sort((a, b) => parseLocalMs(a.startTime) - parseLocalMs(b.startTime));
        this.searched = true;
        if (!this.segments.length) this.showToast("该时段无录像");
      } catch (error) {
        // 摄像头不存在（404）/未绑定 NVR（400）等，直接展示后端错误消息
        this.searched = true;
        this.searchError = error instanceof Error ? error.message : String(error);
        this.showToast(`录像查询失败：${this.searchError}`);
      } finally {
        this.searching = false;
      }
    },
    // 查询结果合并为一条（开始时间 ~ 结束时间），点击从起点连续回放，段间自动接续
    playMergedResult() {
      if (!this.segments.length) return;
      this.playbackDuration = Math.max(0, Math.round((this.rangeEndMs - this.rangeStartMs) / 1000));
      this.playbackCurrent = 0;
      this.startPlaybackAt(0);
    },
    // 全局进度（相对合并结果起点）定位录像段：优先覆盖该时刻的段，时段空隙跳到其后一段
    locateSegment(ms: number): { segment: RecordingSegment; localOffset: number } | null {
      for (const segment of this.segments) {
        const startMs = parseLocalMs(segment.startTime);
        const endMs = parseLocalMs(segment.endTime);
        if (ms >= startMs && ms < endMs) {
          return { segment, localOffset: Math.round((ms - startMs) / 1000) };
        }
        if (ms < startMs) return { segment, localOffset: 0 };
      }
      const last = this.segments[this.segments.length - 1];
      if (!last) return null;
      const lastDuration = Math.max(0, Math.round((parseLocalMs(last.endTime) - parseLocalMs(last.startTime)) / 1000));
      return { segment: last, localOffset: Math.max(lastDuration - 1, 0) };
    },
    // NVR 回放是连续推送流：定位/快进/拖动进度 = 以「合并结果起点 + 全局偏移」对应的录像时刻为新起点重新起流（段内 clamp），倍速随起流生效
    async startPlaybackAt(globalOffsetSeconds: number) {
      if (!this.segments.length || !this.selectedCamera || this.playbackBusy) return;
      const offset = Math.max(0, Math.min(Math.max(this.playbackDuration - 1, 0), Math.round(globalOffsetSeconds)));
      const located = this.locateSegment(this.rangeStartMs + offset * 1000);
      if (!located) return;
      this.activeSegment = located.segment;
      const startMs = parseLocalMs(located.segment.startTime) + located.localOffset * 1000;
      this.playbackBusy = true;
      this.stopProgressTimer();
      this.playbackPlaying = false;
      try {
        const result = await api.startRecordingStream({
          cameraId: this.selectedCamera.id,
          startTime: toLocalIsoSeconds(startMs),
          endTime: located.segment.endTime,
          speed: Number(this.speed)
        });
        this.streamBaseMs = startMs;
        this.streamStartedAt = Date.now();
        this.playbackCurrent = Math.round((startMs - this.rangeStartMs) / 1000);
        this.playbackPlaying = true;
        this.startProgressTimer();
        if (this.playbackStreamUrl === result.url) {
          // URL 相同不会触发播放器组件的 watch，先卸载再在下一帧重建流
          this.playbackStreamUrl = undefined;
          this.$nextTick(() => {
            this.playbackStreamUrl = result.url;
          });
        } else {
          this.playbackStreamUrl = result.url;
        }
      } catch (error) {
        this.showToast(`回放流启动失败：${error instanceof Error ? error.message : error}`);
      } finally {
        this.playbackBusy = false;
      }
    },
    // ---- 播放器组件事件 ----
    // 时间轴 / 时间选择框定位：绝对时刻 → 全局偏移重新起流
    onPlayerSeek(ms: number) {
      if (!this.segments.length) {
        this.showToast("请先查询录像");
        return;
      }
      this.startPlaybackAt(Math.round((ms - this.rangeStartMs) / 1000));
    },
    togglePlayback() {
      if (!this.activeSegment) {
        this.showToast("请先查询并点击左侧录像结果");
        return;
      }
      if (this.playbackPlaying) {
        // 暂停即停流，进度停留在当前位置
        this.stopStreamOnly();
        this.playbackPlaying = false;
        this.stopProgressTimer();
        return;
      }
      if (this.playbackCurrent >= this.playbackDuration) {
        this.startPlaybackAt(0);
        return;
      }
      // 连续推送流无法从暂停点续播，从当前位置重新起流
      this.startPlaybackAt(this.playbackCurrent);
    },
    // 仅停流（暂停）：保留进度与段信息
    stopStreamOnly() {
      this.playbackStreamUrl = undefined;
    },
    // 倍速档位步进（参考站 JS_Fast / JS_Slow：每击一档）
    onSpeedStep(direction: number) {
      const index = SPEED_LEVELS.indexOf(Number(this.speed));
      const next = Math.max(0, Math.min(SPEED_LEVELS.length - 1, (index < 0 ? 2 : index) + direction));
      const speed = SPEED_LEVELS[next];
      if (speed === Number(this.speed)) return;
      this.speed = speed;
      if (this.activeSegment && this.playbackPlaying) {
        this.startPlaybackAt(this.playbackCurrent);
      }
    },
    // 倍速文字点击 = 恢复默认速度（1×）
    onSpeedReset() {
      if (Number(this.speed) === 1) return;
      this.speed = 1;
      if (this.activeSegment && this.playbackPlaying) {
        this.startPlaybackAt(this.playbackCurrent);
      }
    },
    toggleMute() {
      this.muted = !this.muted;
      const shell = (this.$refs as any).playbackPlayerShell;
      const player = shell?.videoInstance?.();
      if (player) player.setMuted(this.muted);
    },
    // 抓图：截取当前画面并下载
    capturePlayback() {
      const shell = (this.$refs as any).playbackPlayerShell;
      const player = shell?.videoInstance?.();
      const dataUrl = player?.snapshot?.();
      if (!dataUrl) {
        this.showToast("暂无可抓取的画面");
        return;
      }
      const link = document.createElement("a");
      const date = new Date(this.currentPlaybackMs);
      const name = this.selectedCamera ? this.selectedCamera.name : "回放";
      link.download = `${name}_${date.getFullYear()}${pad2(date.getMonth() + 1)}${pad2(date.getDate())}_${pad2(date.getHours())}${pad2(date.getMinutes())}${pad2(date.getSeconds())}.jpg`;
      link.href = dataUrl;
      link.click();
      this.showToast("抓图成功");
    },
    // 全部关闭：停止回放并清空进度
    closePlayback() {
      this.resetPlayback();
    },
    toggleRegion(region: RegionNode) {
      if (!this.selectedRegion || this.selectedRegion.fullPath !== region.fullPath) {
        this.selectedRegion = region;
        this.selectedCamera = null;
      }
      this.expandedRegions[region.fullPath] = !this.expandedRegions[region.fullPath];
    },
    selectCamera(camera: any, region: RegionNode) {
      this.selectedRegion = region;
      this.selectedCamera = camera;
      this.segments = [];
      this.searched = false;
      this.searchError = "";
      this.resetPlayback();
    },
    // 录像段时间显示为北京时间；endTime 与 startTime 同日时只显示时分秒
    formatSegmentTime(value?: string, timeOnly = false): string {
      const ms = parseLocalMs(value);
      if (!ms) return "";
      const date = new Date(ms);
      const time = `${pad2(date.getHours())}:${pad2(date.getMinutes())}:${pad2(date.getSeconds())}`;
      if (timeOnly) return time;
      return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())} ${time}`;
    },
    // 切换实况：正在回放时把当前摄像头带到实时预览页直接上屏播放
    goLivePreview() {
      const playing = !!(this.activeSegment && this.playbackStreamUrl && this.selectedCamera);
      this.setRoute("mediaPreview", playing ? { playCameraId: this.selectedCamera.id } : {});
    },
    openRecordDownload() {
      if (!this.selectedCamera) {
        this.showToast("请先在左侧选择摄像头");
        return;
      }
      // 查询结果已合并为一条：默认导出整个合并时段，否则用查询时段
      const startTime = this.rangeStartMs ? toLocalIsoSeconds(this.rangeStartMs) : this.queryStart;
      const endTime = this.rangeEndMs ? toLocalIsoSeconds(this.rangeEndMs) : this.queryEnd;
      this.openModal("recordDownload", { camera: this.selectedCamera, startTime, endTime });
    }
  },
  beforeUnmount() {
    this.stopProgressTimer();
  }
});
</script>

<style scoped>
/* 复刻参考站：播放器铺满右侧舞台（视频区 + 时间轴 + 工具栏整体填充） */
.media-playback-player.playback-player-fill {
  display: flex;
  min-width: 0;
  min-height: 480px;
  background: #262626;
}

.media-playback-player.playback-player-fill > :deep(.playback-player-shell) {
  flex: 1;
}
</style>
