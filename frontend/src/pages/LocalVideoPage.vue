<template>
  <section class="content wide">
    <div class="title-row"><span class="module-icon">▣</span><div><h1 class="page-title">视频分析</h1><p class="page-subtitle">上传本地视频文件进行离线智能分析，自动提取关键帧、目标、事件和时间线。</p></div></div>
    <div class="local-video-layout">
      <div class="panel local-upload-panel">
        <div class="local-source-head">
          <div class="segmented"><button class="btn" @click="setRoute('monitorSearch')">在线监控</button><button class="btn ghost">本地上传</button></div>
          <span class="hint-text">支持 mp4 / mov / avi / mkv</span>
        </div>
        <input ref="localVideoInput" class="hidden-file-input" type="file" accept="video/*" @change="onFileChange" />
        <div class="local-dropzone" :class="{ clickable: !videoUrl }" @click="!videoUrl && triggerUpload()" @dragover.prevent @drop.prevent="handleDrop">
          <video v-if="videoUrl" class="local-video-player" :src="videoUrl" controls muted playsinline @click.stop></video>
          <span v-else><span class="upload-mark">＋</span><br />点击上传本地视频<br /><span class="hint-text">或将视频文件拖拽到此区域</span></span>
        </div>
        <div class="local-file-meta">
          <span>{{ fileName || "未选择本地视频" }}</span>
          <span>{{ fileSize || "等待上传" }}</span>
        </div>
        <div class="local-control-grid">
          <div class="deploy-field"><label>分析算法</label><select class="select"><option>通用视频理解模型</option><option>目标识别与跟踪</option><option>异常事件检测</option></select></div>
          <div class="deploy-field"><label>抽帧策略</label><select class="select"><option>智能抽帧</option><option>每 1 秒抽帧</option><option>关键场景抽帧</option></select></div>
        </div>
        <div class="field-row" style="grid-template-columns:72px 1fr; margin-top:14px;">
          <div class="field-label">分析要求</div>
          <textarea class="textarea">识别视频中的人员、车辆、异常行为和关键时间点，生成可复核的结构化分析说明。</textarea>
        </div>
        <div class="button-row">
          <button class="btn" @click="clearVideo">清空</button>
          <button class="btn" @click="triggerUpload">{{ videoUrl ? "重新上传" : "选择视频" }}</button>
          <button class="btn primary" @click="startAnalyze">开始分析</button>
        </div>
      </div>
      <aside class="panel local-analysis-panel">
        <div class="table-head" style="padding:0 0 12px; border-bottom:0;">
          <h3>分析结果</h3>
          <span class="status-pill" :class="analyzed ? 'pass' : 'waiting'">{{ analyzed ? "已完成" : "待分析" }}</span>
        </div>
        <div class="analysis-state">
          <div class="analysis-row"><span>视频来源</span><strong>{{ fileName ? "本地上传" : "待上传" }}</strong></div>
          <div class="analysis-row"><span>关键帧</span><strong>{{ analyzed ? "12 帧" : "-" }}</strong></div>
          <div class="analysis-row"><span>识别目标</span><strong>{{ analyzed ? "人员 3 / 车辆 1" : "-" }}</strong></div>
          <div class="analysis-row"><span>异常事件</span><strong>{{ analyzed ? "1 条待复核" : "-" }}</strong></div>
        </div>
        <div class="config-note" style="margin-top:14px;">
          <strong>分析说明</strong>
          <span>{{ analyzed ? "系统识别到视频中 00:18 位置出现人员进入限制区域，00:32 位置出现车辆短暂停留，建议生成复核任务继续确认。" : "上传视频并点击开始分析后，将在此处展示目标、事件、关键帧和时间线结果。" }}</span>
        </div>
        <div class="keyframe-grid">
          <div class="keyframe-card" v-for="item in store.results.slice(0, 3)" :key="item.title">
            <img :src="item.image" :alt="item.title" />
            <span>{{ analyzed ? item.date.slice(11, 19) + " · " + item.location : "待生成" }}</span>
          </div>
        </div>
        <div class="action-grid four">
          <button class="btn primary" @click="showToast('已模拟生成复核任务')">生成复核任务</button>
          <button class="btn primary" @click="setRoute('quickDeploy')">快速布防</button>
          <button class="btn" @click="showToast('分析报告已模拟导出')">导出报告</button>
          <button class="btn" @click="setRoute('home')">返回首页</button>
        </div>
      </aside>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";

// The prototype accesses injected members (setRoute/showToast) directly in the
// template; vue-tsc does not infer inject keys onto the template `this`, so
// merge them into ComponentCustomProperties (type-level only, runtime inject
// declarations below stay exactly as the prototype).
declare module "vue" {
  interface ComponentCustomProperties {
    setRoute: (route: string, options?: any) => void;
    showToast: (message: string) => void;
  }
}

export default defineComponent({
  name: "LocalVideoPage",
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  inject: {
    showToast: { from: "showToast", default: (m: string) => {} },
    setRoute: { from: "setRoute", default: (route: string, options?: any) => {} },
  },
  data() {
    return {
      fileName: "",
      fileSize: "",
      videoUrl: "",
      analyzed: false
    };
  },
  methods: {
    triggerUpload() {
      (this.$refs.localVideoInput as HTMLInputElement).click();
    },
    handleDrop(event: DragEvent) {
      const file = event.dataTransfer?.files && event.dataTransfer.files[0];
      if (file) this.loadLocalVideo(file);
    },
    onFileChange(event: Event) {
      const target = event.target as HTMLInputElement;
      const file = target.files && target.files[0];
      if (file) this.loadLocalVideo(file);
    },
    loadLocalVideo(file: File) {
      if (!file.type.startsWith("video/")) {
        (this as any).showToast("请选择视频格式文件");
        return;
      }
      if (this.videoUrl) URL.revokeObjectURL(this.videoUrl);
      this.videoUrl = URL.createObjectURL(file);
      this.fileName = file.name;
      this.fileSize = `${(file.size / 1024 / 1024).toFixed(1)} MB`;
      this.analyzed = false;
      (this as any).showToast("本地视频已载入，可开始分析");
    },
    clearVideo() {
      if (this.videoUrl) URL.revokeObjectURL(this.videoUrl);
      this.videoUrl = "";
      this.fileName = "";
      this.fileSize = "";
      this.analyzed = false;
      if (this.$refs.localVideoInput) (this.$refs.localVideoInput as HTMLInputElement).value = "";
    },
    startAnalyze() {
      if (!this.videoUrl) {
        (this as any).showToast("请先上传本地视频后再开始分析");
        return;
      }
      this.analyzed = true;
      (this as any).showToast("本地视频智能分析已完成");
    }
  },
  beforeUnmount() {
    if (this.videoUrl) URL.revokeObjectURL(this.videoUrl);
  }
});
</script>
