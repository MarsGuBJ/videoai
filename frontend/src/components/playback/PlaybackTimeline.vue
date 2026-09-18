<template>
  <!-- 复刻参考站 Timeline：黑色 canvas 24h 时间轴，录像段色带、刻度、居中白色播放头、
       悬停时间指示、滚轮缩放（0.2/1/2/6/12/24h）、拖拽平移、点击/双击定位 -->
  <div ref="wrap" class="playback-timeline-wrap">
    <canvas ref="canvas" class="playback-timeline-bar"></canvas>
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';

export interface TimelineSegment {
  startMs: number;
  endMs: number;
  type?: string;
}

// 参考站录像类型色板（计划/移动侦测/报警/手工/其他）
const TYPE_COLORS: Record<string, string> = {
  plan: '#5881cf',
  motion: '#836abb',
  alarm: '#b25959',
  manual: '#b6a95b',
  other: '#519f8f',
};
const DEFAULT_COLOR = TYPE_COLORS.plan;

// 参考站缩放档位（小时）
const ZOOM_SPAN_HOURS = [0.2, 1, 2, 6, 12, 24];
// 参考站刻度间距候选（分钟）
const GRADUATIONS = [1, 2, 5, 10, 15, 20, 30, 60, 120, 180, 240, 360, 720, 1440];

function pad2(value: number): string {
  return String(value).padStart(2, '0');
}

