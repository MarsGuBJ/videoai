<template>
  <section class="content review-wide">
    <div class="review-titlebar"><div><h1>预览文件</h1><p>{{ selectedVersion.algorithm }} {{ selectedVersion.version }} 的版本文件预览</p></div><div class="segmented"><button class="btn" @click="setRoute('versionDetail')">返回详情</button><button class="btn primary" @click="showToast('文件下载已模拟触发')">下载文件</button></div></div>
    <div class="preview-layout">
      <div class="panel"><div class="table-head"><h3>文件列表</h3></div><div class="file-list"><button class="file-row active">{{ selectedVersion.file }}<br /><span class="hint-text">模型包</span></button><button class="file-row">config.yaml<br /><span class="hint-text">配置文件</span></button><button class="file-row">README.md<br /><span class="hint-text">说明文档</span></button></div></div>
      <div class="panel search-panel"><div class="table-head" style="padding:0 0 12px; margin-bottom:12px;"><h3>config.yaml</h3><span class="hint-text">静态预览内容</span></div><pre class="code-preview">algorithm:
  name: {{ selectedVersion.algorithm }}
  version: {{ selectedVersion.version }}
  package: {{ selectedVersion.file }}
runtime:
  python: "3.10"
  cuda: "12.1"
  device: "gpu"
parameters:
  confidence: 0.75
  iou_threshold: 0.45
  max_batch_size: 8</pre></div>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";

export default defineComponent({
  name: "PreviewFilePage",
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  // Aliased injection + same-named method wrappers so the template type-checks;
  // runtime behavior matches the prototype's `inject: ["setRoute", "showToast"]`.
  inject: {
    setRouteImpl: { from: "setRoute" },
    showToastImpl: { from: "showToast" },
  },
  methods: {
    setRoute(route: string, options?: any) {
      (this as any).setRouteImpl(route, options);
    },
    showToast(msg: string) {
      (this as any).showToastImpl(msg);
    },
  },
});
</script>
