<template>
  <section class="content review-wide media-playback-page">
    <div class="review-titlebar"><div><h1>录像回放</h1><p>按空间、设备与时间快速检索历史录像，支持时间轴定位、同步回放、分段回放和录像下载</p></div><div class="segmented"><button class="btn" @click="openModal('recordDownload')">录像下载</button><button class="btn primary" @click="setRoute('mediaPreview')">切换实况</button></div></div>
    <div class="media-console-grid playback">
      <aside class="panel media-resource-panel">
        <div v-if="resourceTab === 'resource'" class="media-playback-tree"><div class="media-panel-head"><b>录像资源</b><span class="hint-text">区域 / 监控点</span></div><div class="media-playback-tree-list exact-tree-list"><div v-for="area in areas" :key="area.name"><button class="exact-tree-area-row" :class="{ active: selectedArea && selectedArea.name === area.name }" @click="toggleArea(area)"><span>{{ expandedAreas[area.name] ? '⌄' : '›' }} {{ area.name }}</span><span>{{ area.count }} 台设备</span></button><div v-if="expandedAreas[area.name]" class="exact-tree-children"><button v-for="camera in area.cameras" :key="camera.code" class="exact-tree-device" :class="{ active: selectedCamera && selectedCamera.code === camera.code }" @click="selectCamera(camera, area)"><span>{{ camera.name }}</span><span>{{ camera.status }}</span></button></div></div></div></div><ul v-else class="media-plan-list"><li><b>异常人员经过</b><span>2K_IPC7240 · 2026-07-06 19:42:11</span></li><li><b>车辆逆行片段</b><span>北门卡口 · 2026-07-06 08:14:32</span></li><li><b>设备调试留存</b><span>A1栋入口 · 2026-07-05 16:20:08</span></li></ul>
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
import VideoPlayer from "../components/VideoPlayer.vue";

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
      selectedArea: null as any,
      selectedCamera: null as any,
      playbackStreamUrl: undefined as string | undefined,
      expandedAreas: {
        "园区南门": true,
        "A座停车区": false,
        "生产通道": false,
        "仓储区域": false,
        "外围周界": false
      } as Record<string, boolean>,
      areas: [
        {
          name: "园区南门",
          count: 12,
          cameras: [
            { name: "南门入口枪机", code: "CAM-001", type: "枪机", status: "在线", image: this.store.img.car },
            { name: "南门广角球机", code: "CAM-002", type: "球机", status: "在线", image: this.store.img.target },
            { name: "访客通道半球", code: "CAM-009", type: "半球", status: "在线", image: this.store.img.portrait }
          ]
        },
        {
          name: "A座停车区",
          count: 8,
          cameras: [
            { name: "A1停车场东侧", code: "CAM-003", type: "枪机", status: "在线", image: this.store.img.car },
            { name: "A2停车场出口", code: "CAM-008", type: "枪机", status: "在线", image: this.store.img.target }
          ]
        },
        {
          name: "生产通道",
          count: 6,
          cameras: [
            { name: "生产通道1号门", code: "CAM-004", type: "半球", status: "在线", image: this.store.img.analyst },
            { name: "生产通道东侧", code: "CAM-010", type: "枪机", status: "在线", image: this.store.img.map }
          ]
        },
        {
          name: "仓储区域",
          count: 10,
          cameras: [
            { name: "仓储区西门", code: "CAM-005", type: "枪机", status: "连接异常", image: this.store.img.ai },
            { name: "仓储装卸口", code: "CAM-011", type: "热成像", status: "在线", image: this.store.img.mountain }
          ]
        },
        {
          name: "外围周界",
          count: 7,
          cameras: [
            { name: "外围周界北侧", code: "CAM-006", type: "热成像", status: "连接异常", image: this.store.img.mountain },
            { name: "东侧围栏通道", code: "CAM-012", type: "枪机", status: "在线", image: this.store.img.map }
          ]
        }
      ] as any[],
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
  methods: {
    async loadCameras() {
      try {
        const cameras = await api.cameras();
        if (!cameras || cameras.length === 0) return;
        const groups: Record<string, any[]> = {};
        for (const cam of cameras) {
          const areaName = cam.area || "默认区域";
          if (!groups[areaName]) groups[areaName] = [];
          groups[areaName].push({
            id: cam.id,
            name: cam.name,
            code: cam.id,
            type: cam.streamApp || "IPC",
            status: cam.status === "RUNNING" ? "在线" : "连接异常",
            streamName: cam.streamName,
            image: this.store.img.car
          });
        }
        this.areas = Object.keys(groups).map((name) => ({
          name,
          count: groups[name].length,
          cameras: groups[name]
        }));
        const expanded: Record<string, boolean> = {};
        this.areas.forEach((area: any, index: number) => {
          expanded[area.name] = index === 0;
        });
        this.expandedAreas = expanded;
      } catch (error) {
        // 后端不可用时保留原型 mock 区域树
      }
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
    toggleArea(area: any) {
      if (!this.selectedArea || this.selectedArea.name !== area.name) {
        this.selectedArea = area;
        this.selectedCamera = null;
      }
      this.expandedAreas[area.name] = !this.expandedAreas[area.name];
    },
    selectCamera(camera: any, area: any) {
      this.selectedArea = area;
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