function formatDateTime(ms: number): string {
  const date = new Date(ms);
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())} ${pad2(date.getHours())}:${pad2(date.getMinutes())}:${pad2(date.getSeconds())}`;
}

export default defineComponent({
  name: 'PlaybackTimeline',
  props: {
    segments: { type: Array as () => TimelineSegment[], default: () => [] },
    currentMs: { type: Number, default: 0 },
    // 可定位范围（查询结果合并后的整体时段）
    rangeStartMs: { type: Number, default: 0 },
    rangeEndMs: { type: Number, default: 0 },
    playing: { type: Boolean, default: false },
  },
  data() {
    return {
      spanMs: 0,
      viewStartMs: 0,
      followPlayhead: true,
      hoverMs: null as number | null,
      drag: null as { startX: number; baseViewStart: number; moved: boolean } | null,
      resizeObserver: null as ResizeObserver | null,
    };
  },
  computed: {
    totalRangeMs(): number {
      return Math.max(0, this.rangeEndMs - this.rangeStartMs);
    },
  },
  watch: {
    currentMs: {
      handler() {
        this.render();
      },
      immediate: false,
    },
    segments: {
      handler() {
        this.resetView();
        this.render();
      },
    },
    rangeStartMs() {
      this.resetView();
      this.render();
    },
    hoverMs() {
      this.render();
    },
    playing() {
      if (this.playing) this.followPlayhead = true;
      this.render();
    },
  },
  mounted() {
    this.resetView();
    this.attachEvents();
    if (typeof ResizeObserver !== 'undefined') {
      this.resizeObserver = new ResizeObserver(() => this.render());
      this.resizeObserver.observe(this.$refs.wrap as HTMLElement);
    } else {
      window.addEventListener('resize', this.render);
    }
    this.render();
  },
  beforeUnmount() {
    const wrap = this.$refs.wrap as HTMLElement | undefined;
    if (wrap) {
      wrap.removeEventListener('mousemove', this.onHover);
      wrap.removeEventListener('mouseleave', this.onHoverLeave);
      wrap.removeEventListener('mousedown', this.onDragStart);
      wrap.removeEventListener('wheel', this.onWheel, { passive: false } as EventListenerOptions);
    }
    window.removeEventListener('mouseup', this.onDragEnd);
    window.removeEventListener('resize', this.render);
    this.resizeObserver?.disconnect();
  },
  methods: {
    resetView() {
      // 初始视图：全范围（超过 24h 时截到 24h）；无查询结果时展示当天
      const fallbackStart = new Date();
      fallbackStart.setHours(0, 0, 0, 0);
      this.viewStartMs = this.totalRangeMs ? this.rangeStartMs : fallbackStart.getTime();
      this.spanMs = Math.min(this.totalRangeMs || 24 * 3600 * 1000, 24 * 3600 * 1000);
      this.followPlayhead = true;
    },
    attachEvents() {
      const wrap = this.$refs.wrap as HTMLElement;
      wrap.addEventListener('mousemove', this.onHover);
      wrap.addEventListener('mouseleave', this.onHoverLeave);
      wrap.addEventListener('mousedown', this.onDragStart);
      wrap.addEventListener('wheel', this.onWheel, { passive: false } as EventListenerOptions);
      window.addEventListener('mouseup', this.onDragEnd);
    },
    timeToX(ms: number, width: number): number {
      return ((ms - this.viewStartMs) / this.spanMs) * width;
    },
    xToTime(x: number, width: number): number {
      return this.viewStartMs + (x / width) * this.spanMs;
    },
    clampView(start: number): number {
      // 无数据时以当天为虚拟范围
      const rangeStart = this.totalRangeMs ? this.rangeStartMs : this.viewStartMs;
      const rangeEnd = this.totalRangeMs ? this.rangeEndMs : this.viewStartMs + 24 * 3600 * 1000;
      return Math.max(
        rangeStart - this.spanMs * 0.5,
        Math.min(rangeEnd - this.spanMs * 0.5, start),
      );
    },
    onHover(event: MouseEvent) {
      if (this.drag) return;
      const canvas = this.$refs.canvas as HTMLCanvasElement;
      const rect = canvas.getBoundingClientRect();
      this.hoverMs = this.xToTime(event.clientX - rect.left, rect.width);
    },
    onHoverLeave() {
      this.hoverMs = null;
    },
    onDragStart(event: MouseEvent) {
      if (event.button !== 0) return;
      this.drag = { startX: event.clientX, baseViewStart: this.viewStartMs, moved: false };
      event.preventDefault();
    },
    onDragEnd() {
      if (!this.drag) return;
      const wasDrag = this.drag.moved;
      this.drag = null;
      if (!wasDrag) {
        // 原地单击 = 定位到该时刻（参考站行为）
        this.seekFromEvent(event as MouseEvent);
      }
    },
    seekFromEvent(event: MouseEvent) {
      const canvas = this.$refs.canvas as HTMLCanvasElement;
      const rect = canvas.getBoundingClientRect();
      if (!rect.width) return;
      let ms = this.xToTime(event.clientX - rect.left, rect.width);
      // 只允许定位到可回放范围内
      ms = Math.max(this.rangeStartMs, Math.min(this.rangeEndMs - 1, ms));
      this.followPlayhead = true;
      this.$emit('seek', ms);
    },
    onWheel(event: WheelEvent) {
      event.preventDefault();
      const canvas = this.$refs.canvas as HTMLCanvasElement;
      const rect = canvas.getBoundingClientRect();
      const anchorMs = this.xToTime(event.clientX - rect.left, rect.width);
      const hours = this.spanMs / 3600000;
      let index = 0;
      let best = Infinity;
      ZOOM_SPAN_HOURS.forEach((h, i) => {
        const diff = Math.abs(h - hours);
        if (diff < best) {
          best = diff;
          index = i;
        }
      });
      const nextIndex = Math.max(0, Math.min(ZOOM_SPAN_HOURS.length - 1, index + (event.deltaY > 0 ? 1 : -1)));
      let span = ZOOM_SPAN_HOURS[nextIndex] * 3600000;
      // 范围不足一档时收紧到全范围
      if (span >= this.totalRangeMs) span = Math.max(this.totalRangeMs, 60 * 1000);
      const ratio = (anchorMs - this.viewStartMs) / this.spanMs;
      this.spanMs = span;
      this.viewStartMs = this.clampView(anchorMs - ratio * span);
      this.followPlayhead = false;
      this.render();
    },
    render() {
      const canvas = this.$refs.canvas as HTMLCanvasElement | undefined;
      const wrap = this.$refs.wrap as HTMLElement | undefined;
      if (!canvas || !wrap) return;
      const dpr = window.devicePixelRatio || 1;
      const width = wrap.clientWidth;
      const height = wrap.clientHeight;
      if (!width || !height) return;
      if (canvas.width !== Math.round(width * dpr) || canvas.height !== Math.round(height * dpr)) {
        canvas.width = Math.round(width * dpr);
        canvas.height = Math.round(height * dpr);
        canvas.style.width = `${width}px`;
        canvas.style.height = `${height}px`;
      }
      const ctx = canvas.getContext('2d');
      if (!ctx) return;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      // 播放中视图跟随播放头（播放头固定居中）
      if (this.followPlayhead && this.currentMs) {
        this.viewStartMs = this.clampView(this.currentMs - this.spanMs / 2);
      }
      const viewEnd = this.viewStartMs + this.spanMs;

      // 背景
      ctx.fillStyle = '#000';
      ctx.fillRect(0, 0, width, height);

      // 顶部单元格底带（参考站 drawCellBg：上部 30% 半透明黑带）
      ctx.fillStyle = 'rgba(0,0,0,0.5)';
      ctx.fillRect(0, 0, width, height * 0.3);

      // 可定位范围外区域遮罩（drawRangeBg）；无查询结果时不画
      if (this.totalRangeMs) {
        ctx.fillStyle = 'rgba(255,255,255,0.4)';
        if (this.rangeStartMs > this.viewStartMs) {
          const x = this.timeToX(this.rangeStartMs, width);
          if (x > 0) ctx.fillRect(0, 0, Math.min(x, width), height);
        }
        if (this.rangeEndMs < viewEnd) {
          const x = this.timeToX(this.rangeEndMs, width);
          if (x < width) ctx.fillRect(Math.max(0, x), 0, width - Math.max(0, x), height);
        }
      }

      // 刻度
      const pxPerMs = width / this.spanMs;
      let stepMin = GRADUATIONS[GRADUATIONS.length - 1];
      for (const g of GRADUATIONS) {
        if (g * 60000 * pxPerMs >= 55) {
          stepMin = g;
          break;
        }
      }
      const stepMs = stepMin * 60000;
      let tick = Math.ceil(this.viewStartMs / stepMs) * stepMs;
      ctx.strokeStyle = 'rgba(151,158,167,1)';
      ctx.fillStyle = 'rgba(151,158,167,1)';
      ctx.font = '10px sans-serif';
      ctx.textBaseline = 'top';
      while (tick <= viewEnd) {
        const x = Math.round(this.timeToX(tick, width)) + 0.5;
        const date = new Date(tick);
        const midnight = date.getHours() === 0 && date.getMinutes() === 0;
        const major = (tick / 60000) % (stepMs * 2 / 60000) === 0;
        const tickHeight = midnight ? 0.3 : major ? 0.2 : 0.15;
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height * tickHeight);
        ctx.stroke();
        if (midnight) {
          ctx.fillText(`${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`, x - 10, height * 0.32);
        } else if (major) {
          ctx.fillText(`${pad2(date.getHours())}:${pad2(date.getMinutes())}`, x - 10, height * 0.32);
        }
        tick += stepMs;
      }

      // 录像段色带（fillRect(x, 0.6h, w, 0.7h)）
      for (const segment of this.segments) {
        const start = Math.max(segment.startMs, this.viewStartMs);
        const end = Math.min(segment.endMs, viewEnd);
        if (end <= start) continue;
        const x = this.timeToX(start, width);
        const w = this.timeToX(end, width) - x;
        ctx.fillStyle = TYPE_COLORS[segment.type || 'plan'] || DEFAULT_COLOR;
        ctx.fillRect(x, height * 0.6, w, height * 0.7);
      }

      // 悬停指示线 + 时间文字
      if (this.hoverMs !== null && this.hoverMs >= this.viewStartMs && this.hoverMs <= viewEnd) {
        const x = Math.round(this.timeToX(this.hoverMs, width)) + 0.5;
        ctx.strokeStyle = 'rgb(194,202,215)';
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, 20);
        ctx.stroke();
        ctx.fillStyle = 'rgb(194,202,215)';
        ctx.fillText(formatDateTime(this.hoverMs), Math.min(Math.max(x - 40, 2), width - 140), height * 0.78);
      }

      // 播放头：白色 2px 竖线（跟随模式固定居中）
      const playheadMs = this.followPlayhead && this.currentMs ? this.currentMs : this.currentMs;
      if (playheadMs) {
        const x = this.followPlayhead
          ? Math.round(width / 2)
          : Math.round(this.timeToX(playheadMs, width));
        ctx.strokeStyle = 'rgb(255,255,255)';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
        ctx.lineWidth = 1;
      }
    },
  },
});
</script>

<style scoped>
.playback-timeline-wrap {
  position: relative;
  width: 100%;
  height: 58px;
  cursor: pointer;
}

.playback-timeline-wrap:active {
  cursor: e-resize;
}

.playback-timeline-bar {
  display: block;
  width: 100%;
  height: 100%;
  border: 1px solid #000;
  background: #000;
}
</style>
