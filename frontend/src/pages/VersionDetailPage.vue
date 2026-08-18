<template>
  <section class="content review-wide">
    <div class="review-titlebar"><div><h1>版本号详情</h1><p>查看版本基础信息、文件清单、配置参数与发布状态</p></div><div class="segmented"><button class="btn" @click="setRoute('versionManager')">返回列表</button><button class="btn primary" @click="setRoute('previewFile')">预览文件</button></div></div>
    <div class="detail-header-card"><div><h2>{{ selectedVersion.algorithm }} {{ selectedVersion.version }}</h2><p>{{ selectedVersion.desc }}</p><div class="tags"><span class="tag blue">{{ selectedVersion.name }}</span><span class="status-pill" :class="statusClass(selectedVersion.status)">{{ selectedVersion.status }}</span></div></div><div class="segmented"><button class="btn" @click="showToast('版本已进入编辑状态')">编辑版本</button><button class="btn primary" @click="showToast('版本已发布，状态已模拟更新')">发布版本</button></div></div>
    <div class="detail-grid">
      <div class="panel search-panel"><h3 class="form-section-title">基础信息</h3><dl class="info-list"><dt>版本ID</dt><dd>{{ selectedVersion.id }}</dd><dt>所属算法</dt><dd>{{ selectedVersion.algorithm }}</dd><dt>版本号</dt><dd>{{ selectedVersion.version }}</dd><dt>创建人</dt><dd>{{ selectedVersion.creator }}</dd><dt>创建时间</dt><dd>{{ selectedVersion.created }}</dd><dt>版本文件</dt><dd>{{ selectedVersion.file }}</dd></dl></div>
      <div class="panel search-panel"><h3 class="form-section-title">运行参数</h3><dl class="info-list"><dt>运行环境</dt><dd>Python 3.10 / CUDA 12.1</dd><dt>置信度</dt><dd>0.75</dd><dt>IoU阈值</dt><dd>0.45</dd><dt>最大批次</dt><dd>8</dd><dt>发布范围</dt><dd>园区周界、楼宇入口</dd></dl></div>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";

// Loose typing for App-level provides, so vue-tsc accepts injected members
// used in the template (same pattern as other migrated pages).
declare module "vue" {
  interface ComponentCustomProperties {
    setRoute: (route: string, options?: any) => void;
    showToast: (m: string) => void;
  }
}

export default defineComponent({
  name: "VersionDetailPage",
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  inject: {
    setRoute: { from: "setRoute", default: (route: string, options?: any) => {} },
    showToast: { from: "showToast", default: (m: string) => {} },
  },
});
</script>
