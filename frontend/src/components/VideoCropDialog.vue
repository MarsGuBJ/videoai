<script lang="ts">
const MIN_SCALE = 1;
const MAX_SCALE = 8;
const WHEEL_STEP = 1.15;

export default {
  name: "VideoCropDialog",
  props: ["open", "item", "action", "itemIndex", "confirmLabel", "videoUrl", "videoStart"],
  emits: ["close", "confirm"],
  data() {
    return {
      selection: { x: 15, y: 15, width: 70, height: 70 },
      dragStart: null as any,
      dragging: false,
      mode: "select" as "zoom" | "select",
      scale: MIN_SCALE,
      offsetX: 0,
      offsetY: 0,
      panStart: null as any,
      panning: false,
      imgVersion: 0,
      paused: true,
      videoError: false,
      videoReady: false,
      currentTime: 0,
      duration: 0,
      muted: true
    };
  },
  watch: {
    open(value: boolean) {
      if (!value) {
        const video: any = this.$refs.cropVideo;
        if (video) video.pause();
        return;
      }
      this.selection = { x: 15, y: 15, width: 70, height: 70 };
      this.dragStart = null;
      this.dragging = false;
      this.mode = "select";
      this.scale = MIN_SCALE;
      this.offsetX = 0;
      this.offsetY = 0;
      this.panStart = null;
      this.panning = false;
      this.imgVersion = 0;
      this.paused = true;
      this.videoError = false;
      this.videoReady = false;
      this.currentTime = 0;
      this.duration = 0;
      this.muted = true;
    }
  },
  computed: {
    actionLabel() {
      const labels: any = { imageSearch: "以图搜图", quickDeploy: "快速布防", track: "轨迹还原" };
      return labels[this.action] || "目标操作";
    },
    useVideo() {
      return Boolean(this.videoUrl) && !this.videoError;
    },
    // 视频模式仅在暂停时允许缩放/平移/框选；图片降级模式不受限
    canOperate() {
      return !this.useVideo || this.paused;
    },
    stageClass() {
      return {
        "mode-zoom": this.mode === "zoom",
        "mode-select": this.mode === "select",
        panning: this.panning
      };
    },
    transformStyle() {
      return { transform: `translate(${this.offsetX}px, ${this.offsetY}px) scale(${this.scale})` };
    },
    selectionStyle() {
      const crop = this.selection || { x: 0, y: 0, width: 0, height: 0 };
      return {
        left: `${crop.x}%`,
        top: `${crop.y}%`,
        width: `${crop.width}%`,
        height: `${crop.height}%`
      };
    },
    hasValidSelection() {
      return Boolean(this.selection && this.selection.width >= 3 && this.selection.height >= 3);
    },
    canConfirm() {
      return Boolean(this.canOperate && this.resolvedCrop());
    },
    confirmButtonLabel() {
      return this.confirmLabel || "确定";
    },
    timeLabel() {
      return `${this.formatTime(this.currentTime)} / ${this.formatTime(this.duration)}`;
    }
  },
  methods: {
    setMode(mode: "zoom" | "select") {
      this.mode = mode;
    },
    formatTime(seconds: number) {
      const value = Math.max(0, Math.floor(Number(seconds) || 0));
      const m = Math.floor(value / 60);
      const s = value % 60;
      return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
    },
    // 视频元数据就绪：定位到事件起点并尝试静音自动播放（被拦截则保持暂停，画面定格可框选）
    onLoadedMetadata() {
      const video: any = this.$refs.cropVideo;
      if (!video) return;
      this.duration = Number(video.duration) || 0;
      const start = Math.max(0, Math.min(this.duration || Number(this.videoStart) || 0, Number(this.videoStart) || 0));
      video.muted = this.muted;
      try {
        video.currentTime = start;
      } catch {
        // 忽略定位失败，仍停留在首帧
      }
      this.currentTime = start;
      this.imgVersion += 1;
      const result = video.play();
      if (result && typeof result.catch === "function") {
        result.catch(() => {
          this.paused = true;
          this.snapshotFrame();
        });
      }
    },
    onVideoPlay() {
      this.paused = false;
      this.videoReady = true;
    },
    // 首帧可显示后撤掉加载提示
    onVideoCanPlay() {
      this.videoReady = true;
    },
    onVideoPause() {
      this.paused = true;
      this.snapshotFrame();
    },
    onVideoSeeked() {
      const video: any = this.$refs.cropVideo;
      if (video) this.currentTime = video.currentTime || 0;
      if (this.paused) this.snapshotFrame();
    },
    onTimeUpdate() {
      const video: any = this.$refs.cropVideo;
      if (video) this.currentTime = video.currentTime || 0;
    },
    onVideoError() {
      this.videoError = true;
    },
    // 暂停时把当前帧画到 canvas 上展示，避免某些编码/seek 场景暂停后黑屏
    snapshotFrame() {
      const video: any = this.$refs.cropVideo;
      const canvas: any = this.$refs.cropCanvas;
      if (!video || !canvas || !video.videoWidth || !video.videoHeight) return;
      if (canvas.width !== video.videoWidth || canvas.height !== video.videoHeight) {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
      }
      try {
        const ctx = canvas.getContext("2d");
        if (ctx) ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      } catch {
        // 抓帧失败时保留 video 画面兜底
      }
    },
    togglePlay() {
      const video: any = this.$refs.cropVideo;
      if (!video) return;
      if (video.paused) {
        const result = video.play();
        if (result && typeof result.catch === "function") result.catch(() => undefined);
      } else {
        video.pause();
      }
    },
    seekBy(delta: number) {
      const video: any = this.$refs.cropVideo;
      if (!video) return;
      const max = this.duration ? Math.max(0, this.duration - 0.05) : Number.MAX_SAFE_INTEGER;
      video.currentTime = Math.max(0, Math.min(max, (video.currentTime || 0) + delta));
      // 暂停时 seek 后由 seeked 事件刷新定格帧
    },
    toggleMute() {
      const video: any = this.$refs.cropVideo;
      this.muted = !this.muted;
      if (video) video.muted = this.muted;
    },
    point(pointerEvent: any) {
      const stage: any = this.$refs.cropStage;
      if (!stage) return { x: 0, y: 0 };
      const rect = stage.getBoundingClientRect();
      return {
        x: Math.min(100, Math.max(0, ((pointerEvent.clientX - rect.left) / rect.width) * 100)),
        y: Math.min(100, Math.max(0, ((pointerEvent.clientY - rect.top) / rect.height) * 100))
      };
    },
    startSelection(pointerEvent: any) {
      if (!this.canOperate) return;
      const point = this.point(pointerEvent);
      this.dragStart = point;
      this.selection = { x: point.x, y: point.y, width: 0, height: 0 };
      this.dragging = true;
      if (pointerEvent.currentTarget && pointerEvent.currentTarget.setPointerCapture) {
        pointerEvent.currentTarget.setPointerCapture(pointerEvent.pointerId);
      }
    },
    updateSelection(pointerEvent: any) {
      if (!this.dragging || !this.dragStart) return;
      const point = this.point(pointerEvent);
      this.selection = {
        x: Math.min(this.dragStart.x, point.x),
        y: Math.min(this.dragStart.y, point.y),
        width: Math.abs(point.x - this.dragStart.x),
        height: Math.abs(point.y - this.dragStart.y)
      };
    },
    finishSelection(pointerEvent: any) {
      if (!this.dragging) return;
      this.updateSelection(pointerEvent);
      this.dragging = false;
      this.dragStart = null;
    },
    clampPan() {
      const stage: any = this.$refs.cropStage;
      if (!stage) {
        this.offsetX = 0;
        this.offsetY = 0;
        return;
      }
      const rect = stage.getBoundingClientRect();
      const w = rect.width * this.scale;
      const h = rect.height * this.scale;
      this.offsetX = Math.min(0, Math.max(rect.width - w, this.offsetX));
      this.offsetY = Math.min(0, Math.max(rect.height - h, this.offsetY));
    },
    onWheel(wheelEvent: any) {
      if (this.mode !== "zoom" || !this.canOperate) return;
      const stage: any = this.$refs.cropStage;
      if (!stage) return;
      const rect = stage.getBoundingClientRect();
      const mx = wheelEvent.clientX - rect.left;
      const my = wheelEvent.clientY - rect.top;
      const factor = wheelEvent.deltaY < 0 ? WHEEL_STEP : 1 / WHEEL_STEP;
      const next = Math.min(MAX_SCALE, Math.max(MIN_SCALE, this.scale * factor));
      if (next === this.scale) return;
      // 以鼠标位置为中心缩放：缩放前后鼠标下的画面点保持不动
      const ratio = next / this.scale;
      this.offsetX = mx - (mx - this.offsetX) * ratio;
      this.offsetY = my - (my - this.offsetY) * ratio;
      this.scale = next;
      this.clampPan();
    },
    startPan(pointerEvent: any) {
      if (!this.canOperate) return;
      if (pointerEvent.button !== undefined && pointerEvent.button !== 0) return;
      this.panning = true;
      this.panStart = { x: pointerEvent.clientX, y: pointerEvent.clientY, ox: this.offsetX, oy: this.offsetY };
      if (pointerEvent.currentTarget && pointerEvent.currentTarget.setPointerCapture) {
        pointerEvent.currentTarget.setPointerCapture(pointerEvent.pointerId);
      }
    },
    movePan(pointerEvent: any) {
      if (!this.panning || !this.panStart) return;
      this.offsetX = this.panStart.ox + (pointerEvent.clientX - this.panStart.x);
      this.offsetY = this.panStart.oy + (pointerEvent.clientY - this.panStart.y);
      this.clampPan();
    },
    endPan() {
      this.panning = false;
      this.panStart = null;
    },
    onPointerDown(pointerEvent: any) {
      if (this.mode === "zoom") this.startPan(pointerEvent);
      else this.startSelection(pointerEvent);
    },
    onPointerMove(pointerEvent: any) {
      if (this.mode === "zoom") this.movePan(pointerEvent);
      else this.updateSelection(pointerEvent);
    },
    onPointerUp(pointerEvent: any) {
      if (this.mode === "zoom") this.endPan();
      else this.finishSelection(pointerEvent);
    },
    // 选区（stage 百分比）映射回原始画面内容框（object-fit: contain 的实际内容区，含缩放/平移变换）
    resolvedCrop() {
      if (!this.hasValidSelection) return null;
      void this.imgVersion; // 媒体加载完成后触发重算
      const stage: any = this.$refs.cropStage;
      const media: any = this.useVideo ? this.$refs.cropVideo : this.$refs.cropImage;
      if (!stage || !media) return null;
      const naturalW = this.useVideo ? media.videoWidth : media.naturalWidth;
      const naturalH = this.useVideo ? media.videoHeight : media.naturalHeight;
      if (!naturalW || !naturalH) return null;
      const rect = stage.getBoundingClientRect();
      const w = rect.width;
      const h = rect.height;
      const r = naturalW / naturalH;
      let cw: number;
      let ch: number;
      if (w / h > r) {
        ch = h;
        cw = h * r;
      } else {
        cw = w;
        ch = w / r;
      }
      const content = {
        left: this.offsetX + ((w - cw) / 2) * this.scale,
        top: this.offsetY + ((h - ch) / 2) * this.scale,
        width: cw * this.scale,
        height: ch * this.scale
      };
      if (content.width <= 0 || content.height <= 0) return null;
      const px = w / 100;
      const py = h / 100;
      const clamp = (v: number) => Math.min(100, Math.max(0, v));
      const x1 = clamp((this.selection.x * px - content.left) / content.width * 100);
      const y1 = clamp((this.selection.y * py - content.top) / content.height * 100);
      const x2 = clamp(((this.selection.x + this.selection.width) * px - content.left) / content.width * 100);
      const y2 = clamp(((this.selection.y + this.selection.height) * py - content.top) / content.height * 100);
      if (x2 - x1 < 3 || y2 - y1 < 3) return null;
      return {
        x: Number(x1.toFixed(2)),
        y: Number(y1.toFixed(2)),
        width: Number((x2 - x1).toFixed(2)),
        height: Number((y2 - y1).toFixed(2))
      };
    },
    closeDialog() {
      this.dragging = false;
      this.dragStart = null;
      this.panning = false;
      this.panStart = null;
      const video: any = this.$refs.cropVideo;
      if (video) video.pause();
      this.$emit("close");
    },
    // 直接从定格帧 canvas 裁出选区图片文件：视频经同源代理播放，canvas 未污染可导出；
    // 失败（如跨源污染）时返回 null，由调用方退回截帧接口路径
    captureCropFile(crop: any): Promise<File | null> {
      const canvas: any = this.$refs.cropCanvas;
      if (!canvas || !canvas.width || !canvas.height || !crop) return Promise.resolve(null);
      const sx = Math.round((crop.x / 100) * canvas.width);
      const sy = Math.round((crop.y / 100) * canvas.height);
      const sw = Math.round((crop.width / 100) * canvas.width);
      const sh = Math.round((crop.height / 100) * canvas.height);
      if (!sw || !sh) return Promise.resolve(null);
      const out = document.createElement("canvas");
      out.width = sw;
      out.height = sh;
      const ctx = out.getContext("2d");
      if (!ctx) return Promise.resolve(null);
      try {
        ctx.drawImage(canvas, sx, sy, sw, sh, 0, 0, sw, sh);
      } catch {
        return Promise.resolve(null);
      }
      return new Promise(resolve => {
        try {
          out.toBlob(
            blob => resolve(blob ? new File([blob], "exact-crop.jpg", { type: blob.type || "image/jpeg" }) : null),
            "image/jpeg",
            0.92
          );
        } catch {
          resolve(null);
        }
      });
    },
    async confirmSelection() {
      if (!this.item || !this.canConfirm) return;
      // canConfirm 已保证 resolvedCrop 为有效百分比选区（宽高 ≥3%）
      const crop = this.resolvedCrop();
      // 裁剪图优先从定格帧 canvas 直接裁出（与画面一致且无额外网络请求）；
      // 取不到时由调用方按 frameTime 从原始视频地址截帧（本组件的播放地址是代理地址，不能直接用于截帧）
      const video: any = this.$refs.cropVideo;
      const cropFile = this.useVideo ? await this.captureCropFile(crop) : null;
      const frameTime = this.useVideo && video ? Math.floor(video.currentTime || 0) : null;
      this.$emit("confirm", { action: this.action, item: this.item, index: this.itemIndex, crop, cropFile, frameTime });
    }
  }
};
</script>

