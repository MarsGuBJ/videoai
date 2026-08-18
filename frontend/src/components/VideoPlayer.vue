<template>
  <section class="video-panel">
    <div class="video-shell">
      <img
        v-if="fallbackUrl"
        :key="fallbackUrl"
        ref="image"
        :src="fallbackUrl"
        alt="后端视频流"
        :class="surfaceClassName"
        :style="surfaceStyle"
      />
      <video
        ref="video"
        autoplay
        muted
        controls
        playsinline
        :class="[surfaceClassName, fallbackUrl ? 'video-surface-hidden' : '']"
        :style="surfaceStyle"
        @click="playVideo"
      ></video>
      <div v-if="message" class="video-message">{{ message }}</div>
    </div>
    <div class="ptz-bar" aria-label="数字 PTZ 控制">
      <button title="拉近" @click="zoom(0.2)">＋</button>
      <button title="拉远" @click="zoom(-0.2)">－</button>
      <button title="向上" @click="move(0, 12)">↑</button>
      <button title="向下" @click="move(0, -12)">↓</button>
      <button title="向左" @click="move(12, 0)">←</button>
      <button title="向右" @click="move(-12, 0)">→</button>
      <button title="重置" @click="resetTransform">⟳</button>
      <span>{{ transform.zoom.toFixed(1) }}x</span>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent, markRaw } from 'vue';
import flvjs from 'flv.js';
import type { Player } from 'flv.js';
import Hls from 'hls.js';

type Transform = {
  zoom: number;
  x: number;
  y: number;
};

