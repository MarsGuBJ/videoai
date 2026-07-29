import { useState, useEffect, useCallback } from 'react';
import {
  Play, Pause, SkipBack, SkipForward, FastForward, Rewind, Download, Monitor, Calendar, Clock,
  Maximize2, LayoutGrid, Columns2, Image as ImageIcon, Video as VideoIcon,
  Cloud, CalendarDays,
} from 'lucide-react';
import { api } from '../../api';
import type { Camera as CameraType } from '../../types';

type PlaybackMode = 'normal' | 'segment' | 'sync';
type ProgressMode = 'time-moving' | 'fixed-length';
type Speed = -16 | -8 | -4 | -2 | -1 | 1 | 2 | 4 | 8 | 16;

export function Playback() {
  const [cameras, setCameras] = useState<CameraType[]>([]);
  const [selectedCameraId, setSelectedCameraId] = useState('');
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().slice(0, 10));
  const [endDate, setEndDate] = useState(new Date().toISOString().slice(0, 10));
  const [mode, setMode] = useState<PlaybackMode>('normal');
  const [segmentCount, setSegmentCount] = useState(4);
  const [progressMode, setProgressMode] = useState<ProgressMode>('time-moving');
  const [speed, setSpeed] = useState<Speed>(1);
  const [playing, setPlaying] = useState(false);
  const [displayCount, setDisplayCount] = useState(1);
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [showDownload, setShowDownload] = useState(false);
  const [showCloudSearch, setShowCloudSearch] = useState(false);
  const [recordType, setRecordType] = useState('all');

  const load = useCallback(async () => {
    const list = await api.cameras();
    setCameras(list);
    if (list.length > 0 && !selectedCameraId) setSelectedCameraId(list[0].id);
  }, [selectedCameraId]);

  useEffect(() => { load(); }, [load]);

  const selectedCamera = cameras.find(c => c.id === selectedCameraId);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
      if (e.code === 'Space') { e.preventDefault(); setPlaying(p => !p); }
      else if (e.key === 'ArrowRight') {
        e.preventDefault();
        setSpeed(s => {
          if (s < 0) {
            const next = Math.min(-1, s * 2);
            return (next as Speed);
          }
          const next = Math.min(16, s * 2);
          return (next as Speed);
        });
      }
      else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        setSpeed(s => {
          if (s < 0) {
            const next = Math.max(-16, s / 2);
            return (next as Speed);
          }
          const next = Math.max(1, s / 2);
          return (next as Speed);
        });
      }
      else if (e.key === 'ArrowUp') { e.preventDefault(); }
      else if (e.key === 'ArrowDown') { e.preventDefault(); setSpeed(1); }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  const cycleDisplay = () => {
    setDisplayCount(prev => {
      if (mode === 'segment') return prev === 4 ? 9 : prev === 9 ? 16 : 4;
      return prev === 1 ? 4 : prev === 4 ? 9 : prev === 9 ? 16 : 1;
    });
  };

  return (
    <>
      <header className="topbar">
        <div><h1>录像回放</h1><p>检索和回放历史录像</p></div>
        <div className="button-row">
          <button onClick={() => setShowCloudSearch(true)}><Cloud size={15} />录像云检索</button>
          <button onClick={() => setShowDownload(true)}><Download size={15} />录像下载</button>
        </div>
      </header>

      <div className="playback-controls">
        <div className="playback-row">
          <div className="playback-filters">
            <div className="filter-group">
              <label>摄像头</label>
              <select value={selectedCameraId} onChange={e => setSelectedCameraId(e.target.value)}>
                {cameras.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div className="filter-group">
              <label>开始日期</label>
              <div className="date-picker-trigger" onClick={() => setShowDatePicker(!showDatePicker)}>
                <Calendar size={15} />
                <span>{selectedDate}</span>
              </div>
            </div>
            <div className="filter-group">
              <label>结束日期</label>
              <div className="date-picker-trigger">
                <CalendarDays size={15} />
                <span>{endDate}</span>
              </div>
            </div>
            <div className="filter-group">
              <label>开始时间</label>
              <input type="time" defaultValue="00:00" />
            </div>
            <div className="filter-group">
              <label>结束时间</label>
              <input type="time" defaultValue="23:59" />
            </div>
            <div className="filter-group">
              <label>录像类型</label>
              <select value={recordType} onChange={e => setRecordType(e.target.value)}>
                <option value="all">全部</option>
                <option value="normal">普通录像</option>
                <option value="alarm">报警录像</option>
                <option value="motion">移动侦测</option>
                <option value="timing">定时录像</option>
                <option value="manual">手动录像</option>
              </select>
            </div>
            <div className="filter-group">
              <label>回放模式</label>
              <select value={mode} onChange={e => setMode(e.target.value as PlaybackMode)}>
                <option value="normal">常规回放</option>
                <option value="segment">分段回放</option>
                <option value="sync">同步回放</option>
              </select>
            </div>
            <button className="search-btn"><Clock size={15} />检索</button>
          </div>
        </div>

        <div className="playback-toolbar">
          <div className="toolbar-left">
            <button className={mode === 'segment' ? 'active' : ''} onClick={() => setMode(mode === 'segment' ? 'normal' : 'segment')}>
              <LayoutGrid size={15} />
              {mode === 'segment' ? '退出分段' : '分段回放'}
            </button>
            <button className={mode === 'sync' ? 'active' : ''} onClick={() => setMode(mode === 'sync' ? 'normal' : 'sync')}>
              <Columns2 size={15} />
              {mode === 'sync' ? '退出同步' : '同步回放'}
            </button>
            <button onClick={cycleDisplay}>
              <Maximize2 size={15} />{displayCount}画面
            </button>
            <span className="toolbar-sep" />
            <button onClick={() => setProgressMode(p => p === 'time-moving' ? 'fixed-length' : 'time-moving')}>
              <Clock size={15} />{progressMode === 'time-moving' ? '随时间移动' : '固定长度'}
            </button>
            {mode === 'segment' && (
              <>
                <span className="toolbar-sep" />
                <select value={segmentCount} onChange={e => setSegmentCount(Number(e.target.value))}>
                  <option value={4}>4 分段</option>
                  <option value={9}>9 分段</option>
                  <option value={16}>16 分段</option>
                </select>
              </>
            )}
          </div>
          <div className="toolbar-right">
            <button title="切换实况" onClick={() => {}}><Monitor size={15} />实况</button>
            <button title="下载" onClick={() => setShowDownload(true)}><Download size={15} />下载</button>
          </div>
        </div>
      </div>

      <div className="playback-main">
        <div className={`playback-video-grid playback-cols-${displayCount <= 4 ? 2 : 3}`}>
          {Array.from({ length: displayCount }).map((_, idx) => (
            <div key={idx} className="playback-cell">
              <div className="split-label">
                <span>{selectedCamera?.name || '未选择'} {idx > 0 ? `· 通道 ${idx + 1}` : ''}</span>
              </div>
              <div className="playback-placeholder">
                <Play size={32} />
                <span>{mode === 'segment' ? `${segmentCount}分段回放` : mode === 'sync' ? '同步回放' : '常规回放'}</span>
              </div>
            </div>
          ))}
        </div>

        <div className="timeline-section">
          <div className="progress-mode-bar">
            <span className="timeline-time">00:00</span>
            <div className="progress-track">
              <div className="progress-fill progress-position-35" />
              <div className="progress-thumb progress-position-35" />
              {mode === 'segment' && Array.from({ length: segmentCount }).map((_, i) => {
                return (
                  <div key={i} className={`segment-marker segment-count-${segmentCount} segment-marker-${i + 1}`}>段 {i + 1}</div>
                );
              })}
              <div className={`progress-needle ${progressMode === 'time-moving' ? 'progress-position-50' : 'progress-position-35'}`} />
            </div>
            <span className="timeline-time">23:59</span>
          </div>
          <div className="progress-mode-info">
            {progressMode === 'time-moving' ? (
              <span>随时间移动模式：进度条刻度在中间，进度条随时间移动</span>
            ) : (
              <span>固定长度模式：最左为查询起始时间，最右为结束时间</span>
            )}
          </div>

          <div className="playback-control-bar">
            <div className="control-left">
              <button onClick={() => setSpeed(-16)} title="-16x 倒放"><SkipBack size={16} /></button>
              <button onClick={() => setSpeed(s => {
                if (s < 0) {
                  const next = Math.max(-16, s / 2);
                  return (next as Speed);
                }
                return -1 as Speed;
              })} title="减速"><Rewind size={16} /></button>
              <button className="play-btn" onClick={() => setPlaying(!playing)}>
                {playing ? <Pause size={18} /> : <Play size={18} />}
              </button>
              <button onClick={() => setSpeed(s => {
                if (s < 0) return 1 as Speed;
                const next = Math.min(16, s * 2);
                return (next as Speed);
              })} title="加速"><FastForward size={16} /></button>
              <button onClick={() => setSpeed(1)} title="1倍速恢复"><SkipForward size={16} /></button>
              <span className="speed-label">{speedLabel(speed)}</span>
            </div>
            <div className="control-right">
              <span className="time-label">2026-06-22 14:35:00</span>
              <button title="单帧正放">单帧</button>
              <button title="截图"><ImageIcon size={15} /></button>
              <button title="本地录像"><VideoIcon size={15} /></button>
            </div>
          </div>

          <div className="keyboard-hints">
            <span>快捷键：</span>
            <kbd>Space</kbd> 暂停/恢复
            <kbd>←</kbd><kbd>→</kbd> 切倍速
            <kbd>↑</kbd> 单帧播放
            <kbd>↓</kbd> 恢复1倍速
          </div>
        </div>
      </div>

      {showDatePicker && (
        <div className="modal-overlay" onClick={() => setShowDatePicker(false)}>
          <div className="date-picker-modal" onClick={e => e.stopPropagation()}>
            <div className="modal-title">选择日期范围（跨天回放）</div>
            <div className="device-form">
              <label><span>开始日期</span><input type="date" value={selectedDate} onChange={e => setSelectedDate(e.target.value)} /></label>
              <label><span>结束日期</span><input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} /></label>
            </div>
            <p className="hint">默认支持跨天查询 3 天内的录像</p>
            <div className="button-row modal-actions">
              <button onClick={() => setShowDatePicker(false)}>确定</button>
              <button onClick={() => setShowDatePicker(false)}>取消</button>
            </div>
          </div>
        </div>
      )}

      {showDownload && (
        <DownloadDialog onClose={() => setShowDownload(false)} cameras={cameras} selectedCameraId={selectedCameraId} />
      )}

      {showCloudSearch && (
        <CloudSearchDialog onClose={() => setShowCloudSearch(false)} cameras={cameras} selectedCameraId={selectedCameraId} />
      )}
    </>
  );
}

