<template>
  <section class="content review-wide">
    <div class="review-titlebar"><div><h1>资源监控</h1><p>查看服务器、设备 MN 号与 GPU 算力占用情况</p></div></div>
    <summary-cards :cards="cards"></summary-cards>
    <div class="review-board">
      <div class="page-actions"><div class="left"><button class="btn" @click="showToast('已根据当前条件刷新演示结果')">查询</button><button class="btn">重置</button><input class="input" style="width:220px;" placeholder="搜索服务器IP、设备MN号" /><select class="select" style="width:140px;"><option>全部状态</option><option>在线</option><option>离线</option></select></div></div>
      <table class="prototype-table resource-table">
        <colgroup><col style="width:210px;" /><col style="width:210px;" /><col style="width:110px;" /><col style="width:210px;" /><col /></colgroup>
        <thead><tr><th>服务器IP</th><th>设备MN号</th><th>状态</th><th>最后更新时间</th><th>操作</th></tr></thead>
        <tbody>
          <template v-for="row in store.resourceRows" :key="row.mn">
            <tr class="resource-device-row" @click="toggleResource(row)">
              <td>{{ row.ip }}</td><td>{{ row.mn }}</td><td><span class="status-pill" :class="statusClass(row.status)">{{ row.status }}</span></td><td>{{ row.updated }}</td><td><button class="link-blue" @click.stop="toggleResource(row)">{{ expandedMn === row.mn ? "收起GPU" : "查看GPU" }}</button><button class="link-blue" @click.stop="showToast('已模拟刷新单台设备状态')">刷新</button></td>
            </tr>
            <tr v-if="expandedMn === row.mn">
              <td class="gpu-detail-cell" colspan="5">
                <div class="gpu-grid">
                  <article class="gpu-card" v-for="gpu in row.gpus" :key="gpu.name">
                    <div class="gpu-head"><h4>{{ gpu.name }}</h4><span class="status-pill" :class="statusClass(gpu.status)">{{ gpu.status }}</span></div>
                    <div class="gpu-metrics">
                      <div class="gpu-metric"><span>显存</span><span class="progress-track"><span class="progress-fill" :style="{ width: gpu.memory + '%' }"></span></span><b>{{ gpu.memoryText }}</b></div>
                      <div class="gpu-metric"><span>温度</span><span>{{ gpu.temperature }}</span><b></b></div>
                      <div class="gpu-metric"><span>功耗</span><span>{{ gpu.power }}</span><b></b></div>
                    </div>
                  </article>
                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import SummaryCards from "../components/SummaryCards.vue";

export default defineComponent({
  name: "ResourcePage",
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  components: { SummaryCards },
  // Aliased injection + same-named method wrapper so the template type-checks;
  // runtime behavior matches the prototype's `inject: ["showToast"]`.
  inject: {
    showToastImpl: { from: "showToast" }
  },
  data() {
    return { expandedMn: "MN24010001" };
  },
  computed: {
    cards() {
      const totalGpu = this.store.resourceRows.reduce((sum: number, row: any) => sum + row.gpus.length, 0);
      const busyGpu = this.store.resourceRows.reduce((sum: number, row: any) => sum + row.gpus.filter((gpu: any) => gpu.status === "繁忙").length, 0);
      return [
        { label: "总设备数", value: this.store.resourceRows.length },
        { label: "在线设备", value: this.store.resourceRows.filter((row: any) => row.status === "在线").length },
        { label: "总算力", value: this.store.resourceRows.filter((row: any) => row.status === "离线").length },
        { label: "总GPU数", value: totalGpu },
        { label: "繁忙GPU", value: busyGpu }
      ];
    }
  },
  methods: {
    showToast(msg: string) {
      (this as any).showToastImpl(msg);
    },
    toggleResource(row: any) {
      this.expandedMn = this.expandedMn === row.mn ? "" : row.mn;
    }
  }
});
</script>
