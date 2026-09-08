<template>
  <section class="content review-wide media-playback-page">
    <div class="review-titlebar"><div><h1>录像回放</h1><p>按空间、设备与时间快速检索历史录像，支持时间轴定位、同步回放、分段回放和录像下载</p></div><div class="segmented"><button class="btn" @click="openRecordDownload">录像下载</button><button class="btn primary" @click="setRoute('mediaPreview')">切换实况</button></div></div>
    <div class="media-console-grid playback">
      <aside class="panel media-resource-panel">
        <div class="media-playback-tree"><div class="media-panel-head"><b>录像资源</b><span class="hint-text">区域 / 监控点</span></div><div class="media-playback-tree-list exact-tree-list"><div v-for="region in regions" :key="region.fullPath"><button class="exact-tree-area-row" :class="{ active: selectedRegion && selectedRegion.fullPath === region.fullPath }" :style="region.child ? 'padding-left:24px;' : ''" @click="toggleRegion(region)"><span>{{ expandedRegions[region.fullPath] ? '⌄' : '›' }} {{ region.name }}</span><span>{{ region.count }} 台设备</span></button><div v-if="expandedRegions[region.fullPath]" class="exact-tree-children"><button v-for="camera in camerasForRegion(region)" :key="camera.code" class="exact-tree-device" :class="{ active: selectedCamera && selectedCamera.code === camera.code }" @click="selectCamera(camera, region)"><span>{{ camera.name }}</span><span>{{ camera.status }}</span></button></div></div><div v-if="!regions.length" style="padding:12px;color:#888;">暂无录像资源，请先在设备管理中添加设备</div></div></div>
        <div class="media-record-query"><div class="media-resource-tabs" style="margin-bottom:0;"></div><label>开始时间<input class="input" type="datetime-local" v-model="queryStart" /></label><label>结束时间<input class="input" type="datetime-local" v-model="queryEnd" /></label><button class="btn primary" :disabled="searching" @click="searchRecordings">{{ searching ? '查询中…' : '录像查询' }}</button><ul v-if="segments.length" class="media-plan-list"><li v-for="segment in segments" :key="segment.recordingId || segment.startTime" :class="{ active: activeSegment === segment }" style="cursor:pointer;" @click="playSegment(segment)"><b>{{ formatSegmentTime(segment.startTime) }} ~ {{ formatSegmentTime(segment.endTime, true) }}</b><span>{{ segment.cameraName || (selectedCamera && selectedCamera.name) || '' }}</span></li></ul><p v-else-if="searchError" class="hint-text">{{ searchError }}</p><p v-else-if="searched && !searching" class="hint-text">该时段无录像</p></div>
      </aside>
      <section class="panel media-stage-panel">
        <div class="media-playback-player">
          <video-player v-if="playbackStreamUrl" ref="playbackPlayer" :url="playbackStreamUrl"></video-player>
          <div v-else style="display:flex;align-items:center;justify-content:center;height:100%;color:#98a2b3;font-size:13px;">选择左侧摄像头并查询录像，点击录像段开始回放</div>
          <div class="media-playback-player-title">录像回放 · {{ playbackTitle }}</div>
          <div class="media-playback-overlay-controls">
            <div class="media-playback-button-group" aria-label="录像回放控制">
              <button class="media-playback-step" type="button" title="跳到开始" aria-label="跳到开始" @click="seekPlayback(-playbackDuration)">|◀</button>
              <button class="media-playback-step" type="button" title="后退10秒" aria-label="后退10秒" @click="seekPlayback(-10)">◀</button>
              <button class="media-playback-toggle active" type="button" title="播放或暂停" :aria-label="playbackPlaying ? '暂停' : '播放'" @click="togglePlayback">{{ playbackPlaying ? 'Ⅱ' : '▶' }}</button>
              <button class="media-playback-step" type="button" title="前进10秒" aria-label="前进10秒" @click="seekPlayback(10)">▶</button>
              <button class="media-playback-step" type="button" title="跳到结束" aria-label="跳到结束" @click="seekPlayback(playbackDuration)">▶|</button>
            </div>
            <span>{{ formatClock(segmentStartMs) }}</span>
            <input class="media-playback-progress" type="range" min="0" :max="playbackDuration" step="1" v-model.number="playbackCurrent" :disabled="!activeSegment" aria-label="录像播放进度" @pointerdown="scrubbing = true" @pointerup="scrubbing = false" @change="commitProgress" />
            <span>{{ formatClock(segmentEndMs) }}</span>
            <select class="media-playback-rate" v-model="speed" title="回放倍速（NVR 实测支持 0.25~32 倍）" aria-label="播放倍速" @change="onSpeedChange"><option v-for="option in SPEED_OPTIONS" :key="option" :value="String(option)">{{ option }}x</option></select>
          </div>
        </div>
      </section>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { api } from "../api";