function speedLabel(s: Speed): string {
  if (s > 0) return `${s}x 正放`;
  return `${-s}x 倒放`;
}

function DownloadDialog({ onClose, cameras, selectedCameraId }: { onClose: () => void; cameras: CameraType[]; selectedCameraId: string }) {
  const [startTime, setStartTime] = useState('00:00');
  const [endTime, setEndTime] = useState('23:59');
  const [downloadSpeed, setDownloadSpeed] = useState(4);
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-title">录像下载</div>
        <div className="device-form">
          <label><span>摄像头</span>
            <select defaultValue={selectedCameraId}>
              {cameras.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </label>
          <label><span>下载日期</span><input type="date" defaultValue="2026-06-22" /></label>
          <label><span>开始时间</span><input type="time" value={startTime} onChange={e => setStartTime(e.target.value)} /></label>
          <label><span>结束时间</span><input type="time" value={endTime} onChange={e => setEndTime(e.target.value)} /></label>
          <label><span>下载倍速</span>
            <select value={downloadSpeed} onChange={e => setDownloadSpeed(Number(e.target.value))}>
              {[2, 4, 8, 16, 32, 64].map(n => <option key={n} value={n}>{n}x</option>)}
            </select>
          </label>
          <label><span>录像格式</span>
            <select><option>MP4</option><option>AVI</option></select>
          </label>
        </div>
        <div className="button-row modal-actions">
          <button>开始下载</button>
          <button onClick={onClose}>取消</button>
        </div>
      </div>
    </div>
  );
}

