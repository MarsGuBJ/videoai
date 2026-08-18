<template>
  <section class="content review-wide media-preview-page">
    <div class="review-titlebar"><div><h1>实时预览</h1><p>多设备、多分屏实时查看现场画面和音频内容，支持云台控制、即时回放与轮巡</p></div></div>
    <div class="media-console-grid">
      <aside class="panel media-resource-panel">
        <div class="media-resource-tabs"><button :class="{ active: activeResourceTab === 'monitor' }" @click="activeResourceTab = 'monitor'">监控点</button><button :class="{ active: activeResourceTab === 'favorite' }" @click="activeResourceTab = 'favorite'">收藏</button><button :class="{ active: activeResourceTab === 'history' }" @click="activeResourceTab = 'history'">历史</button></div>
        <input class="input" placeholder="搜索监控点名称/IP" aria-label="搜索监控点名称或IP" />
        <div v-if="activeResourceTab === 'monitor'" class="media-playback-tree"><div class="media-panel-head"><b>监控资源</b><span class="hint-text">区域 / 监控点</span></div><div class="media-playback-tree-list exact-tree-list"><div v-for="area in areas" :key="area.name"><button class="exact-tree-area-row" :class="{ active: selectedArea && selectedArea.name === area.name }" @click="toggleArea(area)"><span>{{ expandedAreas[area.name] ? '⌄' : '›' }} {{ area.name }}</span><span>{{ area.count }} 台设备</span></button><div v-if="expandedAreas[area.name]" class="exact-tree-children"><button v-for="camera in area.cameras" :key="camera.code" class="exact-tree-device" :class="{ active: selectedCamera && selectedCamera.code === camera.code }" @click="selectCamera(camera, area)"><span>{{ camera.name }}</span><span>{{ camera.status }}</span></button></div></div></div></div>
        <ul v-else-if="activeResourceTab === 'favorite'" class="media-resource-list"><li class="group">私有收藏</li><li><span class="online-dot">★</span>园区入口重点点位</li><li class="group">共享收藏</li><li><span class="online-dot">★</span>北门卡口 IPC-07</li></ul>
        <ul v-else class="media-plan-list"><li><b>mipc_10.210.33.196_1</b><span>2026-07-07 09:23:59</span></li><li><b>真实黄区球机_10.210.2.53_通道_1</b><span>2026-07-07 09:19:07</span></li><li><b>A1栋入口 IPC-01</b><span>2026-07-07 09:14:12</span></li></ul>
      </aside>
      <section class="panel media-stage-panel">
        <div class="media-stage-toolbar"><div class="media-layout-buttons"><span>分屏</span><button v-for="count in [1, 4, 9, 16]" :key="count" :class="{ active: previewLayout === count }" @click="previewLayout = count">{{ count }}</button><button @click="openModal('customLayout')">自定义</button></div><div class="media-control-buttons"><select class="select" style="width:96px;"><option>主码流</option><option>子码流</option><option>自动切换</option></select><select class="select" style="width:96px;"><option>原始比例</option><option>满屏窗口</option></select><button class="btn" @click="openModal('videoConfig')">视频参数</button></div></div>
        <div class="media-video-grid" :class="{ single: previewLayout === 1 }"><article v-for="(feed, index) in visibleFeeds" :key="feed.name" class="media-video-tile" :class="{ selected: selectedFeed % feeds.length === index }" @click="selectedFeed = index"><video-player v-if="feed.camera" :url="feedUrl(feed.camera)" /><img v-else :src="feed.image" :alt="feed.name" /><div class="media-video-osd"><b>{{ feed.name }}</b><span>{{ feed.meta }}</span></div><span class="media-video-clock">2026/07/07 09:48:45</span></article></div>
        <div class="media-stage-controls"><div class="media-control-buttons"><button class="media-icon-button" title="播放或暂停" @click="showToast('播放状态已模拟切换')">▶</button><button class="media-icon-button" title="停止">■</button><button class="media-icon-button" title="声音">♪</button><button class="media-icon-button" title="抓拍" @click="showToast('已模拟保存抓拍图片')">▣</button><button class="btn" @click="openModal('quickReplay')">即时回放</button><button class="btn" @click="setRoute('mediaPlayback')">切至录像</button><button class="btn">电子放大</button></div><span class="media-network-state">网络自适应：已根据 {{ previewLayout }} 窗口切换子码流</span></div>
      </section>
      <aside class="panel media-ptz-panel">
        <div class="media-ptz-section"><div class="media-panel-head"><b>云台控制</b><span class="status-pill pass">已解锁</span></div><div class="media-ptz-wheel"><button class="up" @click="ptz('up')">▲</button><button class="left" @click="ptz('left')">◀</button><button class="center" @click="ptz('stop')">●</button><button class="right" @click="ptz('right')">▶</button><button class="down" @click="ptz('down')">▼</button></div><div class="media-range-list"><label>云台步长<input type="range" min="1" max="10" v-model="ptzStep" /></label></div><div class="media-control-buttons" style="margin-top:12px;"><button class="btn primary" @click="showToast('云台已模拟锁定')">锁定云台</button><button class="btn">解锁</button></div></div>
        <div class="media-ptz-section"><div class="media-range-list"><label>变倍<input type="range" min="1" max="10" value="4" /></label><label>变焦<input type="range" min="1" max="10" value="6" /></label><label>光圈<input type="range" min="1" max="10" value="5" /></label></div></div>
        <div class="media-ptz-section"><div class="media-panel-head"><b>预置点</b><button class="link-blue">＋</button></div><ul class="media-preset-list"><li><span>1 主入口</span><button class="link-blue" @click="ptz('preset_goto', 1)">调用</button></li><li><span>2 东侧车道</span><button class="link-blue" @click="ptz('preset_goto', 2)">调用</button></li><li><span>3 周界围栏</span><button class="link-blue" @click="ptz('preset_goto', 3)">调用</button></li></ul></div>
      </aside>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { api, cameraStreamUrl } from "../api";
