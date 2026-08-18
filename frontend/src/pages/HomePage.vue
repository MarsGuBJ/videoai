<template>
  <section class="center-hero">
    <div class="content wide">
      <h1 class="page-title center">万物搜</h1>
      <p class="page-subtitle">一站式智能搜索与分析平台，支持文搜视频、文搜图、图搜图与视频分析</p>
      <div class="cards-grid">
        <button class="entry-card" v-for="card in store.entryCards" :key="card.route" @click="setRoute(card.route)">
          <span class="module-icon">{{ card.icon }}</span>
          <h3>{{ card.title }}</h3>
          <p>{{ card.desc }}</p>
          <span class="card-link">立即使用 →</span>
        </button>
      </div>
      <div class="home-omni-entry panel">
        <div class="home-omni-title">
          <span>统一搜索入口</span>
          <span class="hint-text">输入文字，或上传图片 / 视频后开始分析</span>
        </div>
        <input ref="homeImageInput" class="hidden-file-input" type="file" accept="image/*" @change="onHomeFile('image', $event)" />
        <input ref="homeVideoInput" class="hidden-file-input" type="file" accept="video/*" @change="onHomeFile('video', $event)" />
        <div class="home-input-shell">
          <textarea class="home-omni-textarea" v-model="homeQuery" placeholder="输入自然语言描述，例如：查找今天上午园区南门出现的白色车辆，也可以上传图片或视频进行分析"></textarea>
          <div class="home-input-actions">
            <div class="home-upload-actions">
              <button class="btn" @click="triggerHomeFile('image')">上传图</button>
              <button class="btn" @click="triggerHomeFile('video')">上传视频</button>
            </div>
            <button class="btn primary" @click="submitHomeSearch">智能分析</button>
          </div>
        </div>
        <div class="home-file-tags" v-if="homeImageName || homeVideoName">
          <span class="home-file-tag" v-if="homeImageName"><span>图片：{{ homeImageName }}</span></span>
          <span class="home-file-tag" v-if="homeVideoName"><span>视频：{{ homeVideoName }}</span></span>
        </div>
      </div>
    </div>
    <footer class="footer">
      <div><span>产品文档</span><span>API参考</span><span>更新日志</span><span>联系支持</span></div>
      <div style="margin-top:8px;">© 2026 大模型视觉平台 · 安防视觉万物搜索 · 版权所有</div>
    </footer>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";

export default defineComponent({
  name: "HomePage",
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  inject: {
    setRoute: { from: "setRoute", default: (route: string, options?: any) => {} },
    showToast: { from: "showToast", default: (m: string) => {} },
  },
  data() {
    return {
      homeQuery: "",
      homeImageName: "",
      homeVideoName: ""
    };
  },
  methods: {
    triggerHomeFile(type: string) {
      const input = (type === "image" ? this.$refs.homeImageInput : this.$refs.homeVideoInput) as HTMLInputElement | undefined;
      if (input) input.click();
    },
    onHomeFile(type: string, event: Event) {
      const target = event.target as HTMLInputElement;
      const file = target.files && target.files[0];
      if (!file) return;
      const isImage = type === "image";
      const isValid = isImage ? file.type.startsWith("image/") : file.type.startsWith("video/");
      if (!isValid) {
        this.showToast(isImage ? "请选择图片文件" : "请选择视频文件");
        target.value = "";
        return;
      }
      if (isImage) this.homeImageName = file.name;
      else this.homeVideoName = file.name;
      this.showToast(isImage ? "图片已添加到统一入口" : "视频已添加到统一入口");
    },
    submitHomeSearch() {
      if (this.homeVideoName) {
        this.showToast("已进入视频分析");
        this.setRoute("localVideo");
        return;
      }
      if (this.homeImageName) {
        this.showToast("已进入图搜图");
        this.setRoute("imageSearch");
        return;
      }
      if (this.homeQuery.trim()) {
        this.showToast("已进入文搜视频");
        this.setRoute("exact");
        return;
      }
      this.showToast("请输入文字，或上传图片/视频");
    }
  }
});
</script>
