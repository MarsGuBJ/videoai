<template>
  <section class="content review-wide">
    <div class="review-titlebar"><div><h1>事件统计</h1><p>按时间、类型、区域和处置状态统计视觉事件</p></div></div>
    <summary-cards :cards="cards"></summary-cards>
    <div class="review-board">
    <div class="page-actions"><div class="left"><input class="input" style="width:150px;" value="2026-07-10" /><input class="input" style="width:150px;" value="2026-07-16" /><select class="select" style="width:150px;"><option>全部区域</option><option>园区南门</option><option>A座停车区</option><option>仓储区</option></select></div></div>
      <div class="stats-layout">
        <div class="chart-panel"><h3>近7日事件趋势</h3><div class="bar-chart"><div class="bar-item" v-for="item in store.eventTrend" :key="item.label"><span>{{ item.value }}</span><span class="bar" :style="{ height: Math.round(item.value / trendMax * 160) + 'px' }"></span><span>{{ item.label }}</span></div></div></div>
        <div class="chart-panel"><h3>事件类型分布</h3><div class="stat-row" v-for="item in store.eventTypeStats" :key="item.label"><span>{{ item.label }}</span><span class="progress-track"><span class="progress-fill" :style="{ width: Math.round(item.value / typeMax * 100) + '%' }"></span></span><b>{{ item.value }}</b></div></div>
        <div class="chart-panel"><h3>区域事件排行</h3><div class="rank-list"><div class="rank-item" v-for="(item, index) in [{label:'园区南门',value:38},{label:'A座停车区',value:26},{label:'仓储区',value:19},{label:'园区北门',value:15},{label:'园区周界',value:12}]" :key="item.label"><span class="rank-no">{{ index + 1 }}</span><span>{{ item.label }}</span><strong>{{ item.value }} 起</strong></div></div></div>
        <div class="chart-panel review-event-panel"><h3>复核事件统计</h3><div class="review-event-legend" aria-label="图例"><span><i></i>有效</span><span><i class="invalid"></i>无效</span></div><div class="review-event-chart" role="img" aria-label="按事件类型统计的有效和无效复核事件数量"><div class="review-event-y-axis"><span>{{ reviewMax }}</span><span>{{ Math.ceil(reviewMax * 2 / 3) }}</span><span>{{ Math.ceil(reviewMax / 3) }}</span><span>0</span></div><div class="review-event-plot"><div class="review-event-group" v-for="item in reviewEventStats" :key="item.label"><div class="review-event-bars"><span class="review-event-bar valid" :style="{ height: Math.max(7, Math.round(item.valid / reviewMax * 154)) + 'px' }" :title="item.label + '：有效 ' + item.valid + ' 起'"><b>{{ item.valid }}</b></span><span class="review-event-bar invalid" :style="{ height: Math.max(7, Math.round(item.invalid / reviewMax * 154)) + 'px' }" :title="item.label + '：无效 ' + item.invalid + ' 起'"><b>{{ item.invalid }}</b></span></div><span class="review-event-label">{{ item.label }}</span></div></div></div></div>
      </div>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import SummaryCards from "../components/SummaryCards.vue";

export default defineComponent({
  name: "StatsPage",
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  components: { SummaryCards },
  computed: {
    cards() {
      return [
        { label: "今日事件", value: 42 },
        { label: "本周事件", value: (this as any).store.eventTrend.reduce((sum: number, item: any) => sum + item.value, 0) },
        { label: "高等级事件", value: (this as any).store.eventRows.filter((row: any) => row.level === "高").length },
        { label: "复核率", value: "78%" }
      ];
    },
    trendMax(): number {
      return Math.max(...(this as any).store.eventTrend.map((item: any) => item.value));
    },
    typeMax(): number {
      return Math.max(...(this as any).store.eventTypeStats.map((item: any) => item.value));
    },
    reviewEventStats(): any[] {
      return (this as any).store.eventTypeStats.map((item: any, index: number) => {
        const invalid = Math.max(1, Math.round(item.value * [0.32, 0.29, 0.31, 0.38, 0.33][index % 5]));
        return { label: item.label, valid: item.value - invalid, invalid };
      });
    },
    reviewMax(): number {
      return Math.max(...(this as any).reviewEventStats.flatMap((item: any) => [item.valid, item.invalid]));
    }
  }
});
</script>