export default defineComponent({
  name: 'VideoPlayer',
  props: {
    url: { type: String, default: undefined },
  },
  data() {
    return {
      transform: { zoom: 1, x: 0, y: 0 } as Transform,
      message: '未选择摄像头',
      fallbackUrl: undefined as string | undefined,
      reloadToken: 0,
      player: null as Player | null,
      hls: null as Hls | null,
      retryTimer: null as number | null,
      retryCount: 0,
    };
  },
  computed: {
    videoElement(): HTMLVideoElement | undefined {
      return this.$refs.video as HTMLVideoElement | undefined;
    },
    surfaceClassName(): string {
      return [
        'video-surface',
        zoomClass(this.transform.zoom),
        panClass('x', this.transform.x),
        panClass('y', this.transform.y),
      ].join(' ');
    },
    surfaceStyle(): Record<string, string> {
      return {
        transform: `translate(${this.transform.x}%, ${this.transform.y}%) scale(${this.transform.zoom})`,
      };
    },
  },
  watch: {
    url() {
      this.setupStream();
    },
    reloadToken() {
      this.setupStream();
    },
  },
  mounted() {
    this.setupStream();
  },
  beforeUnmount() {
    this.teardown();
  },
  methods: {
    scheduleRetry() {
      if (this.retryTimer !== null) {
        return;
      }
      const delay = Math.min(2000 * Math.pow(2, this.retryCount), 30000);
      this.retryCount += 1;
      this.message = `视频流重连中（第${this.retryCount}次，${Math.round(delay / 1000)}秒后）`;
      this.retryTimer = window.setTimeout(() => {
        this.retryTimer = null;
        this.reloadToken += 1;
      }, delay);
    },
    cancelRetryTimer() {
      if (this.retryTimer !== null) {
        window.clearTimeout(this.retryTimer);
        this.retryTimer = null;
      }
    },
    clearRetry() {
      this.cancelRetryTimer();
      this.retryCount = 0;
    },
    clearMessage() {
      this.message = '';
    },
    markPlaying() {
      this.clearRetry();
      this.clearMessage();
    },
    destroy() {
      this.cancelRetryTimer();
      if (this.hls) {
        this.hls.destroy();
        this.hls = null;
      }
      if (this.player) {
        this.player.destroy();
        this.player = null;
      }
      const video = this.videoElement;
      if (video) {
        video.srcObject = null;
        video.removeAttribute('src');
        video.load();
      }
      const image = this.$refs.image as HTMLImageElement | undefined;
      if (image) {
        image.removeAttribute('src');
      }
    },
    teardown() {
      const video = this.videoElement;
      if (video) {
        video.removeEventListener('loadedmetadata', this.clearMessage);
        video.removeEventListener('canplay', this.clearMessage);
        video.removeEventListener('playing', this.markPlaying);
      }
      this.destroy();
    },
    setupStream() {
      this.teardown();
      const video = this.videoElement;
      const url = this.url;
      if (!video || !url) {
        return;
      }

      this.fallbackUrl = undefined;
      this.message = '正在连接视频流';

      video.addEventListener('loadedmetadata', this.clearMessage);
      video.addEventListener('canplay', this.clearMessage);
      video.addEventListener('playing', this.markPlaying);

      if (url.endsWith('.mjpeg')) {
        this.fallbackUrl = url;
        this.message = '';
        return;
      }

      if (url.endsWith('.m3u8')) {
        if (video.canPlayType('application/vnd.apple.mpegurl')) {
          video.src = url;
          video.play().then(this.clearMessage).catch(() => {
            this.message = '点击视频播放后端流';
          });
        } else if (Hls.isSupported()) {
          const hls = markRaw(
            new Hls({
              lowLatencyMode: true,
              backBufferLength: 30,
              liveSyncDurationCount: 2,
              liveMaxLatencyDurationCount: 5,
            }),
          );
          this.hls = hls;
          hls.on(Hls.Events.ERROR, (_event, data) => {
            if (data.fatal) {
              this.scheduleRetry();
            }
          });
          hls.on(Hls.Events.MANIFEST_PARSED, () => {
            this.clearRetry();
            video.play().then(this.clearMessage).catch(() => {
              this.message = '点击视频播放后端流';
            });
          });
          hls.attachMedia(video);
          hls.loadSource(url);
        } else {
          this.message = '当前浏览器不支持 HLS 播放';
          return;
        }
      } else if (flvjs.isSupported() && url.endsWith('.flv')) {
        const player = markRaw(
          flvjs.createPlayer(
            { type: 'flv', url, isLive: true },
            {
              enableWorker: false,
              enableStashBuffer: false,
              stashInitialSize: 128,
              autoCleanupSourceBuffer: true,
              autoCleanupMaxBackwardDuration: 30,
              autoCleanupMinBackwardDuration: 10,
              fixAudioTimestampGap: false,
            },
          ),
        );
        this.player = player;
        player.on?.('error', (type: string) => {
          if (type === 'NetworkError' || type === 'MediaError') {
            this.scheduleRetry();
          }
        });
        player.on?.('loading_complete', () => {
          this.scheduleRetry();
        });
        player.attachMediaElement(video);
        player.load();
        player.play().then(this.clearMessage).catch(() => {
          this.message = '点击视频播放后端流';
        });
      } else {
        video.src = url;
        video.play().then(this.clearMessage).catch(() => {
          this.message = '浏览器阻止自动播放';
        });
      }
    },
    move(dx: number, dy: number) {
      this.transform = {
        ...this.transform,
        x: clamp(this.transform.x + dx, -45, 45),
        y: clamp(this.transform.y + dy, -45, 45),
      };
    },
    zoom(delta: number) {
      this.transform = { ...this.transform, zoom: clamp(this.transform.zoom + delta, 1, 3) };
    },
    resetTransform() {
      this.transform = { zoom: 1, x: 0, y: 0 };
    },
    playVideo() {
      const video = this.videoElement;
      if (!video || !this.url) {
        return;
      }
      video.play().then(() => {
        this.message = '';
      }).catch((error) => {
        this.message = `播放失败：${error.message}`;
      });
    },
  },
});

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function zoomClass(zoomValue: number) {
  return `video-zoom-${Math.round(zoomValue * 10)}`;
}

function panClass(axis: 'x' | 'y', value: number) {
  const rounded = Math.round(value);
  const suffix = rounded < 0 ? `n${Math.abs(rounded)}` : `${rounded}`;
  return `video-pan-${axis}-${suffix}`;
}
</script>

<style scoped>
.video-panel {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
}

.video-shell {
  position: relative;
  flex: 1;
  min-height: 0;
  background: #000;
  overflow: hidden;
}

.video-surface {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: #000;
}

.video-surface-hidden {
  visibility: hidden;
}

.video-message {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  z-index: 2;
  padding: 6px 12px;
  border-radius: 4px;
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  font-size: 13px;
  pointer-events: none;
  white-space: nowrap;
}

.ptz-bar {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 8px;
  background: #111;
  color: #fff;
  font-size: 13px;
}

.ptz-bar button {
  width: 28px;
  height: 28px;
  border: 1px solid #333;
  border-radius: 4px;
  background: #1f1f1f;
  color: #fff;
  cursor: pointer;
  line-height: 1;
}

.ptz-bar button:hover {
  background: #2a2a2a;
}

.ptz-bar span {
  margin-left: 8px;
}
</style>
