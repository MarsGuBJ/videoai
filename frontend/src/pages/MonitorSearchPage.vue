<script lang="ts">
import { defineComponent } from "vue";
import VideoResults from "../components/VideoResults.vue";

export default defineComponent({
  name: "MonitorSearchPage",
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  components: { VideoResults },
  // Aliased injection + same-named method wrapper (see VideoResults.vue).
  inject: {
    showToastImpl: { from: "showToast" }
  },
  methods: {
    showToast(m: string) {
      (this as any).showToastImpl(m);
    }
  }
});
</script>

<template>
  <section class="content wide">
    <div class="title-row"><span class="module-icon">▤</span><div><h1 class="page-title">监控搜索</h1><p class="page-subtitle">多模态融合搜索与布控</p></div></div>
    <div class="panel search-panel">
      <div class="field-row"><div class="field-label">搜索模式</div><div class="segmented"><button class="btn ghost">文本查询</button><button class="btn">图片查询</button><button class="btn">轨迹查询</button></div></div>
      <div class="field-row"><div class="field-label">搜索描述</div><textarea class="textarea">用自然语言描述搜索监控视频片段。</textarea></div>
      <div class="field-row"><div class="field-label">上传资料</div><button class="btn" @click="showToast('静态原型：此处模拟上传入口')">上传</button></div>
      <div class="button-row"><button class="btn">清空</button><button class="btn primary" @click="showToast('已根据当前条件刷新演示结果')">⌕ 开始搜索</button></div>
    </div>
    <div class="result-count">搜索完成后，可从结果详情继续进行图搜图、快速布防或轨迹还原。</div>
    <video-results :items="store.results.slice(0, 3)"></video-results>
  </section>
</template>
