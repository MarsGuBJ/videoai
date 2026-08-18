<template>
  <section class="content review-wide">
    <div class="review-titlebar"><div><h1>布控任务详情</h1><p>查看布控任务配置、运行状态、告警记录和关联点位</p></div><div class="segmented"><button class="btn" @click="setRoute('deployTasks')">返回列表</button><button class="btn primary" @click="openModal('deployTask')">编辑任务</button></div></div>
    <div class="detail-header-card"><div><h2>{{ selectedDeployTask?.name || '—' }}</h2><p>{{ selectedDeployTask?.desc || '—' }}</p><div class="tags"><span class="tag blue">{{ selectedDeployTask?.algorithm || '—' }}</span><span class="status-pill" :class="statusClass(selectedDeployTask?.status)">{{ selectedDeployTask?.status || '—' }}</span><span class="tag">{{ selectedDeployTask?.area || '—' }}</span></div></div><div class="segmented"><button class="btn" @click="showToast('布控任务状态已模拟切换')">启停任务</button><button class="btn primary" @click="showToast('已根据当前条件刷新演示结果')">刷新状态</button></div></div>
    <div class="detail-grid">
      <div class="panel search-panel"><h3 class="form-section-title">任务信息</h3><dl class="info-list"><dt>任务ID</dt><dd>{{ selectedDeployTask?.id || '—' }}</dd><dt>算法类型</dt><dd>{{ selectedDeployTask?.algorithm || '—' }}</dd><dt>布控区域</dt><dd>{{ selectedDeployTask?.area || '—' }}</dd><dt>监控点位</dt><dd>{{ selectedDeployTask?.points || '—' }}</dd><dt>生效时间</dt><dd>{{ selectedDeployTask?.time || '—' }}</dd><dt>相似度</dt><dd>{{ selectedDeployTask?.threshold ?? '—' }}%</dd><dt>创建人</dt><dd>{{ selectedDeployTask?.owner || '—' }}</dd><dt>创建时间</dt><dd>{{ selectedDeployTask?.created || '—' }}</dd></dl></div>
      <div class="panel search-panel"><h3 class="form-section-title">告警概览</h3><dl class="info-list"><dt>今日告警</dt><dd>{{ selectedDeployTask?.alerts ?? '—' }} 条</dd><dt>高优先级</dt><dd>3 条</dd><dt>复核通过</dt><dd>6 条</dd><dt>通知方式</dt><dd>平台弹窗、消息推送</dd><dt>最新告警</dt><dd>2026-07-16 14:32:08</dd></dl></div>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";

// Injected by App.vue via provide(); declared here so vue-tsc accepts
// template calls to the injected members.
declare module "vue" {
  interface ComponentCustomProperties {
    setRoute: (route: string, options?: any) => void;
    openModal: (key: string, payload?: any) => void;
    showToast: (m: string) => void;
  }
}

export default defineComponent({
  name: "DeployTaskDetailPage",
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  inject: {
    setRoute: { from: "setRoute", default: (route: string, options?: any) => {} },
    openModal: { from: "openModal", default: (key: string, payload?: any) => {} },
    showToast: { from: "showToast", default: (m: string) => {} },
  },
});
</script>
