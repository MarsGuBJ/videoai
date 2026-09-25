<template>
  <section class="content review-wide">
    <div class="review-titlebar"><div><h1>事件详情</h1><p>查看事件基础信息、告警证据、处置进度和关联任务</p></div><div class="segmented"><button class="btn" @click="setRoute('events')">返回列表</button><button class="btn primary" :disabled="handling" @click="ev.status === '待复核' ? setRoute('reviewTasks') : handleEvent('handle')">{{ ev.status === "待复核" ? "去复核" : "处理事件" }}</button></div></div>
    <div class="detail-header-card"><div><h2>{{ ev.name || "—" }}</h2><p>{{ ev.desc || "—" }}</p><div class="tags"><span class="tag blue">{{ ev.type || "—" }}</span><span class="level-pill" :class="levelClass(ev.level)">{{ ev.level || "—" }}</span><span class="status-pill" :class="statusClass(ev.status)">{{ ev.status || "—" }}</span><span class="tag">{{ ev.area || "—" }} / {{ ev.point || "—" }}</span></div></div><div class="segmented"><button class="btn" @click="setRoute('deployTaskDetail')">关联任务</button><button class="btn" :disabled="handling" @click="handleEvent('close')">关闭事件</button></div></div>
    <div class="detail-grid">
      <div class="panel search-panel"><h3 class="form-section-title">告警画面<span class="alarm-view-switch"><button type="button" :class="{ active: alarmView === 'video' }" @click="alarmView = 'video'">视频</button><button type="button" :class="{ active: alarmView === 'image' }" @click="alarmView = 'image'">图片</button></span></h3><div v-if="alarmView === 'video'" class="alarm-video-wrap"><video-player v-if="eventVideo" :url="eventVideo" /><div v-else class="alarm-video-empty">暂无视频画面</div></div><img v-else :src="eventImage" :alt="ev.name" style="width:100%; height:300px; border-radius:6px; object-fit:cover; background:#f2f4f7;" /><div class="tags" style="margin-top:12px;"><span class="tag blue">AI置信度 92%</span><span class="tag">已截取关键帧</span><span class="tag">可进入人工复核</span></div></div>
      <div class="panel search-panel"><h3 class="form-section-title">事件信息</h3><dl class="info-list"><dt>事件ID</dt><dd>{{ ev.id || "—" }}</dd><dt>事件类型</dt><dd>{{ ev.type || "—" }}</dd><dt>事件等级</dt><dd><span class="level-pill" :class="levelClass(ev.level)">{{ ev.level || "—" }}</span></dd><dt>事件来源</dt><dd>{{ ev.eventSource || "—" }}</dd><dt>算法编号</dt><dd>{{ ev.algorithmCode || "—" }}</dd><dt>复核状态</dt><dd>{{ ev.reviewStatus || "—" }}</dd><dt>区域</dt><dd>{{ ev.area || "—" }}</dd><dt>点位</dt><dd>{{ ev.point || "—" }}</dd><dt>发生时间</dt><dd>{{ ev.time || "—" }}</dd><dt>负责人</dt><dd>{{ ev.owner || "—" }}</dd><dt>当前状态</dt><dd><span class="status-pill" :class="statusClass(ev.status)">{{ ev.status || "—" }}</span></dd><dt>处置时间</dt><dd>{{ formattedHandledAt }}</dd><dt>处置说明</dt><dd>{{ ev.handleNote || "—" }}</dd></dl></div>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { api, assetUrl, cameraStreamUrl, sameOriginAssetUrl } from "../api";
import VideoPlayer from "../components/VideoPlayer.vue";

export default defineComponent({
  name: "EventDetailPage",
  components: { VideoPlayer },
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  inject: {
    setRoute: { from: "setRoute", default: (_route: string, _options?: any) => {} },
    showToast: { from: "showToast", default: (_m: string) => {} }
  },
  data() {
    return {
      // 告警画面默认展示图片，可切换为关联摄像头的实时视频
      alarmView: "image",
      eventVideo: undefined as string | undefined,
      // 处置动作后的本地覆盖（避免依赖列表刷新）
      handling: false,
      localStatus: null as string | null,
      localHandledAt: null as string | null,
      localHandleNote: null as string | null
    };
  },
  mounted() {
    this.loadEventVideo();
  },
  computed: {
    // Normalize both mock-shaped rows (store.eventRows) and API-shaped
    // events (FaceEvent / FaceMatchEvent) into the fields the template uses.
    ev(): any {
      const e: any = this.selectedEvent || {};
      const profileName = e.profileName || e.faceProfileName;
      return {
        id: e.id,
        name: e.name || (profileName ? `${profileName}人脸比对命中` : ""),
        desc: e.desc || "",
        type: e.type || (profileName ? "人脸比对" : ""),
        level: e.level,
        eventSource: e.eventSource,
        algorithmCode: e.algorithmCode,
        reviewStatus: e.reviewStatus,
        area: e.area || e.cameraArea || "",
        point: e.point || e.cameraName || "",
        status: this.localStatus ?? e.status,
        handledAt: this.localHandledAt ?? e.handledAt,
        handleNote: this.localHandleNote ?? e.handleNote,
        time: e.time || e.videoTime || e.matchedAt || e.createdAt || "",
        owner: e.owner,
        image: sameOriginAssetUrl(e.image || e.snapshotUrl || e.facePhotoUrl || e.faceProfilePhotoUrl || ""),
        cameraId: e.cameraId,
        cameraName: e.cameraName
      };
    },
    eventImage(): string {
      const image = this.ev.image;
      if (!image) {
        return "";
      }
      if (/^(https?:|blob:|data:|\/)/.test(image)) {
        return image;
      }
      return assetUrl(image);
    },
    formattedHandledAt(): string {
      const value = this.ev.handledAt;
      if (!value) return "—";
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return value;
      const pad = (n: number) => String(n).padStart(2, "0");
      return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
    }
  },
  methods: {
    // 处置/关闭事件：调用后端接口写入处置状态与留痕，失败保留原状并提示
    async handleEvent(action: "handle" | "close") {
      if (!this.ev.id) {
        this.showToast("事件缺少ID，无法处置");
        return;
      }
      if (this.handling) return;
      this.handling = true;
      try {
        const updated = await api.handleDeploymentEvent(this.ev.id, { action });
        this.localStatus = updated.handleStatus || (action === "handle" ? "已处置" : "已关闭");
        this.localHandledAt = updated.handledAt || new Date().toISOString();
        this.localHandleNote = updated.handleNote || "";
        this.showToast(action === "handle" ? "事件已处置" : "事件已关闭");
      } catch (error) {
        this.showToast(error instanceof Error ? error.message : "事件处置失败");
      } finally {
        this.handling = false;
      }
    },
    // 解析事件关联摄像头的实时流地址，作为“视频”视图的播放源
    async loadEventVideo() {
      try {
        const cameras = await api.cameras();
        const camera = (cameras || []).find(
          (item: any) => item.id === this.ev.cameraId || (this.ev.cameraName && item.name === this.ev.cameraName)
        );
        this.eventVideo = camera ? cameraStreamUrl(camera) : undefined;
      } catch {
        this.eventVideo = undefined;
      }
    }
  }
});
</script>
