<template>
  <!-- 复刻参考站（iSecure Center / dolphin_vss）回放播放器 JsPluginPro 的外观结构：
       深色视频区(#262626) + 悬浮窗口遮罩 + 58px 时间轴 + 40px 工具栏(#333) -->
  <section ref="root" class="playback-player-shell" :class="{ 'is-fullscreen': isFullscreen }">
    <div class="playback-player-view-wrap">
      <div ref="videoHost" class="playback-player-view">
        <video-player
          v-if="streamUrl"
          ref="video"
          :url="streamUrl"
          format="flv"
          :native-controls="false"
          :show-zoom-bar="false"
          @resolution="(resolution) => $emit('resolution', resolution)"
        ></video-player>

        <!-- 悬浮窗口遮罩（VideoMask）：悬停显示标题栏/底栏 -->
        <div class="video-mask" :class="{ 'is-active': maskActive }" @mouseenter="maskActive = true" @mouseleave="maskActive = false">
          <div class="video-mask-header">
            <span class="video-mask-title">
              <playback-icon name="capture" class="video-mask-camera-icon"></playback-icon>
              <span class="video-mask-name">{{ title || '未选择监控点' }}</span>
            </span>
            <span class="video-mask-header-right">
              <span v-if="playing" class="video-mask-playing-tag">回放中</span>
              <button class="video-mask-btn" type="button" title="关闭窗口" @click="$emit('close')">
                <playback-icon name="close"></playback-icon>
              </button>
            </span>
          </div>
          <div class="video-mask-content">
            <slot name="mask">{{ maskText }}</slot>
          </div>
          <div class="video-mask-footer">
            <div class="video-mask-footer-left"></div>
            <div class="video-mask-footer-right">
              <button class="video-mask-btn" type="button" :title="muted ? '开启声音' : '声音'" @click="$emit('mute-toggle')">
                <playback-icon :name="muted ? 'soundOff' : 'soundOn'"></playback-icon>
              </button>
              <button class="video-mask-btn" type="button" title="抓图" @click="$emit('capture')">
                <playback-icon name="capture"></playback-icon>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="playback-player-timeline">
      <playback-timeline
        :segments="segments"
        :current-ms="currentMs"
        :range-start-ms="rangeStartMs"
        :range-end-ms="rangeEndMs"
        :playing="playing"
        @seek="(ms) => $emit('seek', ms)"
      ></playback-timeline>
    </div>

    <div class="playback-player-toolbar">
      <div class="playback-toolbar-left">
        <label class="playback-time-picker" title="定位回放时间">
          <input type="datetime-local" step="1" :value="pickerValue" @change="onPickerChange" />
          <playback-icon name="clock" class="playback-time-picker-icon"></playback-icon>
        </label>
        <button class="playback-toolbar-btn" type="button" :title="playing ? '暂停' : '播放'" @click="$emit('toggle-play')">
          <playback-icon :name="playing ? 'pause' : 'play'"></playback-icon>
        </button>
        <div class="playback-speed-pill" title="回放倍速">
          <button class="playback-speed-btn" type="button" title="降低播放速度" @click="$emit('speed-step', -1)">
            <playback-icon name="fastBackward"></playback-icon>
          </button>
          <span class="playback-speed-text" title="恢复默认速度" @click="$emit('speed-reset')">{{ speedText }}</span>
          <button class="playback-speed-btn" type="button" title="提升播放速度" @click="$emit('speed-step', 1)">
            <playback-icon name="fastForward"></playback-icon>
          </button>
        </div>
        <span class="playback-dividing"></span>
        <button class="playback-toolbar-btn" type="button" :title="muted ? '取消静音' : '静音'" @click="$emit('mute-toggle')">
          <playback-icon :name="muted ? 'soundOff' : 'soundOn'"></playback-icon>
        </button>
        <button class="playback-toolbar-btn" type="button" title="全部抓图" @click="$emit('capture')">
          <playback-icon name="capture"></playback-icon>
        </button>
      </div>
      <div class="playback-toolbar-right">
        <button class="playback-toolbar-btn" type="button" title="全部关闭" @click="$emit('close')">
          <playback-icon name="screensClose"></playback-icon>
        </button>
        <span class="playback-dividing"></span>
        <button class="playback-toolbar-btn" type="button" title="全屏" @click="toggleFullscreen">
          <playback-icon name="fullScreen"></playback-icon>
        </button>
      </div>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import VideoPlayer from '../VideoPlayer.vue';
import PlaybackIcon from './PlaybackIcon.vue';
import PlaybackTimeline, { TimelineSegment } from './PlaybackTimeline.vue';

function pad2(value: number): string {
  return String(value).padStart(2, '0');
}

function toPickerValue(ms: number): string {
  if (!ms) return '';
  const date = new Date(ms);
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}T${pad2(date.getHours())}:${pad2(date.getMinutes())}:${pad2(date.getSeconds())}`;
}

export default defineComponent({
  name: 'PlaybackPlayer',
  components: { VideoPlayer, PlaybackIcon, PlaybackTimeline },
  props: {
    streamUrl: { type: String, default: undefined },
    title: { type: String, default: '' },
    playing: { type: Boolean, default: false },
    speed: { type: Number, default: 1 },
    currentMs: { type: Number, default: 0 },
    rangeStartMs: { type: Number, default: 0 },
    rangeEndMs: { type: Number, default: 0 },
    segments: { type: Array as () => TimelineSegment[], default: () => [] },
    muted: { type: Boolean, default: true },
    maskText: { type: String, default: '' },
  },
  data() {
    return {
      maskActive: false,
      isFullscreen: false,
    };
  },
  computed: {
    speedText(): string {
      // 参考站展示口径：慢速 1/4x、1/2x；快速 2×、4×
      if (this.speed < 1) return `1/${Math.round(1 / this.speed)}x`;
      return `${this.speed}×`;
    },
    pickerValue(): string {
      return toPickerValue(this.currentMs);
    },
  },
  methods: {
    videoInstance(): any | null {
      return (this.$refs.video as any) || null;
    },
    onPickerChange(event: Event) {
      const value = (event.target as HTMLInputElement).value;
      if (!value) return;
      const ms = new Date(value).getTime();
      if (!Number.isNaN(ms)) {
        this.$emit('seek', ms);
      }
    },
    toggleFullscreen() {
      const root = this.$refs.root as HTMLElement | undefined;
      if (!root) return;
      if (document.fullscreenElement) {
        document.exitFullscreen().catch(() => {});
      } else {
        root.requestFullscreen?.().catch(() => {});
      }
    },
  },
});
</script>

<style scoped>
.playback-player-shell {
  position: relative;
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  background: #262626;
  border: 1px solid #000;
}

.playback-player-shell.is-fullscreen {
  width: 100vw;
  height: 100vh;
}

.playback-player-view-wrap {
  position: relative;
  flex: 1;
  min-height: 0;
}

.playback-player-view {
  position: absolute;
  inset: 0;
  background: #262626;
}

/* ---- 悬浮窗口遮罩（参考站 VideoMask） ---- */
.video-mask {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  pointer-events: none;
}

.video-mask-header,
.video-mask-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 28px;
  padding: 0 4px;
  background: #1a1a1a;
  opacity: 0;
  transition: opacity 0.2s;
  pointer-events: none;
}

.video-mask.is-active .video-mask-header,
.video-mask.is-active .video-mask-footer {
  opacity: 1;
  pointer-events: auto;
}

.video-mask-title {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  max-width: 60%;
  color: #fff;
  font-size: 12px;
}

.video-mask-camera-icon {
  width: 16px;
  height: 16px;
  color: #ccc;
}

.video-mask-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.video-mask-header-right {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.video-mask-playing-tag {
  color: #ccc;
  font-size: 12px;
}

.video-mask-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: 0;
  padding: 0;
  background: transparent;
  color: #ccc;
  cursor: pointer;
}

.video-mask-btn:hover {
  color: #fff;
}

.video-mask-btn .playback-icon {
  width: 18px;
  height: 18px;
}

.video-mask-content {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ccc;
  font-size: 12px;
  pointer-events: none;
}

.video-mask-footer-right {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

/* ---- 时间轴 ---- */
.playback-player-timeline {
  height: 58px;
  flex: none;
}

/* ---- 工具栏（参考站 #333 / 40px） ---- */
.playback-player-toolbar {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 40px;
  flex: none;
  background: #333;
  line-height: 40px;
}

.playback-toolbar-left,
.playback-toolbar-right {
  display: flex;
  align-items: center;
}

.playback-toolbar-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 32px;
  min-width: 32px;
  margin: 4px;
  padding: 4px;
  border: 0;
  border-radius: 2px;
  background: transparent;
  color: #ccc;
  cursor: pointer;
  line-height: 1;
}

.playback-toolbar-btn:hover {
  background: rgba(255, 255, 255, 0.1);
}

.playback-toolbar-btn.is-disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.playback-toolbar-btn .playback-icon {
  width: 24px;
  height: 24px;
}

.playback-dividing {
  display: inline-block;
  width: 1px;
  height: 16px;
  margin: 0 4px;
  background: rgba(255, 255, 255, 0.2);
}

/* 时间选择框：参考站 playing-time-date-picker（160px、深色底 #4b4b4b） */
.playback-time-picker {
  position: relative;
  display: inline-flex;
  align-items: center;
  height: 40px;
  margin: 0 4px;
}

.playback-time-picker input {
  width: 160px;
  height: 28px;
  margin: 6px 0;
  padding: 0 8px;
  border: 0;
  border-radius: 2px;
  background: #4b4b4b;
  color: #eee;
  font-size: 12px;
  color-scheme: dark;
  cursor: pointer;
}

.playback-time-picker input:hover {
  background: #666;
}

.playback-time-picker input:focus {
  outline: none;
}

.playback-time-picker-icon {
  position: absolute;
  right: -22px;
  width: 14px;
  height: 14px;
  color: #474747;
  pointer-events: none;
}

/* 倍速胶囊：参考站 plugin-speed（#222 圆角 14px） */
.playback-speed-pill {
  display: inline-flex;
  align-items: center;
  height: 28px;
  margin: 6px 4px;
  padding: 0 4px;
  border-radius: 14px;
  background: #222;
}

.playback-speed-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border: 0;
  padding: 0;
  background: transparent;
  color: #7f8a9a;
  cursor: pointer;
}

.playback-speed-btn:hover {
  color: #ccc;
}

.playback-speed-btn .playback-icon {
  width: 16px;
  height: 16px;
}

.playback-speed-text {
  min-width: 34px;
  color: #999;
  font-size: 12px;
  text-align: center;
  cursor: pointer;
  user-select: none;
}

.playback-speed-text:hover {
  color: #ccc;
}
</style>
