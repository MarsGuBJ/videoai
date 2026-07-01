import { useEffect, useRef, useState } from 'react';
import flvjs from 'flv.js';
import Hls from 'hls.js';
import { ArrowDown, ArrowLeft, ArrowRight, ArrowUp, Minus, Plus, RotateCcw } from 'lucide-react';
import type { Player } from 'flv.js';

type Props = {
  url?: string;
};

type Transform = {
  zoom: number;
  x: number;
  y: number;
};

export function VideoPlayer({ url }: Props) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const playerRef = useRef<Player | null>(null);
  const hlsRef = useRef<Hls | null>(null);
  const retryTimerRef = useRef<number | null>(null);
  const retryCountRef = useRef(0);
  const [transform, setTransform] = useState<Transform>({ zoom: 1, x: 0, y: 0 });
  const [message, setMessage] = useState('未选择摄像头');
  const [fallbackUrl, setFallbackUrl] = useState<string | undefined>();
  const [reloadToken, setReloadToken] = useState(0);

  const scheduleRetry = () => {
    if (retryTimerRef.current !== null) {
      return;
    }
    const delay = Math.min(2000 * Math.pow(2, retryCountRef.current), 30000);
    retryCountRef.current += 1;
    setMessage(`视频流重连中（第${retryCountRef.current}次，${Math.round(delay / 1000)}秒后）`);
    retryTimerRef.current = window.setTimeout(() => {
      retryTimerRef.current = null;
      setReloadToken((t) => t + 1);
    }, delay);
  };

  const clearRetry = () => {
    if (retryTimerRef.current !== null) {
      window.clearTimeout(retryTimerRef.current);
      retryTimerRef.current = null;
    }
    retryCountRef.current = 0;
  };

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !url) {
      return;
    }
    const clearMessage = () => setMessage('');

    const destroy = () => {
      clearRetry();
      if (hlsRef.current) {
        hlsRef.current.destroy();
        hlsRef.current = null;
      }
      if (playerRef.current) {
        playerRef.current.destroy();
        playerRef.current = null;
      }
      if (video) {
        video.srcObject = null;
        video.removeAttribute('src');
        video.load();
      }
    };

    destroy();

    video.removeEventListener('loadedmetadata', clearMessage);
    video.removeEventListener('canplay', clearMessage);
    video.removeEventListener('playing', clearMessage);

    setFallbackUrl(undefined);
    setMessage('正在连接视频流');

    video.addEventListener('loadedmetadata', clearMessage);
    video.addEventListener('canplay', clearMessage);
    video.addEventListener('playing', clearMessage);

    let fallbackTimer: number | undefined;

    if (url.endsWith('.mjpeg')) {
      setFallbackUrl(url);
      setMessage('');
      return;
    }

    if (url.endsWith('.m3u8')) {
      fallbackTimer = window.setTimeout(() => {
        if (video.paused || video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) {
          const mjpegUrl = hlsToMjpegUrl(url);
          if (mjpegUrl) {
            setFallbackUrl(mjpegUrl);
            setMessage('');
          }
        }
      }, 7000);
      if (video.canPlayType('application/vnd.apple.mpegurl')) {
        video.src = url;
        video.play().then(clearMessage).catch(() => setMessage('点击视频播放后端流'));
      } else if (Hls.isSupported()) {
        const hls = new Hls({ lowLatencyMode: true });
        hlsRef.current = hls;
        hls.on(Hls.Events.ERROR, (_event, data) => {
          if (data.fatal) {
            scheduleRetry();
          }
        });
        hls.on(Hls.Events.MANIFEST_PARSED, () => {
          clearRetry();
          video.play().then(clearMessage).catch(() => setMessage('点击视频播放后端流'));
        });
        hls.attachMedia(video);
        hls.loadSource(url);
      } else {
        setMessage('当前浏览器不支持 HLS 播放');
        return;
      }
    } else if (flvjs.isSupported() && url.endsWith('.flv')) {
      const player = flvjs.createPlayer(
        { type: 'flv', url, isLive: true },
        { enableWorker: false },
      );
      playerRef.current = player;
      player.on?.('error', (type: string, detail: string) => {
        if (type === 'NetworkError' || type === 'MediaError') {
          scheduleRetry();
        }
      });
      player.on?.('loading_complete', () => {
        clearRetry();
        setMessage('');
      });
      player.attachMediaElement(video);
      player.load();
      player.play().then(clearMessage).catch(() => setMessage('点击视频播放后端流'));
    } else {
      video.src = url;
      video.play().then(clearMessage).catch(() => setMessage('浏览器阻止自动播放'));
    }

    return () => {
      video.removeEventListener('loadedmetadata', clearMessage);
      video.removeEventListener('canplay', clearMessage);
      video.removeEventListener('playing', clearMessage);
      if (fallbackTimer) {
        window.clearTimeout(fallbackTimer);
      }
      destroy();
    };
  }, [url, reloadToken]);

  const move = (dx: number, dy: number) => {
    setTransform((current) => ({
      ...current,
      x: clamp(current.x + dx, -45, 45),
      y: clamp(current.y + dy, -45, 45),
    }));
  };

  const zoom = (delta: number) => {
    setTransform((current) => ({ ...current, zoom: clamp(current.zoom + delta, 1, 3) }));
  };

  const playVideo = () => {
    const video = videoRef.current;
    if (!video || !url) {
      return;
    }
    video.play().then(() => setMessage('')).catch((error) => setMessage(`播放失败：${error.message}`));
  };

  const videoStyle = {
    transform: `scale(${transform.zoom}) translate(${transform.x}px, ${transform.y}px)`,
  };

  return (
    <section className="video-panel">
      <div className="video-shell">
        {fallbackUrl && (
          <img src={fallbackUrl} alt="后端视频流" className="video-surface" style={videoStyle} />
        )}
        <video
          ref={videoRef}
          muted
          controls
          playsInline
          className="video-surface"
          style={{ ...videoStyle, display: fallbackUrl ? 'none' : undefined }}
          onClick={playVideo}
        />
        {message && <div className="video-message">{message}</div>}
      </div>
      <div className="ptz-bar" aria-label="数字 PTZ 控制">
        <button title="拉近" onClick={() => zoom(0.2)}><Plus size={16} /></button>
        <button title="拉远" onClick={() => zoom(-0.2)}><Minus size={16} /></button>
        <button title="向上" onClick={() => move(0, 12)}><ArrowUp size={16} /></button>
        <button title="向下" onClick={() => move(0, -12)}><ArrowDown size={16} /></button>
        <button title="向左" onClick={() => move(12, 0)}><ArrowLeft size={16} /></button>
        <button title="向右" onClick={() => move(-12, 0)}><ArrowRight size={16} /></button>
        <button title="重置" onClick={() => setTransform({ zoom: 1, x: 0, y: 0 })}><RotateCcw size={16} /></button>
        <span>{transform.zoom.toFixed(1)}x</span>
      </div>
    </section>
  );
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function hlsToMjpegUrl(url: string) {
  const parsed = new URL(url, window.location.href);
  if (!parsed.pathname.endsWith('.m3u8')) {
    return undefined;
  }
  parsed.pathname = parsed.pathname.replace(/\.m3u8$/, '.mjpeg');
  parsed.search = '';
  return parsed.toString();
}