function CloudSearchDialog({ onClose, cameras, selectedCameraId }: { onClose: () => void; cameras: CameraType[]; selectedCameraId: string }) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-title">录像云检索</div>
        <p className="hint">优先从本级平台录像查询，若本级无录像则查询下级录像/设备录像</p>
        <div className="device-form">
          <label><span>摄像头</span>
            <select defaultValue={selectedCameraId}>
              {cameras.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </label>
          <label><span>查询日期</span><input type="date" defaultValue="2026-06-22" /></label>
          <label><span>时间段</span>
            <select><option>全天</option><option>工作时间</option><option>自定义</option></select>
          </label>
        </div>
        <div className="cloud-search-results">
          <div className="result-section">
            <div className="result-title">本级平台录像 <span className="count">3 段</span></div>
            <div className="result-list">
              <div className="result-item">08:30:00 - 09:15:23</div>
              <div className="result-item">10:42:11 - 11:30:45</div>
              <div className="result-item">14:20:00 - 15:00:12</div>
            </div>
          </div>
          <div className="result-section">
            <div className="result-title">下级录像/设备录像 <span className="count">2 段</span></div>
            <div className="result-list">
              <div className="result-item">06:15:30 - 07:00:00</div>
              <div className="result-item">20:30:00 - 21:45:30</div>
            </div>
          </div>
        </div>
        <div className="button-row modal-actions">
          <button>下载选中</button>
          <button onClick={onClose}>关闭</button>
        </div>
      </div>
    </div>
  );
}
