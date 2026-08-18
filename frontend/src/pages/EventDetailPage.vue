<template>
  <section class="content review-wide">
    <div class="review-titlebar"><div><h1>事件详情</h1><p>查看事件基础信息、告警证据、处置进度和关联任务</p></div><div class="segmented"><button class="btn" @click="setRoute('events')">返回列表</button><button class="btn primary" @click="ev.status === '待复核' ? setRoute('reviewTasks') : showToast('事件处置流程已模拟触发')">{{ ev.status === "待复核" ? "去复核" : "处理事件" }}</button></div></div>
    <div class="detail-header-card"><div><h2>{{ ev.name || "—" }}</h2><p>{{ ev.desc || "—" }}</p><div class="tags"><span class="tag blue">{{ ev.type || "—" }}</span><span class="level-pill" :class="levelClass(ev.level)">{{ ev.level || "—" }}</span><span class="status-pill" :class="statusClass(ev.status)">{{ ev.status || "—" }}</span><span class="tag">{{ ev.area || "—" }} / {{ ev.point || "—" }}</span></div></div><div class="segmented"><button class="btn" @click="setRoute('deployTaskDetail')">关联任务</button><button class="btn" @click="showToast('事件已模拟关闭')">关闭事件</button></div></div>
    <div class="detail-grid">
      <div class="panel search-panel"><h3 class="form-section-title">告警画面</h3><img :src="eventImage" :alt="ev.name" style="width:100%; height:300px; border-radius:6px; object-fit:cover; background:#f2f4f7;" /><div class="tags" style="margin-top:12px;"><span class="tag blue">AI置信度 92%</span><span class="tag">已截取关键帧</span><span class="tag">可进入人工复核</span></div></div>
      <div class="panel search-panel"><h3 class="form-section-title">事件信息</h3><dl class="info-list"><dt>事件ID</dt><dd>{{ ev.id || "—" }}</dd><dt>事件类型</dt><dd>{{ ev.type || "—" }}</dd><dt>事件等级</dt><dd><span class="level-pill" :class="levelClass(ev.level)">{{ ev.level || "—" }}</span></dd><dt>事件来源</dt><dd>{{ ev.eventSource || "—" }}</dd><dt>区域</dt><dd>{{ ev.area || "—" }}</dd><dt>点位</dt><dd>{{ ev.point || "—" }}</dd><dt>发生时间</dt><dd>{{ ev.time || "—" }}</dd><dt>负责人</dt><dd>{{ ev.owner || "—" }}</dd><dt>当前状态</dt><dd><span class="status-pill" :class="statusClass(ev.status)">{{ ev.status || "—" }}</span></dd></dl></div>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { assetUrl } from "../api";

export default defineComponent({
  name: "EventDetailPage",
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  inject: {
    setRoute: { from: "setRoute", default: (_route: string, _options?: any) => {} },
    showToast: { from: "showToast", default: (_m: string) => {} }
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
        area: e.area || e.cameraArea || "",
        point: e.point || e.cameraName || "",
        status: e.status,
        time: e.time || e.videoTime || e.matchedAt || e.createdAt || "",
        owner: e.owner,
        image: e.image || e.snapshotUrl || e.facePhotoUrl || e.faceProfilePhotoUrl || ""
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
    }
  }
});
</script>
