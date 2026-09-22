<script lang="ts">
const MIN_SCALE = 1;
const MAX_SCALE = 8;
const WHEEL_STEP = 1.15;

export default {
  name: "ImageCropDialog",
  props: ["open", "item", "action", "itemIndex", "confirmLabel"],
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
      imgVersion: 0
    };
  },
  watch: {
    open(value: boolean) {
      if (!value) return;
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
    }
  },
  computed: {
    actionLabel() {
      const labels: any = { imageSearch: "以图搜图", quickDeploy: "快速布防", track: "轨迹还原", replaceUpload: "裁剪参考图", replaceTarget: "裁剪目标图片", searchCrop: "以图搜图" };
      return labels[this.action] || "目标操作";
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
      return Boolean(this.resolvedCrop());
    },
    confirmButtonLabel() {
      return this.confirmLabel || (this.action === "searchCrop" ? "搜图" : "确定");
    }
  },
  methods: {
    setMode(mode: "zoom" | "select") {
      this.mode = mode;
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
      if (this.mode !== "zoom") return;
      const stage: any = this.$refs.cropStage;
      if (!stage) return;
      const rect = stage.getBoundingClientRect();
      const mx = wheelEvent.clientX - rect.left;
      const my = wheelEvent.clientY - rect.top;
      const factor = wheelEvent.deltaY < 0 ? WHEEL_STEP : 1 / WHEEL_STEP;
      const next = Math.min(MAX_SCALE, Math.max(MIN_SCALE, this.scale * factor));
      if (next === this.scale) return;
      // 以鼠标位置为中心缩放：缩放前后鼠标下的图片点保持不动
      const ratio = next / this.scale;
      this.offsetX = mx - (mx - this.offsetX) * ratio;
      this.offsetY = my - (my - this.offsetY) * ratio;
      this.scale = next;
      this.clampPan();
    },
    startPan(pointerEvent: any) {
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
    // 选区（stage 百分比）映射回原始图片内容框（object-fit: contain 的实际内容区，含缩放/平移变换）
    resolvedCrop() {
      if (!this.hasValidSelection) return null;
      void this.imgVersion; // 图片加载完成后触发重算
      const stage: any = this.$refs.cropStage;
      const img: any = this.$refs.cropImage;
      if (!stage || !img || !img.naturalWidth || !img.naturalHeight) return null;
      const rect = stage.getBoundingClientRect();
      const w = rect.width;
      const h = rect.height;
      const r = img.naturalWidth / img.naturalHeight;
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
      this.$emit("close");
    },
    confirmSelection() {
      if (!this.item || !this.canConfirm) return;
      // canConfirm 已保证 resolvedCrop 为有效百分比选区（宽高 ≥3%）
      const crop = this.resolvedCrop();
      this.$emit("confirm", { action: this.action, item: this.item, index: this.itemIndex, crop });
    }
  }
};
</script>

<template>
  <div class="modal-mask image-crop-mask" :class="{ open: open }" :inert="!open" @click.self="closeDialog">
    <section class="modal-dialog image-crop-dialog" role="dialog" aria-modal="true" aria-labelledby="shared-image-crop-title">
      <div class="modal-head"><h3 id="shared-image-crop-title">{{ actionLabel }} · 框选目标</h3><button class="modal-close" aria-label="关闭" @click="closeDialog">×</button></div>
      <div class="modal-body image-crop-body">
        <div v-if="item" ref="cropStage" class="image-crop-stage" :class="stageClass" @wheel.prevent="onWheel" @pointerdown="onPointerDown" @pointermove="onPointerMove" @pointerup="onPointerUp" @pointercancel="onPointerUp">
          <div class="image-crop-transform" :style="transformStyle">
            <img ref="cropImage" :src="item.image" :alt="item.title" draggable="false" @load="imgVersion += 1" />
          </div>
          <span v-if="selection && mode === 'select'" class="image-crop-selection" :style="selectionStyle"></span>
        </div>
        <div class="image-crop-toolbar">
          <button type="button" class="image-crop-mode-btn" :class="{ active: mode === 'zoom' }" :aria-pressed="mode === 'zoom'" @click="setMode('zoom')">放大</button>
          <button type="button" class="image-crop-mode-btn" :class="{ active: mode === 'select' }" :aria-pressed="mode === 'select'" @click="setMode('select')">框选</button>
        </div>
      </div>
      <div class="modal-footer"><button class="btn" @click="closeDialog">取消</button><button class="btn primary" :disabled="!canConfirm" @click="confirmSelection">{{ confirmButtonLabel }}</button></div>
    </section>
  </div>
</template>
