<template>
  <section class="content review-wide">
    <div class="review-titlebar"><div><h1>大模型配置</h1><p>维护用于事件复核、告警解释与结构化研判的大模型服务</p></div></div>
    <summary-cards :cards="cards"></summary-cards>
    <div class="review-board">
      <div class="page-actions"><div class="left"><button class="btn primary" @click="openModal('modelConfig')">新增配置</button><button class="btn" @click="showToast('已根据当前条件刷新演示结果')">查询</button><button class="btn">重置</button><input class="input" style="width:260px;" placeholder="请输入名称" /><select class="select" style="width:150px;"><option>全部状态</option><option>运行良好</option><option>离线</option></select><select class="select" style="width:150px;"><option>全部部署方式</option><option>云端服务</option><option>本地部署</option></select></div></div>
      <div class="model-grid">
        <article class="model-card" v-for="row in store.modelConfigRows" :key="row.name">
          <div class="model-head">
            <div class="model-title"><span class="model-logo">AI</span><div><h3>{{ row.name }}</h3><p>{{ row.provider }}</p></div></div>
            <span class="status-pill" :class="statusClass(row.status)">{{ row.status }}</span>
          </div>
          <div class="model-metrics">
            <div class="model-metric"><span>平均时延</span><b>{{ row.latency }}</b></div>
            <div class="model-metric"><span>并发限制</span><b>{{ row.concurrency }}</b></div>
          </div>
          <div class="model-meta">
            <span>部署方式</span><span>{{ row.deploy }}</span>
            <span>服务地址</span><span class="ellipsis">{{ row.url }}</span>
            <span>检测时间</span><span>{{ row.checked }}</span>
          </div>
          <div class="button-row" style="margin-top:14px;"><button class="btn" :class="row.status === '离线' ? 'primary' : ''" style="margin-right:auto;" @click="showToast(row.status === '离线' ? '已模拟启动模型服务' : '已模拟停止模型服务')">{{ row.status === '离线' ? '启动' : (row.status === '运行良好' ? '停止' : '启动') }}</button><button class="btn" @click="showToast('已模拟检测模型连接')">连接检测</button><button class="btn primary" @click="openModal('modelConfig')">编辑配置</button></div>
        </article>
      </div>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import SummaryCards from "../components/SummaryCards.vue";

export default defineComponent({
  name: "ModelConfigPage",
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  components: { SummaryCards },
  inject: {
    openModal: { from: "openModal", default: (key: string) => {} },
    showToast: { from: "showToast", default: (m: string) => {} }
  },
  computed: {
    cards(): any[] {
      return [
        { label: "配置总数", value: this.store.modelConfigRows.length },
        { label: "运行良好", value: this.store.modelConfigRows.filter((row: any) => row.status === "运行良好").length },
        { label: "云端服务", value: this.store.modelConfigRows.filter((row: any) => row.deploy === "云端服务").length },
        { label: "本地部署", value: this.store.modelConfigRows.filter((row: any) => row.deploy === "本地部署").length }
      ];
    }
  }
});
</script>