<template>
  <div class="modal-mask image-crop-mask" :class="{ open: open }" :inert="!open" @click.self="closeDialog">
    <section class="modal-dialog image-crop-dialog" role="dialog" aria-modal="true" aria-labelledby="shared-video-crop-title">
      <div class="modal-head"><h3 id="shared-video-crop-title">{{ actionLabel }} · 框选目标</h3><button class="modal-close" aria-label="关闭" @click="closeDialog">×</button></div>
      <div class="modal-body image-crop-body">
        <div v-if="item" ref="cropStage" class="image-crop-stage" :class="stageClass" @wheel.prevent="onWheel" @pointerdown="onPointerDown" @pointermove="onPointerMove" @pointerup="onPointerUp" @pointercancel="onPointerUp">
          <div class="image-crop-transform" :style="transformStyle">
            <template v-if="useVideo">
              <video
                ref="cropVideo"
                v-show="!paused"
                :src="videoUrl"
                playsinline
                preload="auto"
                @loadedmetadata="onLoadedMetadata"
                @loadeddata="onVideoSeeked"
                @canplay="onVideoCanPlay"
                @play="onVideoPlay"
                @pause="onVideoPause"
                @seeked="onVideoSeeked"
                @timeupdate="onTimeUpdate"
                @ended="onVideoPause"
                @error="onVideoError"
              ></video>
              <canvas ref="cropCanvas" v-show="paused"></canvas>
            </template>
            <img v-else ref="cropImage" :src="item.image" :alt="item.title" draggable="false" @load="imgVersion += 1" />
          </div>
          <div v-if="useVideo && !videoReady" class="video-crop-loading">视频加载中，请稍候…</div>
          <span v-if="selection && mode === 'select' && canOperate" class="image-crop-selection" :style="selectionStyle"></span>
        </div>
        <div v-if="item && useVideo && !canOperate" class="video-crop-hint">播放中，暂停后可缩放 / 框选</div>
        <div class="image-crop-toolbar">
          <template v-if="useVideo">
            <button type="button" class="image-crop-mode-btn" @click="seekBy(-5)">-5s</button>
            <button type="button" class="image-crop-mode-btn" @click="togglePlay">{{ paused ? "播放" : "暂停" }}</button>
            <button type="button" class="image-crop-mode-btn" @click="seekBy(5)">+5s</button>
            <span class="video-crop-time">{{ timeLabel }}</span>
            <button type="button" class="image-crop-mode-btn" @click="toggleMute">{{ muted ? "取消静音" : "静音" }}</button>
          </template>
          <button type="button" class="image-crop-mode-btn" :class="{ active: mode === 'zoom' }" :aria-pressed="mode === 'zoom'" @click="setMode('zoom')">放大</button>
          <button type="button" class="image-crop-mode-btn" :class="{ active: mode === 'select' }" :aria-pressed="mode === 'select'" @click="setMode('select')">框选</button>
        </div>
      </div>
      <div class="modal-footer"><button class="btn" @click="closeDialog">取消</button><button class="btn primary" :disabled="!canConfirm" @click="confirmSelection">{{ confirmButtonLabel }}</button></div>
    </section>
  </div>
</template>
