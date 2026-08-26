<template>
  <section class="content review-wide media-playback-page">
    <div class="review-titlebar"><div><h1>录像回放</h1><p>按空间、设备与时间快速检索历史录像，支持时间轴定位、同步回放、分段回放和录像下载</p></div><div class="segmented"><button class="btn" @click="openModal('recordDownload')">录像下载</button><button class="btn primary" @click="setRoute('mediaPreview')">切换实况</button></div></div>
    <div class="media-console-grid playback">
      <aside class="panel media-resource-panel">
        <div v-if="resourceTab === 'resource'" class="media-playback-tree"><div class="media-panel-head"><b>录像资源</b><span class="hint-text">区域 / 监控点</span></div><div class="media-playback-tree-list exact-tree-list"><div v-for="region in regions" :key="region.fullPath"><button class="exact-tree-area-row" :class="{ active: selectedRegion && selectedRegion.fullPath === region.fullPath }" :style="region.child ? 'padding-left:24px;' : ''" @click="toggleRegion(region)"><span>{{ expandedRegions[region.fullPath] ? '⌄' : '›' }} {{ region.name }}</span><span>{{ region.count }} 台设备</span></button><div v-if="expandedRegions[region.fullPath]" class="exact-tree-children"><button v-for="camera in camerasForRegion(region)" :key="camera.code" class="exact-tree-device" :class="{ active: selectedCamera && selectedCamera.code === camera.code }" @click="selectCamera(camera, region)"><span>{{ camera.name }}</span><span>{{ camera.status }}</span></button></div></div><div v-if="!regions.length" style="padding:12px;color:#888;">暂无录像资源，请先在设备管理中添加设备</div></div></div><ul v-else class="media-plan-list"><li><b>异常人员经过</b><span>2K_IPC7240 · 2026-07-06 19:42:11</span></li><li><b>车辆逆行片段</b><span>北门卡口 · 2026-07-06 08:14:32</span></li><li><b>设备调试留存</b><span>A1栋入口 · 2026-07-05 16:20:08</span></li></ul>
        <div class="media-record-query"><div class="media-resource-tabs" style="margin-bottom:0;"></div><label>开始时间<input class="input" type="datetime-local" value="2026-07-05T00:00" /></label><label>结束时间<input class="input" type="datetime-local" value="2026-07-07T23:59" /></label><button class="btn primary" @click="showToast('录像检索已模拟完成')">录像查询</button></div>
      </aside>
      <section class="panel media-stage-panel">
        <div class="media-playback-player">
          <video-player v-if="playbackStreamUrl" :url="playbackStreamUrl"></video-player>
          <img v-else :src="currentPlaybackFeed.image" :alt="currentPlaybackFeed.name" />
          <div class="media-playback-player-title">录像回放 · {{ currentPlaybackFeed.name }}</div>
          <div class="media-playback-overlay-controls">
            <div class="media-playback-button-group" aria-label="录像回放控制">
              <button class="media-playback-step" type="button" title="跳到开始" aria-label="跳到开始" @click="seekPlayback(-playbackDuration)">|◀</button>
              <button class="media-playback-step" type="button" title="后退10秒" aria-label="后退10秒" @click="seekPlayback(-10)">◀</button>
              <button class="media-playback-toggle active" type="button" title="播放或暂停" :aria-label="playbackPlaying ? '暂停' : '播放'" @click="togglePlayback">{{ playbackPlaying ? 'Ⅱ' : '▶' }}</button>
              <button class="media-playback-step" type="button" title="前进10秒" aria-label="前进10秒" @click="seekPlayback(10)">▶</button>
              <button class="media-playback-step" type="button" title="跳到结束" aria-label="跳到结束" @click="seekPlayback(playbackDuration)">▶|</button>
            </div>
            <span>{{ formatPlaybackTime(playbackCurrent) }}</span>
            <input class="media-playback-progress" type="range" min="0" :max="playbackDuration" step="1" v-model.number="playbackCurrent" aria-label="录像播放进度" />
            <span>{{ formatPlaybackTime(playbackDuration) }}</span>
            <select class="media-playback-rate" v-model="speed" aria-label="播放倍速"><option value="0.5">0.5x</option><option value="1">1x</option><option value="1.5">1.5x</option><option value="2">2x</option></select>
          </div>
        </div>
      </section>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { api, streamUrl } from "../api";
