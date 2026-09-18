<template>
  <section class="video-panel">
    <div
      ref="shell"
      class="video-shell"
      :class="{ 'video-shell-pannable': transform.zoom > 1, 'video-shell-panning': !!panDrag }"
      @mousedown="onPanStart"
    >
      <img
        v-if="fallbackUrl"
        :key="fallbackUrl"
        ref="image"
        :src="fallbackUrl"
        alt="后端视频流"
        :class="surfaceClassName"
        :style="surfaceStyle"
        @load="onImageLoad"
      />
      <video
        ref="video"
        autoplay
        muted
        :controls="nativeControls"
        playsinline
        :class="[surfaceClassName, fallbackUrl ? 'video-surface-hidden' : '']"
        :style="surfaceStyle"
        @click="onSurfaceClick"
      ></video>
      <div v-if="message" class="video-message">{{ message }}</div>
      <div v-if="hevcUnsupported" class="video-hevc-tip">
        <p>当前浏览器不支持 H.265（HEVC）视频解码，无法播放该摄像头画面。</p>
        <p>
          <a :href="hevcStoreLink" target="_blank" rel="noopener">
            点此打开微软商店，免费安装“HEVC 视频扩展”（安装后刷新本页）
          </a>
        </p>
        <p class="video-hevc-alt">
          商店无法打开时可用此链接：
          <a :href="hevcWebLink" target="_blank" rel="noopener">HEVC 视频扩展网页版</a>
          ；也可换用已支持 HEVC 的电脑/浏览器访问。
        </p>
      </div>
    </div>
    <div v-if="showZoomBar" class="ptz-bar" aria-label="数字 PTZ 控制">
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
import mpegts from 'mpegts.js';
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
    // 流格式提示（如 'flv'）：动态链接（/recording-live?...）不带 .flv 后缀时由调用方显式指定
    format: { type: String, default: '' },
    fit: { type: String, default: 'contain' },
    showZoomBar: { type: Boolean, default: true },
    // 是否显示 <video> 原生控制条；回放播放器（自绘工具栏）传 false 隐藏
    nativeControls: { type: Boolean, default: true },
  },
  data() {
    return {
      transform: { zoom: 1, x: 0, y: 0 } as Transform,
      // 电子放大后鼠标拖动画面：记录拖拽起点与基准偏移；moved 区分点击与拖拽
      panDrag: null as {
        startX: number;
        startY: number;
        baseX: number;
        baseY: number;
        moved: boolean;
      } | null,
      // 拖拽结束的 mouseup 会紧跟一次 click，用它抑制误触发的播放/暂停
      suppressClick: false,
      message: '未选择摄像头',
      fallbackUrl: undefined as string | undefined,
      hevcUnsupported: false,
      hevcStoreLink: 'ms-windows-store://pdp/?ProductId=9n4wgh0z6vhq',
      hevcWebLink: 'https://apps.microsoft.com/detail/9n4wgh0z6vhq',
      reloadToken: 0,
      streamToken: 0,
      player: null as mpegts.Player | null,
      hls: null as Hls | null,
      retryTimer: null as number | null,
      retryCount: 0,
      // 当前流是否已禁用音轨：现场部分摄像头（如 4号楼枪机）主码流带 G.711(PCMA) 音频，
      // mpegts.js 不支持会抛 DemuxException/CodecUnsupported 导致整体播放失败，此时按无音频重建
      noAudio: false,
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
        objectFit: this.fit,
      };
    },
  },
  watch: {
    url() {
      // 切换流时恢复音轨自动探测，由新流的报错再决定是否禁用
      this.noAudio = false;
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
    window.removeEventListener('mousemove', this.onPanMove);
    window.removeEventListener('mouseup', this.onPanEnd);
    this.teardown();
  },
  methods: {
    scheduleRetry() {
      if (this.retryTimer !== null) {
        return;
      }
      if (!this.player && !this.hls) {
        // 已销毁的实例不再安排重连
        return;
      }
      const delay = Math.min(2000 * Math.pow(2, this.retryCount), 30000);
      this.retryCount += 1;
      this.message = `视频流重连中（第${this.retryCount}次，${Math.round(delay / 1000)}秒后）`;
      this.retryTimer = window.setTimeout(() => {
        this.retryTimer = null;
        if (!this.player && !this.hls) {
          // 等待期间实例已销毁，放弃重连
          return;
        }
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
    showHevcUnsupported() {
      // 重试无意义：销毁播放器并固定提示，停止自动重连
      this.destroy();
      this.message = '';
      this.hevcUnsupported = true;
    },
    markPlaying() {
      this.clearRetry();
      this.clearMessage();
    },
    // 视频元数据就绪后向父组件抛出真实分辨率，供预览窗格按宽高比适配高度
    emitResolution() {
      const video = this.videoElement;
      if (video && video.videoWidth && video.videoHeight) {
        this.$emit('resolution', { width: video.videoWidth, height: video.videoHeight });
      }
    },
    // mjpeg 图片流无 video 元数据，用图片自然尺寸代替
    onImageLoad() {
      const image = this.$refs.image as HTMLImageElement | undefined;
      if (image && image.naturalWidth && image.naturalHeight) {
        this.$emit('resolution', { width: image.naturalWidth, height: image.naturalHeight });
      }
    },
    destroy() {
      this.cancelRetryTimer();
      const hls = this.hls;
      this.hls = null;
      if (hls) {
        hls.destroy();
      }
      const player = this.player;
      this.player = null;
      const video = this.videoElement;
      if (player) {
        // 立即停画面：只暂停 <video>，不经过 mpegts 内部调用
        if (video) {
          video.pause();
        }
        // mpegts.js 的 Transmuxer 事件投递全部包了一层 Promise.resolve().then(...) 微任务
        // （_onInitSegment/_onMediaSegment/_onMediaInfo 等，dist 堆栈已确认）。同步执行
        // unload/destroy 会把 Transmuxer._emitter 置 null，已排队/在途的微任务随即抛
        // "Cannot read properties of null (reading 'emit')"。因此完整销毁序列
        // （pause → unload → detachMediaElement → destroy）整体推迟 400ms：
        // 微任务与在途 IO 回调在 emitter 存活期间落地（本组件 token 守卫使其成为 no-op），
        // MSE append 在延迟窗口内的异常由 mpegts 内部 try/catch 兜底。
        const token = this.streamToken;
        window.setTimeout(() => {
          // <video> 已被新流接管（token 变更/元素更换）时，先摘掉旧播放器对元素的引用：
          // mpegts 的 unload()/destroy() 会 pause() 其 _media_element（在引擎 _player_engine 上），
          // 不摘掉会把新流刚起的播放停掉
          const elementTakenOver = token !== this.streamToken || (video ? this.videoElement !== video : false);
          if (elementTakenOver) {
            try {
              (player as any)._media_element = null;
              const engine = (player as any)._player_engine;
              if (engine) {
                engine._media_element = null;
              }
            } catch {
              // 忽略
            }
          }
          try {
            if (!elementTakenOver) {
              player.pause();
            }
          } catch {
            // 播放器内部状态异常时仍继续销毁
          }
          try {
            player.unload();
          } catch {
            // 同上
          }
          try {
            if (video && this.videoElement === video && token === this.streamToken) {
              // <video> 未被新流接管：走标准 detach（清理元素 src、回收 blob URL、销毁 MSE）
              player.detachMediaElement();
            } else {
              // <video> 已被新流接管（或组件已卸载）：跳过 detachMediaElement 中对元素的
              // 操作（否则会清掉新流的 src），仅清理旧 MSE 内部状态后放行 destroy
              const engine = (player as any)._player_engine;
              if (engine) {
                try {
                  engine._mse_controller?.destroy?.();
                } catch {
                  // 忽略
                }
                engine._mse_controller = null;
                engine._media_element = null;
              }
            }
          } catch {
            // 同上
          }
          try {
            player.destroy();
          } catch {
            // 已销毁或内部状态异常，忽略
          }
        }, 400);
      } else if (video) {
        // 非 mpegts 路径（原生 HLS / 直链 mp4）：立即清理元素
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
        video.removeEventListener('loadedmetadata', this.emitResolution);
        video.removeEventListener('canplay', this.clearMessage);
        video.removeEventListener('playing', this.markPlaying);
      }
      this.destroy();
    },
    setupStream() {
      this.teardown();
      // 令牌递增：旧实例的回调（重连/error/media_info）在销毁后不再生效
      const token = ++this.streamToken;
      const video = this.videoElement;
      const url = this.url;
      if (!video || !url) {
        return;
      }

      this.fallbackUrl = undefined;
      this.hevcUnsupported = false;
      this.message = '正在连接视频流';

      video.addEventListener('loadedmetadata', this.clearMessage);
      video.addEventListener('loadedmetadata', this.emitResolution);
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
            if (token !== this.streamToken || this.hls !== hls) return;
            if (data.fatal) {
              this.scheduleRetry();
            }
          });
          hls.on(Hls.Events.MANIFEST_PARSED, () => {
            if (token !== this.streamToken || this.hls !== hls) return;
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
      } else if (mpegts.isSupported() && (this.format === 'flv' || url.endsWith('.flv'))) {
        // mpegts.js 兼容 flv.js API，同时支持 H.264 和 H.265（FLV CodecID 12）passthrough
        const player = markRaw(
          mpegts.createPlayer(
            { type: 'flv', url, isLive: true, hasAudio: !this.noAudio },
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
        // H.265 passthrough 要求浏览器支持 HEVC MSE；在 media_info 拿到真实编码串后先探测，
        // 不支持时给中文提示，避免 mpegts.js 抛出 addSourceBuffer 英文原始报错
        player.on?.('media_info', (info: { videoCodec?: string }) => {
          if (token !== this.streamToken || this.player !== player) return;
          const codec = info?.videoCodec || '';
          if (isHevcCodec(codec) && !canPlayHevc(codec)) {
            this.showHevcUnsupported();
          }
        });
        player.on?.('error', (type: string, details?: unknown, data?: unknown) => {
          if (token !== this.streamToken || this.player !== player) return;
          if (type === 'MediaError' && isHevcError(details, data)) {
            this.showHevcUnsupported();
            return;
          }
          // G.711(PCMA) 等 mpegts.js 不支持的音轨会让解复用整体失败（内部以 MediaError/CodecUnsupported
          // 上报，info 形如 "Flv: Unsupported audio codec idx: 7"）：改为无音频重建（忽略音轨）
          if (type === 'MediaError' && !this.noAudio && isUnsupportedAudioError(details, data)) {
            this.noAudio = true;
            this.restart();
            return;
          }
          if (type === 'NetworkError' || type === 'MediaError') {
            this.scheduleRetry();
          }
        });
        player.on?.('loading_complete', () => {
          if (token !== this.streamToken || this.player !== player) return;
          this.scheduleRetry();
        });
        player.attachMediaElement(video);
        player.load();
        Promise.resolve(player.play()).then(this.clearMessage).catch(() => {
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
    // 电子放大（zoom > 1）后按住鼠标拖动画面平移；拖完后抑制一次 click，避免误触发播放
    onPanStart(event: MouseEvent) {
      if (event.button !== 0 || this.transform.zoom <= 1) {
        return;
      }
      // 避开 <video> 原生控制条区域（底部 ~40px），不与进度条等控件争抢拖动
      const target = event.target as HTMLElement;
      if (target === this.videoElement) {
        const rect = target.getBoundingClientRect();
        if (event.clientY > rect.bottom - 40) {
          return;
        }
      }
      this.panDrag = {
        startX: event.clientX,
        startY: event.clientY,
        baseX: this.transform.x,
        baseY: this.transform.y,
        moved: false,
      };
      window.addEventListener('mousemove', this.onPanMove);
      window.addEventListener('mouseup', this.onPanEnd);
      event.preventDefault();
    },
    onPanMove(event: MouseEvent) {
      const drag = this.panDrag;
      const shell = this.$refs.shell as HTMLElement | undefined;
      if (!drag || !shell) {
        return;
      }
      if (!drag.moved) {
        // 小位移视为点击，不进入拖拽
        if (Math.abs(event.clientX - drag.startX) + Math.abs(event.clientY - drag.startY) < 4) {
          return;
        }
        drag.moved = true;
      }
      const rect = shell.getBoundingClientRect();
      if (!rect.width || !rect.height) {
        return;
      }
      this.transform = {
        ...this.transform,
        x: clamp(drag.baseX + ((event.clientX - drag.startX) / rect.width) * 100, -45, 45),
        y: clamp(drag.baseY + ((event.clientY - drag.startY) / rect.height) * 100, -45, 45),
      };
    },
    onPanEnd() {
      if (this.panDrag?.moved) {
        this.suppressClick = true;
        window.setTimeout(() => {
          this.suppressClick = false;
        }, 0);
      }
      this.panDrag = null;
      window.removeEventListener('mousemove', this.onPanMove);
      window.removeEventListener('mouseup', this.onPanEnd);
    },
    onSurfaceClick() {
      if (this.suppressClick) {
        return;
      }
      this.playVideo();
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
        if (isHevcError(error?.message, '')) {
          this.showHevcUnsupported();
          return;
        }
        this.message = `播放失败：${error.message}`;
      });
    },
    // --- 供父组件（实时预览/录像回放工具栏）调用的播放控制 ---
    isPaused(): boolean {
      const video = this.videoElement;
      return video ? video.paused : true;
    },
    pause() {
      this.videoElement?.pause();
    },
    resume() {
      if (!this.player && !this.hls && !this.fallbackUrl && !this.videoElement?.src) {
        // 已停止：重建流
        this.restart();
        return;
      }
      this.playVideo();
    },
    stop() {
      this.teardown();
      this.fallbackUrl = undefined;
      this.hevcUnsupported = false;
      this.message = '已停止';
    },
    restart() {
      this.reloadToken += 1;
    },
    setMuted(muted: boolean) {
      const video = this.videoElement;
      if (video) {
        video.muted = muted;
      }
    },
    isMuted(): boolean {
      const video = this.videoElement;
      return video ? video.muted : true;
    },
    // 抓取当前画面为 JPEG dataURL；mjpeg 图片跨域受污染或无可抓画面时返回 null
    snapshot(mimeType: string = 'image/jpeg', quality = 0.92): string | null {
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      if (!ctx) {
        return null;
      }
      try {
        if (!this.fallbackUrl) {
          const video = this.videoElement;
          if (!video || !video.videoWidth) {
            return null;
          }
          canvas.width = video.videoWidth;
          canvas.height = video.videoHeight;
          ctx.drawImage(video, 0, 0);
        } else {
          const image = this.$refs.image as HTMLImageElement | undefined;
          if (!image || !image.naturalWidth) {
            return null;
          }
          canvas.width = image.naturalWidth;
          canvas.height = image.naturalHeight;
          ctx.drawImage(image, 0, 0);
        }
        return canvas.toDataURL(mimeType, quality);
      } catch {
        return null;
      }
    },
  },
});

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

/** FLV 视频编码串是否为 H.265/HEVC（如 hvc1.1.1.L150.B0、hev1.2.4.L153.B0）。 */
function isHevcCodec(codec: string): boolean {
  return /^(hvc1|hev1|h265|hevc)/i.test(codec.trim());
}

/** 浏览器 MSE 是否能解码该 HEVC 编码串（依赖操作系统 HEVC 解码器）。 */
function canPlayHevc(codec: string): boolean {
  if (typeof MediaSource === 'undefined' || !MediaSource.isTypeSupported) {
    return false;
  }
  const candidates = [codec, 'hvc1.1.6.L123.00', 'hev1.1.6.L123.00'];
  return candidates.some((c) => MediaSource.isTypeSupported(`video/mp4; codecs="${c}"`));
}

/** mpegts.js DemuxException 是否为不支持的音频编码（如 G.711/PCMA，info 形如 "Flv: Unsupported audio codec idx: 7"）。 */
function isUnsupportedAudioError(details: unknown, data: unknown): boolean {
  if (String(details || '') !== 'CodecUnsupported') {
    return false;
  }
  return /audio/i.test(isHevcErrorText(data));
}

/** 与 isHevcError 相同的文本提取，供其它错误判定复用。 */
function isHevcErrorText(value: unknown): string {
  if (!value) {
    return '';
  }
  if (typeof value === 'string') {
    return value;
  }
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

/** mpegts.js MediaError 的 details/data 是否为 HEVC 不支持报错。 */
function isHevcError(details: unknown, data: unknown): boolean {
  const text = [details, data]
    .map((item) => {
      if (!item) {
        return '';
      }
      if (typeof item === 'string') {
        return item;
      }
      try {
        return JSON.stringify(item);
      } catch {
        return String(item);
      }
    })
    .join(' ');
  return /hvc1|hev1|h265|hevc/i.test(text);
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

/* 电子放大后画面可拖动平移 */
.video-shell-pannable .video-surface {
  cursor: grab;
}

.video-shell-panning .video-surface {
  cursor: grabbing;
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

.video-hevc-tip {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  z-index: 3;
  max-width: 85%;
  padding: 12px 16px;
  border-radius: 6px;
  background: rgba(0, 0, 0, 0.75);
  color: #fff;
  font-size: 13px;
  line-height: 1.7;
  text-align: center;
}

.video-hevc-tip p {
  margin: 4px 0;
}

.video-hevc-tip a {
  color: #4da3ff;
  text-decoration: underline;
}

.video-hevc-tip .video-hevc-alt {
  color: #bbb;
  font-size: 12px;
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
