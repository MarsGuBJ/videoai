<template>
  <section class="content wide overview-skin">
    <div class="overview-tech-stage" aria-hidden="true">
      <span class="overview-tech-shape overview-tech-core"></span>
      <span class="overview-tech-shape overview-tech-ring"></span>
      <span class="overview-tech-shape overview-tech-cube"></span>
      <span class="overview-tech-shape overview-tech-prism"></span>
      <span class="overview-tech-shape overview-tech-spark"></span>
    </div>
    <div class="title-row">
      <span class="module-icon">▦</span>
      <div><h1 class="page-title">总览</h1><p class="page-subtitle">集中查看视觉大模型平台运行态、资源状态、任务规模与搜索热点</p></div>
    </div>
    <div class="overview-grid">
      <div class="overview-card" v-for="card in cards" :key="card.label" :class="{ clickable: card.route }" @click="card.route && setRoute(card.route)">
        <div class="overview-card-head"><span>{{ card.label }}</span><span class="overview-card-icon">{{ card.icon }}</span></div>
        <strong>{{ card.value }}<small>{{ card.unit }}</small></strong>
        <p>{{ card.desc }}</p>
      </div>
    </div>
    <div class="overview-layout">
      <div class="overview-main-stack">
        <section class="panel overview-section">
          <div class="table-head" style="padding:0 0 12px; border-bottom:0;">
            <h3>资源负载</h3>
          </div>
          <div class="device-bars">
            <div class="device-row" v-for="item in devices" :key="item.name">
              <span>{{ item.name }}</span>
              <span class="bar-track"><i class="bar-fill" :style="{ width: item.usage + '%' }"></i></span>
              <span>{{ item.usage }}%</span>
            </div>
            <div class="device-row" v-if="!devices.length"><span>暂无资源数据</span></div>
          </div>
        </section>
        <div class="overview-split-row">
          <section class="panel overview-section">
            <div class="event-chart-head">
              <h3>事件统计</h3>
              <select class="select" v-model="eventStatsRange" @change="loadEventStats"><option value="week">最近一周</option><option value="today">今日</option><option value="month">最近一月</option></select>
            </div>
            <div class="event-metric-grid">
              <div class="event-metric-card" v-for="item in eventMetrics" :key="item.label">
                <span>{{ item.label }}</span>
                <strong>{{ item.value }}</strong>
              </div>
            </div>
          </section>
          <section class="panel overview-section">
            <h3>高发事件</h3>
            <div class="event-hot-list">
              <div class="event-hot-row" v-for="item in hotEvents" :key="item.name">
                <span>{{ item.name }}</span>
                <span class="event-hot-track"><i class="event-hot-fill" :style="{ width: item.width + '%' }"></i></span>
                <strong>{{ item.value }}</strong>
              </div>
              <div class="event-hot-row" v-if="!hotEvents.length"><span>暂无事件数据</span></div>
            </div>
          </section>
        </div>
        <section class="panel overview-section">
          <div class="event-chart-head">
            <h3>有效事件发生情况</h3>
            <select class="select"><option>最近一周</option><option disabled>今日</option><option disabled>最近一月</option></select>
          </div>
          <div class="event-line-chart">
            <svg viewBox="0 0 800 224" preserveAspectRatio="none" aria-label="有效事件折线图">
              <defs><linearGradient id="eventLineFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#1677ff" stop-opacity=".18"/><stop offset="100%" stop-color="#1677ff" stop-opacity="0"/></linearGradient></defs>
              <path d="M 40 34 H 780 M 40 76 H 780 M 40 118 H 780 M 40 160 H 780 M 40 204 H 780" stroke="#eef2f7" stroke-width="1" fill="none"></path>
              <path :d="lineAreaPath" fill="url(#eventLineFill)"></path>
              <path :d="linePath" fill="none" stroke="#1677ff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"></path>
              <circle class="event-line-dot" v-for="point in lineSeries" :key="point.label" :cx="point.x" :cy="point.y" r="5" @mouseenter="showLineTip(point)" @mouseleave="hideLineTip"><title>{{ point.label }}：有效事件 {{ point.value }} 起</title></circle>
            </svg>
            <div class="event-hover-tip" :class="{ show: lineTip.show }" :style="{ left: lineTip.left + 'px', top: lineTip.top + 'px' }"><b>{{ lineTip.value }}</b><span>{{ lineTip.label }} 有效事件</span></div>
            <div class="event-line-axis"><span v-for="point in lineSeries" :key="point.label" :title="point.label + '：有效事件 ' + point.value + ' 起'" @mouseenter="showLineTip(point)" @mouseleave="hideLineTip">{{ point.label }}</span></div>
          </div>
        </section>
      </div>
      <aside class="overview-side-stack">
        <section class="panel overview-section">
          <div class="table-head" style="padding:0 0 12px; border-bottom:0;"><h3>搜索关键词</h3></div>
          <div class="keyword-cloud">
            <span class="keyword-chip" v-for="item in keywords" :key="item.keyword"># {{ item.keyword }}<b>{{ item.count }}</b></span>
            <span v-if="!keywords.length">暂无搜索记录</span>
          </div>
        </section>
        <div class="overview-card clickable" @click="setRoute(taskCard.route)">
          <div class="overview-card-head"><span>{{ taskCard.label }}</span><span class="overview-card-icon">{{ taskCard.icon }}</span></div>
          <strong>{{ taskCard.value }}<small>{{ taskCard.unit }}</small></strong>
          <p>{{ taskCard.desc }}</p>
        </div>
        <section class="panel overview-section">
          <h3>任务趋势</h3>
          <div class="task-rhythm">
            <div class="task-bar" v-for="item in taskBars" :key="item.day">
              <strong>{{ item.value }}</strong>
              <i :style="{ height: item.height + '%' }"></i>
              <span>{{ item.day }}</span>
            </div>
          </div>
        </section>
      </aside>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { api } from "../api";