import { buildRegionTree, loadCustomRegions, type RegionNode } from "../utils/regions";
import VideoPlayer from "../components/VideoPlayer.vue";

function statusLabel(status: string): string {
  const value = (status || "").toUpperCase();
  if (value === "RUNNING") return "在线";
  if (value === "STOPPED") return "离线";
  if (value === "DISABLED") return "停用";
  return "未成功连接";
}

export default defineComponent({
  name: "MediaPlaybackPage",
  components: { VideoPlayer },
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  inject: {
    openModal: { from: "openModal", default: (name: string) => {} },
    setRoute: { from: "setRoute", default: (route: string, options?: any) => {} },
    showToast: { from: "showToast", default: (m: string) => {} }
  },
  data() {
    return {
      resourceTab: "resource",
      playbackMode: "regular",
      speed: "1",
      playbackPlaying: false,
      playbackCurrent: 0,
      playbackDuration: 200,
      playbackTimer: null as number | null,
      playbackGridCount: 1,
      selectedPlaybackTile: 0,
      selectedCamera: null as any,
      selectedRegion: null as RegionNode | null,
      playbackStreamUrl: undefined as string | undefined,
      regions: [] as RegionNode[],
      regionCameras: {} as Record<string, any[]>,
      expandedRegions: {} as Record<string, boolean>,
      playbackFeeds: [
        { name: "南门入口枪机", meta: "4K · smart265 · 中心录像", image: this.store.img.car },
        { name: "真实黄区球机_10.210.2.54_通道_1", meta: "smart264 · 同步", image: this.store.img.target },
        { name: "15_155_波_通道_1", meta: "设备录像 · 夜视", image: this.store.img.mountain },
        { name: "A1栋入口 IPC-01", meta: "告警录像", image: this.store.img.map }
      ] as any[]
    };
  },
  computed: {
    visiblePlaybackFeeds(): any[] {
      return this.playbackGridCount === 1 ? this.playbackFeeds.slice(0, 1) : this.playbackFeeds;
    },
    currentPlaybackFeed(): any {
      return this.playbackFeeds[this.selectedPlaybackTile] || this.playbackFeeds[0];
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
        const areaPath = (cam.area || "").trim() || "未分配";
        if (!regionCameras[areaPath]) regionCameras[areaPath] = [];
        regionCameras[areaPath].push({
          id: cam.id,
          name: cam.name,
          code: cam.id,
          type: cam.protocol || cam.streamApp || "IPC",
          status: statusLabel(cam.status),
          streamName: cam.streamName,
          image: this.store.img.car,
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
    formatPlaybackTime(value: any) {
      const seconds = Math.max(0, Math.min(this.playbackDuration, Math.floor(Number(value) || 0)));
      return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
    },
    stopPlayback() {
      this.playbackPlaying = false;
      if (this.playbackTimer) window.clearInterval(this.playbackTimer);
      this.playbackTimer = null;
    },
    togglePlayback() {
      if (this.playbackPlaying) {
        this.stopPlayback();
        return;
      }
      if (this.playbackCurrent >= this.playbackDuration) this.playbackCurrent = 0;
      this.playbackPlaying = true;
      this.playbackTimer = window.setInterval(() => {
        this.playbackCurrent = Math.min(this.playbackDuration, this.playbackCurrent + Number(this.speed));
        if (this.playbackCurrent >= this.playbackDuration) this.stopPlayback();
      }, 1000);
    },
    seekPlayback(delta: number) {
      this.playbackCurrent = Math.max(0, Math.min(this.playbackDuration, this.playbackCurrent + delta));
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
      this.playbackStreamUrl = camera.streamName
        ? streamUrl(`/api/streams/live/${encodeURIComponent(camera.streamName)}.m3u8`)
        : undefined;
      this.playbackFeeds = [
        { name: camera.name, meta: `${camera.type} · ${camera.status} · 中心录像`, image: camera.image },
        ...this.playbackFeeds.slice(1)
      ];
      this.selectedPlaybackTile = 0;
      this.playbackCurrent = 0;
      this.stopPlayback();
    }
  },
  beforeUnmount() {
    this.stopPlayback();
  }
});
</script>