import type { PtzCommand } from "../api";
import VideoPlayer from "../components/VideoPlayer.vue";

export default defineComponent({
  name: "MediaPreviewPage",
  components: { VideoPlayer },
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  inject: {
    openModal: { from: "openModal", default: (key: string) => {} },
    setRoute: { from: "setRoute", default: (route: string, options?: any) => {} },
    showToast: { from: "showToast", default: (m: string) => {} },
  },
  data() {
    return {
      activeResourceTab: "monitor",
      previewLayout: 4,
      selectedFeed: 0,
      selectedArea: null as any,
      selectedCamera: null as any,
      ptzStep: 5,
      startRequests: new Set<string>(),
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
      feeds: [
        { name: "真实黄区球机_10.210.2.53_通道_1", meta: "4K · H.265 · 主码流", image: this.store.img.car, camera: null },
        { name: "A1栋入口 IPC-01", meta: "H.264 · 子码流", image: this.store.img.target, camera: null },
        { name: "停车场 NVR-01", meta: "即时回放 · 前15秒", image: this.store.img.mountain, camera: null },
        { name: "北门卡口 IPC-07", meta: "H.265 · 子码流", image: this.store.img.map, camera: null }
      ] as any[]
    };
  },
  computed: {
    visibleFeeds(): any[] {
      return this.previewLayout === 1 ? this.feeds.slice(0, 1) : this.feeds;
    },
    ptzCamera(): any {
      if (this.selectedCamera && this.selectedCamera.camera) {
        return this.selectedCamera.camera;
      }
      if (!this.feeds.length) {
        return null;
      }
      const feed = this.visibleFeeds[this.selectedFeed % this.feeds.length];
      return feed && feed.camera ? feed.camera : null;
    }
  },
  mounted() {
    this.loadCameras();
  },
  methods: {
    async loadCameras() {
      try {
        const list = await api.cameras();
        if (list && list.length) {
          this.applyCameras(list);
        }
      } catch (e) {
        // 接口不可用时保留原型 mock 数据
      }
    },
    applyCameras(list: any[]) {
      const groups = new Map<string, any[]>();
      for (const c of list) {
        const areaName = c.area || "默认区域";
        if (!groups.has(areaName)) {
          groups.set(areaName, []);
        }
        groups.get(areaName)!.push({
          name: c.name,
          code: c.id,
          type: c.streamName || "IPC",
          status: c.status === "RUNNING" ? "在线" : "离线",
          image: this.store.img.car,
          camera: c
        });
      }
      const areas = [...groups.entries()].map(([name, cameras]) => ({ name, count: cameras.length, cameras }));
      const expanded: Record<string, boolean> = {};
      areas.forEach((a, i) => {
        expanded[a.name] = i === 0;
      });
      this.areas = areas;
      this.expandedAreas = expanded;
      this.feeds = list.slice(0, 4).map((c: any) => ({
        name: c.name,
        meta: `${c.streamName || "IPC"} · ${c.status === "RUNNING" ? "在线" : "离线"} · 主码流`,
        image: this.store.img.car,
        camera: c
      }));
      this.selectedFeed = 0;
      this.ensureStarted();
    },
    ensureStarted() {
      for (const feed of this.visibleFeeds) {
        const c = feed.camera;
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
    feedUrl(camera: any) {
      return cameraStreamUrl(camera);
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
      this.feeds = [
        { name: camera.name, meta: `${camera.type} · ${camera.status} · 主码流`, image: camera.image, camera: camera.camera || null },
        ...this.feeds.slice(1)
      ];
      this.selectedFeed = 0;
      this.ensureStarted();
    },
    async ptz(command: PtzCommand, preset?: number) {
      const camera = this.ptzCamera;
      if (!camera) {
        this.showToast("请先选择一路真实摄像头");
        return;
      }
      try {
        await api.ptzControl(camera.id, { command, step: Number(this.ptzStep), preset });
      } catch (e: any) {
        this.showToast(`云台控制失败：${(e && e.message) || e}`);
      }
    }
  }
});
</script>