import type { RecordingSegment } from "../api";
import { buildRegionTree, loadCustomRegions, normalizePath, type RegionNode } from "../utils/regions";
import VideoPlayer from "../components/VideoPlayer.vue";

function statusLabel(status: string): string {
  const value = (status || "").toUpperCase();
  if (value === "RUNNING") return "在线";
  if (value === "STOPPED") return "离线";
  if (value === "DISABLED") return "停用";
  return "未成功连接";
}

// 排序权重：在线在前，其后离线/停用/未连接，同状态按名称排序
function statusRank(status: string): number {
  const value = (status || "").toUpperCase();
  if (value === "RUNNING") return 0;
  if (value === "STOPPED") return 1;
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

// 现场海康 NVR（10.10.7.252/253）回放倍速实测支持 0.25~32 倍
const SPEED_OPTIONS = [0.25, 0.5, 1, 2, 4, 8, 16, 32];

export default defineComponent({
  name: "MediaPlaybackPage",
  components: { VideoPlayer },
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
      speed: "1",
      SPEED_OPTIONS,
      queryStart: toLocalDateTimeValue(today),
      queryEnd: toLocalDateTimeValue(now),
      searching: false,
      searched: false,
      searchError: "",
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
    segmentStartMs(): number {
      return this.activeSegment ? parseLocalMs(this.activeSegment.startTime) : 0;
    },
    segmentEndMs(): number {
      return this.activeSegment ? parseLocalMs(this.activeSegment.endTime) : 0;
    },
    // 当前回放位置 ≈ 起流时刻 + 已播放墙钟秒数 × 倍速
    currentPlaybackMs(): number {
      return this.activeSegment ? this.segmentStartMs + this.playbackCurrent * 1000 : 0;
    },
    playbackTitle(): string {
      if (!this.selectedCamera) return "未选择摄像头";
      if (!this.activeSegment) return this.selectedCamera.name;
      return `${this.selectedCamera.name} · ${this.formatClock(this.currentPlaybackMs)}`;
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
      try {
        const cameras = await api.cameras();
        this.applyCameras(cameras || []);
      } catch (error) {
        // 后端不可用时保留当前树
      }
    },
    // 录像资源树与设备管理页共用同一套区域聚合逻辑：
    // 设备 area 按 "/" 分层 + localStorage 自定义区域（utils/regions.ts）
    applyCameras(cameras: any[]) {
      const regionCameras: Record<string, any[]> = {};
      for (const cam of cameras) {
        // 与 buildRegionTree 的 fullPath 口径一致（" / " 连接、分段 trim），否则展开区域取不到设备
        const areaPath = normalizePath(cam.area) || "未分配";
        if (!regionCameras[areaPath]) regionCameras[areaPath] = [];
        regionCameras[areaPath].push({
          id: cam.id,
          name: cam.name,
          code: cam.id,
          type: cam.protocol || cam.streamApp || "IPC",
          status: statusLabel(cam.status),
          statusRaw: cam.status,
          streamName: cam.streamName,
          image: this.store.img.car,
          areaPath
        });
      }
      for (const list of Object.values(regionCameras)) {
        list.sort((a, b) => statusRank(a.statusRaw) - statusRank(b.statusRaw) || a.name.localeCompare(b.name, "zh"));
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
    },
    // 顶层区域展开时显示其全部子孙区域的设备，与 count 口径一致
    camerasForRegion(region: RegionNode): any[] {
      const result: any[] = [];
      for (const path of Object.keys(this.regionCameras)) {
        if (path === region.fullPath || path.startsWith(region.fullPath + " / ")) {
          result.push(...this.regionCameras[path]);
        }
      }
      return result;
    },
    formatClock(ms: number): string {
      if (!ms) return "--:--:--";
      const date = new Date(ms);
      return `${pad2(date.getHours())}:${pad2(date.getMinutes())}:${pad2(date.getSeconds())}`;
    },
    stopProgressTimer() {
      if (this.playbackTimer) window.clearInterval(this.playbackTimer);
      this.playbackTimer = null;
    },
    startProgressTimer() {
      this.stopProgressTimer();
      this.playbackTimer = window.setInterval(() => {
        if (!this.playbackPlaying || this.scrubbing) return;
        // 倍速流进度 = 起流位置 + 墙钟秒数 × 倍速
        const elapsed = Math.floor(((Date.now() - this.streamStartedAt) / 1000) * Number(this.speed));
        this.playbackCurrent = Math.max(0, Math.min(this.playbackDuration, Math.round((this.streamBaseMs - this.segmentStartMs) / 1000) + elapsed));
        if (this.playbackCurrent >= this.playbackDuration) {
          this.playbackPlaying = false;
          this.stopProgressTimer();
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
        this.segments = (result && result.data) || [];
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
    playSegment(segment: RecordingSegment) {
      this.activeSegment = segment;
      this.playbackDuration = Math.max(0, Math.round((parseLocalMs(segment.endTime) - parseLocalMs(segment.startTime)) / 1000));
      this.playbackCurrent = 0;
      this.startPlaybackAt(0);
    },
    // NVR 回放是连续推送流：定位/快进/拖动进度 = 以「段开始 + 偏移」为新起点重新起流（段内 clamp），倍速随起流生效
    async startPlaybackAt(offsetSeconds: number) {
      const segment = this.activeSegment;
      if (!segment || !this.selectedCamera || this.playbackBusy) return;
      const offset = Math.max(0, Math.min(Math.max(this.playbackDuration - 1, 0), Math.round(offsetSeconds)));
      const startMs = this.segmentStartMs + offset * 1000;
      this.playbackBusy = true;
      this.stopProgressTimer();
      this.playbackPlaying = false;
      try {
        const result = await api.startRecordingStream({
          cameraId: this.selectedCamera.id,
          startTime: toLocalIsoSeconds(startMs),
          endTime: toLocalIsoSeconds(this.segmentEndMs),
          speed: Number(this.speed)
        });
        this.streamBaseMs = startMs;
        this.streamStartedAt = Date.now();
        this.playbackCurrent = offset;
        this.playbackPlaying = true;
        this.startProgressTimer();
        if (this.playbackStreamUrl === result.url) {
          // URL 相同不会触发 VideoPlayer 的 watch，先卸载再在下一帧重建流
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
    // 切换倍速：以当前回放位置为新起点按新倍速重新起流
    onSpeedChange() {
      if (!this.activeSegment || !this.playbackPlaying) return;
      this.startPlaybackAt(this.playbackCurrent);
    },
    togglePlayback() {
      if (!this.activeSegment) {
        this.showToast("请先查询并点击左侧录像段");
        return;
      }
      const player = this.$refs.playbackPlayer as any;
      if (this.playbackPlaying) {
        // 暂停即停流，进度停留在当前位置
        if (player) player.stop();
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
    seekPlayback(delta: number) {
      if (!this.activeSegment) return;
      this.startPlaybackAt(this.playbackCurrent + delta);
    },
    commitProgress() {
      if (!this.activeSegment) return;
      this.startPlaybackAt(this.playbackCurrent);
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
    openRecordDownload() {
      if (!this.selectedCamera) {
        this.showToast("请先在左侧选择摄像头");
        return;
      }
      // 已选中录像段时默认导出该段（时段过长会超出 NVR 导出上限），否则用查询时段
      const segment = this.activeSegment;
      const startMs = segment ? parseLocalMs(segment.startTime) : 0;
      const endMs = segment ? parseLocalMs(segment.endTime) : 0;
      const startTime = startMs ? toLocalIsoSeconds(startMs) : this.queryStart;
      const endTime = endMs ? toLocalIsoSeconds(endMs) : this.queryEnd;
      this.openModal("recordDownload", { camera: this.selectedCamera, startTime, endTime });
    }
  },
  beforeUnmount() {
    this.stopProgressTimer();
  }
});
</script>
