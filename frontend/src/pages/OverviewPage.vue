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
          </div>
        </section>
        <section class="panel overview-section">
          <h3>今日各类型事件统计</h3>
          <div class="event-metric-grid">
            <div class="event-metric-card" v-for="item in eventMetrics" :key="item.label">
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
            </div>
          </div>
        </section>
        <section class="panel overview-section">
          <div class="event-chart-head">
            <h3>有效事件发生情况</h3>
            <select class="select"><option>最近一周</option><option>今日</option><option>最近一月</option></select>
          </div>
          <div class="event-line-chart">
            <svg viewBox="0 0 800 224" preserveAspectRatio="none" aria-label="有效事件折线图">
              <defs><linearGradient id="eventLineFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#1677ff" stop-opacity=".18"/><stop offset="100%" stop-color="#1677ff" stop-opacity="0"/></linearGradient></defs>
              <path d="M 40 34 H 780 M 40 76 H 780 M 40 118 H 780 M 40 160 H 780 M 40 204 H 780" stroke="#eef2f7" stroke-width="1" fill="none"></path>
              <path :d="lineAreaPath" fill="url(#eventLineFill)"></path>
              <path :d="linePath" fill="none" stroke="#1677ff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"></path>
              <circle class="event-line-dot" v-for="point in lineSeries" :key="point.x" :cx="point.x" :cy="point.y" r="5" @mouseenter="showLineTip(point)" @mouseleave="hideLineTip"><title>{{ point.label }}：有效事件 {{ point.value }} 起</title></circle>
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
            <span class="keyword-chip" v-for="word in keywords" :key="word"># {{ word }}</span>
          </div>
        </section>
        <section class="panel overview-section">
          <h3>近 7 日任务趋势</h3>
          <div class="task-rhythm">
            <div class="task-bar" v-for="item in taskBars" :key="item.day">
              <strong>{{ item.value }}</strong>
              <i :style="{ height: item.height + '%' }"></i>
              <span>{{ item.day }}</span>
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
          </div>
        </section>
      </aside>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";

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
        { label: "算力", value: "24", unit: "台", desc: "21 台在线，3 台繁忙", icon: "▰" },
        { label: "摄像头", value: "386", unit: "个", desc: "在线率 96.8%，异常 12 路", icon: "▤", route: "cameraList" },
        { label: "总任务", value: "1,284", unit: "个", desc: "今日新增 68，待复核 23", icon: "☑", route: "reviewTasks" },
        { label: "搜索关键词", value: "7,932", unit: "个", desc: "近 7 日检索次数", icon: "⌕" }
      ] as any[],
      devices: [
        { name: "服务器", usage: 86, status: "运行中" },
        { name: "GPU", usage: 64, status: "繁忙" },
        { name: "CPU", usage: 72, status: "运行中" },
        { name: "磁盘", usage: 48, status: "空闲" }
      ],
      keywords: ["白色车辆", "人员聚集", "未戴安全帽", "烟火检测", "访客轨迹", "车辆逆行", "园区南门", "蓝色工服", "相似目标", "夜间徘徊"],
      taskBars: [
        { day: "周一", value: 58, height: 52 },
        { day: "周二", value: 76, height: 70 },
        { day: "周三", value: 64, height: 60 },
        { day: "周四", value: 92, height: 86 },
        { day: "周五", value: 83, height: 78 },
        { day: "周六", value: 49, height: 46 },
        { day: "周日", value: 38, height: 36 }
      ],
      eventMetrics: [
        { label: "有效事件", value: "9" },
        { label: "研判后事件", value: "89" },
        { label: "过滤后事件", value: "259" },
        { label: "原始事件", value: "999" }
      ],
      lineSeries: [
        { label: "07/18", x: 40, y: 168, value: 18 },
        { label: "07/19", x: 160, y: 144, value: 26 },
        { label: "07/20", x: 280, y: 158, value: 21 },
        { label: "07/21", x: 400, y: 92, value: 43 },
        { label: "07/22", x: 520, y: 116, value: 35 },
        { label: "07/23", x: 640, y: 70, value: 51 },
        { label: "07/24", x: 760, y: 108, value: 38 }
      ],
      hotEvents: [
        { name: "人员入侵", value: 128, width: 86 },
        { name: "车辆违停", value: 93, width: 63 },
        { name: "烟火检测", value: 67, width: 45 },
        { name: "安全帽", value: 57, width: 38 },
        { name: "垃圾识别", value: 38, width: 26 },
        { name: "抽烟", value: 27, width: 18 }
      ],
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
      const start = this.lineSeries[0];
      const end = this.lineSeries[this.lineSeries.length - 1];
      return `${this.linePath} L ${end.x} 204 L ${start.x} 204 Z`;
    }
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
    }
  }
});
</script>
