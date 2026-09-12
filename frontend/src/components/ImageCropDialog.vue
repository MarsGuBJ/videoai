<script lang="ts">
export default {
  name: "ImageCropDialog",
  props: ["open", "item", "action", "itemIndex", "confirmLabel"],
  emits: ["close", "confirm"],
  data() {
    return {
      selection: { x: 15, y: 15, width: 70, height: 70 },
      dragStart: null as any,
      dragging: false
    };
  },
  watch: {
    open(value: boolean) {
      if (!value) return;
      this.selection = { x: 15, y: 15, width: 70, height: 70 };
      this.dragStart = null;
      this.dragging = false;
    }
  },
  computed: {
    actionLabel() {
      const labels: any = { imageSearch: "以图搜图", quickDeploy: "快速布防", track: "轨迹还原", replaceUpload: "裁剪参考图", replaceTarget: "裁剪目标图片", searchCrop: "以图搜图" };
      return labels[this.action] || "目标操作";
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
      return this.hasValidSelection;
    },
    confirmButtonLabel() {
      return this.confirmLabel || (this.action === "searchCrop" ? "搜图" : "确定");
    }
  },
  methods: {
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
    closeDialog() {
      this.dragging = false;
      this.dragStart = null;
      this.$emit("close");
    },
    confirmSelection() {
      if (!this.item || !this.canConfirm) return;
      // canConfirm 已保证框选有效（宽高 ≥3%），crop 恒为有效百分比选区
      const crop = this.hasValidSelection
        ? {
            x: Number(this.selection.x.toFixed(2)),
            y: Number(this.selection.y.toFixed(2)),
            width: Number(this.selection.width.toFixed(2)),
            height: Number(this.selection.height.toFixed(2))
          }
        : null;
      this.$emit("confirm", { action: this.action, item: this.item, index: this.itemIndex, crop });
    }
  }
};
</script>

<template>
  <div class="modal-mask image-crop-mask" :class="{ open: open }" :aria-hidden="open ? 'false' : 'true'" @click.self="closeDialog">
    <section class="modal-dialog image-crop-dialog" role="dialog" aria-modal="true" aria-labelledby="shared-image-crop-title">
      <div class="modal-head"><h3 id="shared-image-crop-title">{{ actionLabel }} · 框选目标</h3><button class="modal-close" aria-label="关闭" @click="closeDialog">×</button></div>
      <div class="modal-body image-crop-body">
        <div v-if="item" ref="cropStage" class="image-crop-stage" @pointerdown="startSelection" @pointermove="updateSelection" @pointerup="finishSelection" @pointercancel="finishSelection">
          <img :src="item.image" :alt="item.title" draggable="false" />
          <span v-if="selection" class="image-crop-selection" :style="selectionStyle"></span>
        </div>
      </div>
      <div class="modal-footer"><button class="btn" @click="closeDialog">取消</button><button class="btn primary" :disabled="!canConfirm" @click="confirmSelection">{{ confirmButtonLabel }}</button></div>
    </section>
  </div>
</template>
