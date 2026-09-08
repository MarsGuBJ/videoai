<template>
  <section class="content review-wide">
    <div class="review-titlebar"><div><h1>事件统计</h1><p>按时间、类型、区域和复核状态统计布控事件</p></div></div>
    <summary-cards :cards="cards"></summary-cards>
    <div class="review-board">
    <div class="page-actions"><div class="left"><button class="btn" @click="loadStats">查询</button><button class="btn" @click="resetFilters">重置</button><input class="input" style="width:150px;" type="date" v-model="startDate" aria-label="开始日期" /><input class="input" style="width:150px;" type="date" v-model="endDate" aria-label="结束日期" /><select class="select" style="width:150px;" v-model="areaFilter"><option value="">全部区域</option><option v-for="area in stats.areas" :key="area" :value="area">{{ area }}</option></select></div></div>
      <div class="stats-layout">
        <div class="chart-panel"><h3>事件趋势</h3><div class="bar-chart"><div class="bar-item" v-for="item in stats.trend" :key="item.date"><span>{{ item.count }}</span><span class="bar" :style="{ height: Math.round(item.count / trendMax * 160) + 'px' }"></span><span>{{ shortDate(item.date) }}</span></div></div></div>
        <div class="chart-panel"><h3>事件类型分布</h3><div class="stat-row" v-for="item in typeRows" :key="item.label"><span>{{ item.label }}</span><span class="progress-track"><span class="progress-fill" :style="{ width: Math.round(item.value / typeMax * 100) + '%' }"></span></span><b>{{ item.value }}</b></div></div>
        <div class="chart-panel"><h3>区域事件排行</h3><div class="rank-list"><div class="rank-item" v-for="(item, index) in stats.byArea" :key="item.area"><span class="rank-no">{{ index + 1 }}</span><span>{{ item.area }}</span><strong>{{ item.count }} 起</strong></div><div v-if="!loading && !stats.byArea.length" class="rank-item"><span>暂无数据</span></div></div></div>
        <div class="chart-panel review-event-panel"><h3>复核事件统计</h3><div class="review-event-legend" aria-label="图例"><span><i></i>有效</span><span><i class="invalid"></i>无效</span></div><div class="review-event-chart" role="img" aria-label="按事件类型统计的有效和无效复核事件数量"><div class="review-event-y-axis"><span>{{ reviewMax }}</span><span>{{ Math.ceil(reviewMax * 2 / 3) }}</span><span>{{ Math.ceil(reviewMax / 3) }}</span><span>0</span></div><div class="review-event-plot"><div class="review-event-group" v-for="item in reviewRows" :key="item.label"><div class="review-event-bars"><span class="review-event-bar valid" :style="{ height: Math.max(7, Math.round(item.valid / reviewMax * 154)) + 'px' }" :title="item.label + '：有效 ' + item.valid + ' 起'"><b>{{ item.valid }}</b></span><span class="review-event-bar invalid" :style="{ height: Math.max(7, Math.round(item.invalid / reviewMax * 154)) + 'px' }" :title="item.label + '：无效 ' + item.invalid + ' 起'"><b>{{ item.invalid }}</b></span></div><span class="review-event-label">{{ item.label }}</span></div></div></div></div>
      </div>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import SummaryCards from "../components/SummaryCards.vue";
import { api } from "../api";
import type { DeploymentEventStats } from "../types";

const EVENT_TYPE_LABELS: Record<string, string> = {
  face_match: "人脸比对",
  object_detection: "目标检测"
};

function emptyStats(): DeploymentEventStats {
  return {
    total: 0,
    today: 0,
    week: 0,
    unreviewed: 0,
    reviewRate: 0,
    faceMatch: 0,
    objectDetection: 0,
    areas: [],
    trend: [],
    byArea: [],
    reviewByType: []
  };
}

function toDateInput(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

export default defineComponent({
  name: "StatsPage",
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  components: { SummaryCards },
  inject: {
    injectedShowToast: { from: "showToast", default: (_m: string) => {} }
  },
  data() {
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - 6);
    return {
      stats: emptyStats(),
      loading: false,
      startDate: toDateInput(start),
      endDate: toDateInput(end),
      areaFilter: ""
    };
  },
  computed: {
    cards() {
      return [
        { label: "今日事件", value: this.stats.today },
        { label: "本周事件", value: this.stats.week },
        { label: "未复核事件", value: this.stats.unreviewed },
        { label: "复核率", value: `${Math.round(this.stats.reviewRate * 100)}%` }
      ];
    },
    trendMax(): number {
      return Math.max(1, ...this.stats.trend.map((item) => item.count));
    },
    typeRows() {
      return [
        { label: "人脸比对", value: this.stats.faceMatch },
        { label: "目标检测", value: this.stats.objectDetection }
      ];
    },
    typeMax(): number {
      return Math.max(1, ...this.typeRows.map((item) => item.value));
    },
    reviewRows() {
      return this.stats.reviewByType.map((item) => ({
        label: EVENT_TYPE_LABELS[item.eventType] || item.eventType,
        valid: item.valid,
        invalid: item.invalid
      }));
    },
    reviewMax(): number {
      return Math.max(1, ...this.reviewRows.flatMap((item) => [item.valid, item.invalid]));
    }
  },
  mounted() {
    this.loadStats();
  },
  methods: {
    showToast(m: string) {
      (this as any).injectedShowToast(m);
    },
    shortDate(value: string): string {
      return value.length >= 10 ? value.slice(5) : value;
    },
    toIsoStart(value: string): string | undefined {
      if (!value) return undefined;
      const date = new Date(`${value}T00:00:00`);
      return Number.isNaN(date.getTime()) ? undefined : date.toISOString();
    },
    toIsoEnd(value: string): string | undefined {
      if (!value) return undefined;
      const date = new Date(`${value}T23:59:59`);
      return Number.isNaN(date.getTime()) ? undefined : date.toISOString();
    },
    resetFilters() {
      const end = new Date();
      const start = new Date();
      start.setDate(start.getDate() - 6);
      this.startDate = toDateInput(start);
      this.endDate = toDateInput(end);
      this.areaFilter = "";
      this.loadStats();
    },
    async loadStats() {
      if (this.loading) return;
      this.loading = true;
      try {
        this.stats = await api.deploymentEventStats({
          startTime: this.toIsoStart(this.startDate),
          endTime: this.toIsoEnd(this.endDate),
          area: this.areaFilter || undefined
        });
      } catch (e) {
        this.showToast(e instanceof Error ? e.message : "事件统计加载失败");
      } finally {
        this.loading = false;
      }
    }
  }
});
</script>
