<template>
  <section class="content review-wide">
    <div class="review-titlebar"><div><h1>事件列表</h1><p>统一管理视觉告警事件、复核状态和处置结果</p></div></div>
    <summary-cards :cards="cards"></summary-cards>
    <div class="review-board">
      <div class="page-actions"><div class="left"><button class="btn" @click="showToast('已根据当前条件刷新演示结果')">查询</button><button class="btn">重置</button><input class="input" style="width:260px;" placeholder="搜索事件名称、事件ID" /><select class="select" style="width:140px;"><option>全部状态</option><option>待复核</option><option>有效</option></select><select class="select" style="width:150px;"><option>全部类型</option><option v-for="item in store.eventTypeStats">{{ item.label }}</option></select><select class="select" style="width:150px;"><option>全部区域</option><option>园区南门</option><option>A座停车区</option><option>仓储区</option></select></div></div>
      <table class="prototype-table">
        <colgroup><col style="width:132px;" /><col style="width:220px;" /><col style="width:92px;" /><col style="width:72px;" /><col style="width:150px;" /><col style="width:130px;" /><col style="width:82px;" /><col style="width:112px;" /></colgroup>
        <thead><tr><th>事件ID</th><th class="left">事件信息</th><th>事件类型</th><th>等级</th><th class="left">事件来源</th><th>区域/点位</th><th>状态</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="row in store.eventRows" :key="row.id">
            <td>{{ row.id }}</td><td class="left"><div class="event-name-cell"><img class="event-thumb" :src="row.image" :alt="row.name" style="cursor:pointer;" @click="setRoute('imageSearch', { prefill: row.image })" /><div><h4>{{ row.name }}</h4><p>{{ row.time }}</p></div></div></td><td>{{ row.type }}</td><td><span class="level-pill" :class="levelClass(row.level)">{{ row.level }}</span></td><td class="left ellipsis">{{ row.eventSource }}</td><td>{{ row.area }}<br /><span class="hint-text">{{ row.point }}</span></td><td><span class="status-pill" :class="statusClass(row.status)">{{ row.status }}</span></td>
            <td><button class="link-blue" @click="openEventDetail(row)">详情</button><button v-if="row.status !== '待复核'" class="link-blue" @click="showToast('事件处置流程已模拟触发')">处理</button></td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import SummaryCards from "../components/SummaryCards.vue";
import { api, assetUrl } from "../api";
import type { FaceEvent, FaceMatchEvent } from "../types";

// The prototype accesses injected members (setRoute/openEventDetail/showToast)
// directly in the template; vue-tsc does not infer inject keys onto the
// template `this`, so merge them into ComponentCustomProperties (type-level
// only, runtime inject declarations below stay exactly as the prototype).
declare module "vue" {
  interface ComponentCustomProperties {
    openEventDetail: (row: any) => void;
  }
}

export default defineComponent({
  name: "EventsPage",
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  components: { SummaryCards },
  inject: {
    setRoute: { from: "setRoute", default: (_route: string, _options?: any) => {} },
    openEventDetail: { from: "openEventDetail", default: (_row: any) => {} },
    showToast: { from: "showToast", default: (_m: string) => {} }
  },
  computed: {
    cards() {
      return [
        { label: "事件总数", value: this.store.eventRows.length },
        { label: "待复核", value: this.store.eventRows.filter((row: any) => row.status === "待复核").length },
        { label: "有效", value: this.store.eventRows.filter((row: any) => row.status === "有效").length },
        { label: "高等级", value: this.store.eventRows.filter((row: any) => row.level === "高").length }
      ];
    }
  },
  methods: {
    formatEventTime(value?: string | null): string {
      if (!value) {
        return "—";
      }
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) {
        return value;
      }
      const pad = (n: number) => String(n).padStart(2, "0");
      return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
    },
    mapFaceMatchEvent(event: FaceMatchEvent) {
      const similarity = event.similarity == null ? "" : `比对相似度 ${(event.similarity <= 1 ? event.similarity * 100 : event.similarity).toFixed(1)}%`;
      return {
        id: event.id,
        name: `${event.faceProfileName || "未知人员"}人脸比对命中`,
        type: "人脸比对",
        level: "中",
        eventSource: "中心推理平台",
        area: event.cameraArea || "—",
        point: event.cameraName || "—",
        status: "待复核",
        time: this.formatEventTime(event.matchedAt || event.createdAt),
        owner: "—",
        image: assetUrl(event.snapshotUrl || event.faceProfilePhotoUrl),
        desc: similarity
      };
    },
    mapFaceEvent(event: FaceEvent) {
      const similarity = event.similarity == null ? "" : `比对相似度 ${(event.similarity <= 1 ? event.similarity * 100 : event.similarity).toFixed(1)}%`;
      return {
        id: event.id,
        name: `${event.profileName || "未知人员"}人脸比对命中`,
        type: "人脸比对",
        level: "中",
        eventSource: "中心推理平台",
        area: "—",
        point: event.cameraName || "—",
        status: "待复核",
        time: this.formatEventTime(event.videoTime || event.createdAt),
        owner: "—",
        image: assetUrl(event.snapshotUrl || event.facePhotoUrl),
        desc: similarity
      };
    },
    async loadEvents() {
      try {
        const rows = await api.faceMatchEvents();
        if (rows.length) {
          this.store.eventRows = rows.map((event) => this.mapFaceMatchEvent(event));
          return;
        }
      } catch (error) {
        console.warn("EventsPage: failed to load face match events", error);
      }
      try {
        const rows = await api.events();
        if (rows.length) {
          this.store.eventRows = rows.map((event) => this.mapFaceEvent(event));
        }
      } catch (error) {
        console.warn("EventsPage: failed to load events, keeping mock rows", error);
      }
    }
  },
  created() {
    this.loadEvents();
  }
});
</script>