import type { DeploymentEventStats, SearchKeywordStatItem } from "../types";

const WEEKDAY_LABELS = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"];

function formatNumber(value: number): string {
  return Number(value || 0).toLocaleString("zh-CN");
}

export default defineComponent({
  name: "OverviewPage",
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  // Prototype declares `inject: ["setRoute", "showToast"]`; aliased here and
  // re-exposed as methods so templates/methods keep calling them by name.
  inject: {
    setRouteImpl: { from: "setRoute", default: (_r: string, _o?: any) => {} },
    showToastImpl: { from: "showToast", default: (_m: string) => {} }
  },
  data() {
    return {
      cards: [
        { label: "算力", value: "0", unit: "台", desc: "数据加载中…", icon: "▰", route: "resource" },
        { label: "摄像头", value: "0", unit: "个", desc: "数据加载中…", icon: "▤", route: "cameraList" },
        // 录像设备 = 摄像头列表中关联 NVR（nvrId 非空）的设备
        { label: "录像设备", value: "0", unit: "台", desc: "数据加载中…", icon: "▣", route: "cameraList" },
        { label: "搜索关键词", value: "0", unit: "次", desc: "数据加载中…", icon: "⌕" }
      ] as any[],
      nvrDeviceTotal: 0,
      nvrDeviceToday: 0,
      eventUnreviewed: 0,
      // 总任务 = 事件存储表（deployment_events）中的事件总数；卡片放在右侧栏任务趋势上方
      taskCard: { label: "总任务", value: "0", unit: "个", desc: "数据加载中…", icon: "☑", route: "events" } as any,
      eventStatsRange: "week",
      devices: [] as any[],
      keywords: [] as { keyword: string; count: number }[],
      taskBars: [] as any[],
      eventMetrics: [
        { label: "原始事件", value: "0" },
        { label: "有效事件", value: "0" },
        { label: "过滤后事件", value: "0" },
        { label: "待复核", value: "0" }
      ] as any[],
      lineSeries: [] as any[],
      hotEvents: [] as any[],
      lineTip: {
        show: false,
        left: 0,
        top: 0,
        label: "",
        value: 0
      }
    };
  },
  computed: {
    linePath(): string {
      return this.lineSeries.map((point: any, index: number) => `${index === 0 ? "M" : "L"} ${point.x} ${point.y}`).join(" ");
    },
    lineAreaPath(): string {
      if (!this.lineSeries.length) return "";
      const start = this.lineSeries[0];
      const end = this.lineSeries[this.lineSeries.length - 1];
      return `${this.linePath} L ${end.x} 204 L ${start.x} 204 Z`;
    }
  },
  mounted() {
    this.loadAll();
  },
  methods: {
    setRoute(route: string, options?: any) {
      (this as any).setRouteImpl(route, options);
    },
    showToast(message: string) {
      (this as any).showToastImpl(message);
    },
    showLineTip(point: any) {
      this.lineTip = {
        show: true,
        left: point.x,
        top: Math.max(12, point.y - 56),
        label: point.label,
        value: point.value
      };
    },
    hideLineTip() {
      this.lineTip.show = false;
    },
    setCard(label: string, patch: any) {
      const card = this.cards.find((item: any) => item.label === label);
      if (card) Object.assign(card, patch);
    },
    markCardFailed(label: string) {
      if (label === this.taskCard.label) {
        this.taskCard.desc = "数据加载失败";
        return;
      }
      this.setCard(label, { desc: "数据加载失败" });
    },
    async loadAll() {
      const [workers, cameras, summary, stats, keywordStats] = await Promise.allSettled([
        api.workerNodes(),
        api.cameras(),
        api.deploymentEventSummary(),
        api.deploymentEventStats(),
        api.searchKeywordStats(100)
      ]);
      if (workers.status === "fulfilled") this.applyWorkerNodes(workers.value);
      else {
        console.error("加载 worker 节点失败", workers.reason);
        this.markCardFailed("算力");
      }
      if (cameras.status === "fulfilled") this.applyCameras(cameras.value);
      else {
        console.error("加载摄像头失败", cameras.reason);
        this.markCardFailed("摄像头");
        this.markCardFailed("录像设备");
      }
      if (summary.status === "fulfilled" || stats.status === "fulfilled") {
        this.applyEventStats(
          summary.status === "fulfilled" ? summary.value : null,
          stats.status === "fulfilled" ? stats.value : null
        );
      } else {
        console.error("加载事件统计失败", summary.status === "rejected" ? summary.reason : (stats as PromiseRejectedResult).reason);
        this.markCardFailed("总任务");
      }
      if (keywordStats.status === "fulfilled") this.applyKeywordStats(keywordStats.value);
      else {
        console.error("加载搜索关键词失败", keywordStats.reason);
        this.markCardFailed("搜索关键词");
      }
    },
    // 资源负载：与资源监控页（ResourcePage）同源的 worker 心跳数据
    applyWorkerNodes(nodes: any[]) {
      const online = nodes.filter((node) => node.status === "在线");
      const busy = nodes.filter((node) => node.gpus.some((gpu: any) => gpu.status === "繁忙"));
      this.setCard("算力", {
        value: formatNumber(nodes.length),
        desc: `${online.length} 台在线，${busy.length} 台繁忙`
      });
      const onlineGpus = online.flatMap((node) => node.gpus);
      const avgUtil = onlineGpus.length
        ? Math.round(onlineGpus.reduce((sum: number, gpu: any) => sum + gpu.utilizationPct, 0) / onlineGpus.length)
        : 0;
      // CPU/内存/磁盘取在线节点的平均值；旧版 worker 不上报系统指标（全零）时不参与平均
      const withSystem = online.filter((node) => node.system && (node.system.memoryTotalMb > 0 || node.system.diskTotalGb > 0));
      const avgSystem = (pick: (system: any) => number) =>
        withSystem.length
          ? Math.min(100, Math.round(withSystem.reduce((sum: number, node: any) => sum + pick(node.system), 0) / withSystem.length))
          : 0;
      this.devices = [
        { name: "CPU 使用率", usage: avgSystem((system) => system.cpuPercent) },
        { name: "内存使用率", usage: avgSystem((system) => (system.memoryTotalMb ? (system.memoryUsedMb / system.memoryTotalMb) * 100 : 0)) },
        { name: "磁盘使用率", usage: avgSystem((system) => (system.diskTotalGb ? (system.diskUsedGb / system.diskTotalGb) * 100 : 0)) },
        { name: "GPU 算力利用率", usage: avgUtil }
      ];
    },
    applyCameras(cameras: any[]) {
      const statusOf = (camera: any) => String(camera.status || "").toUpperCase();
      const online = cameras.filter((camera) => statusOf(camera) === "RUNNING").length;
      const disabled = cameras.filter((camera) => statusOf(camera) === "DISABLED").length;
      const abnormal = cameras.length - online - disabled;
      this.setCard("摄像头", {
        value: formatNumber(cameras.length),
        desc: `在线 ${online} 路，异常 ${abnormal} 路`
      });
      // 录像设备卡：关联 NVR 的设备数；今日新增按 createdAt 本地日期判断
      const nvrDevices = cameras.filter((camera) => camera.nvrId);
      const todayText = new Date().toDateString();
      this.nvrDeviceTotal = nvrDevices.length;
      this.nvrDeviceToday = nvrDevices.filter((camera) => camera.createdAt && new Date(camera.createdAt).toDateString() === todayText).length;
      this.updateNvrCard();
    },
    updateNvrCard() {
      this.setCard("录像设备", {
        value: formatNumber(this.nvrDeviceTotal),
        desc: `今日新增 ${formatNumber(this.nvrDeviceToday)}，待复核 ${formatNumber(this.eventUnreviewed)}`
      });
    },
    applyEventStats(summary: { total: number; today: number } | null, stats: DeploymentEventStats | null) {
      // 总任务 = 事件存储表全量条数，取 summary.total；stats 接口默认只统计近 7 天
      const total = summary?.total ?? stats?.total ?? 0;
      const today = summary?.today ?? stats?.today ?? 0;
      const unreviewed = stats?.unreviewed ?? 0;
      this.eventUnreviewed = unreviewed;
      this.updateNvrCard();
      Object.assign(this.taskCard, {
        value: formatNumber(total),
        desc: `今日新增 ${formatNumber(today)}，待复核 ${formatNumber(unreviewed)}`
      });
      if (!stats) return;
      this.applyEventMetrics(stats);
      this.applyTrend(stats.trend.slice(-7));
      this.applyHotEvents(stats);
    },
    // 事件统计四宫格：原始/有效/过滤/待复核（随右上角时间段下拉变化）
    applyEventMetrics(stats: DeploymentEventStats) {
      const valid = stats.reviewByType.reduce((sum, item) => sum + item.valid, 0);
      const invalid = stats.reviewByType.reduce((sum, item) => sum + item.invalid, 0);
      this.eventMetrics = [
        { label: "原始事件", value: formatNumber(stats.total) },
        { label: "有效事件", value: formatNumber(valid) },
        { label: "过滤后事件", value: formatNumber(invalid) },
        { label: "待复核", value: formatNumber(stats.unreviewed) }
      ];
    },
    // 事件统计时间段下拉：今日 / 最近一周 / 最近一月，联动事件统计与高发事件
    async loadEventStats() {
      const now = new Date();
      const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
      const rangeDays: Record<string, number> = { today: 0, week: 6, month: 29 };
      const start = new Date(startOfToday);
      start.setDate(start.getDate() - (rangeDays[this.eventStatsRange] ?? 6));
      try {
        const stats = await api.deploymentEventStats({
          startTime: start.toISOString(),
          endTime: now.toISOString()
        });
        this.applyEventMetrics(stats);
        this.applyHotEvents(stats);
      } catch (error) {
        console.error("加载事件统计失败", error);
        this.showToast("事件统计加载失败");
      }
    },
    applyTrend(trend: { date: string; count: number }[]) {
      const max = Math.max(1, ...trend.map((item) => item.count));
      const step = trend.length > 1 ? 720 / (trend.length - 1) : 0;
      this.lineSeries = trend.map((item, index) => ({
        label: item.date.slice(5).replace("-", "/"),
        x: Math.round(40 + step * index),
        y: Math.round(204 - (item.count / max) * 170),
        value: item.count
      }));
      this.taskBars = trend.map((item) => ({
        day: WEEKDAY_LABELS[new Date(`${item.date}T00:00:00`).getDay()],
        value: item.count,
        height: Math.max(item.count > 0 ? 6 : 2, Math.round((item.count / max) * 100))
      }));
    },
    applyHotEvents(stats: DeploymentEventStats) {
      const rows = stats.reviewByType
        .map((item) => ({ name: item.eventType, value: item.valid + item.invalid + item.unreviewed }))
        .filter((item) => item.value > 0)
        .sort((a, b) => b.value - a.value)
        .slice(0, 6);
      const max = Math.max(1, ...rows.map((item) => item.value));
      this.hotEvents = rows.map((item) => ({ ...item, width: Math.max(6, Math.round((item.value / max) * 100)) }));
    },
    applyKeywordStats(items: SearchKeywordStatItem[]) {
      const totalSearches = items.reduce((sum, item) => sum + item.count, 0);
      this.setCard("搜索关键词", {
        value: formatNumber(totalSearches),
        desc: "累计检索次数"
      });
      // 词云取 Top 10（页面最多展示 4 行，超出由 CSS 隐藏）
      this.keywords = items.slice(0, 10).map((item) => ({ keyword: item.keyword, count: item.count }));
    }
  }
});
</script>
