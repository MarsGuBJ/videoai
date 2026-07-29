import { useEffect, useMemo, useRef, useState, useCallback } from 'react';
import type { MouseEvent } from 'react';
import {
  Grid3X3, Columns3, Columns4, Maximize2, Camera, Bookmark, History,
  ArrowUp, ArrowDown, ArrowLeft, ArrowRight, Plus, Minus, RotateCcw, Target, Image as ImageIcon,
  Video as VideoIcon, RefreshCw, Repeat, Lightbulb, Cloud, Unlock, User,
  Layers, Save, Trash2, Edit3, ChevronRight, ChevronLeft, Settings,
} from 'lucide-react';
import { api, cameraStreamUrl } from '../../api';
import { VideoPlayer } from '../../VideoPlayer';
import type { Camera as CameraType, PtzCommand } from '../../types';

const LAYOUTS = [1, 2, 3, 4, 6, 7, 8, 9, 10, 13, 14, 16, 17, 25, 32, 36, 64];

const LAYOUT_MATRICES: Record<number, { cols: number; rows: number }> = {
  1: { cols: 1, rows: 1 }, 2: { cols: 2, rows: 1 }, 3: { cols: 3, rows: 1 },
  4: { cols: 2, rows: 2 }, 6: { cols: 3, rows: 2 }, 7: { cols: 4, rows: 2 },
  8: { cols: 4, rows: 2 }, 9: { cols: 3, rows: 3 }, 10: { cols: 5, rows: 2 },
  13: { cols: 5, rows: 3 }, 14: { cols: 5, rows: 3 }, 16: { cols: 4, rows: 4 },
  17: { cols: 6, rows: 3 }, 25: { cols: 5, rows: 5 }, 32: { cols: 8, rows: 4 },
  36: { cols: 6, rows: 6 }, 64: { cols: 8, rows: 8 },
};

function splitLayoutClass(count: number) {
  const matrix = LAYOUT_MATRICES[count] || { cols: 2, rows: 2 };
  return `split-cols-${matrix.cols} split-rows-${matrix.rows}`;
}

type DisplayRatio = 'aspect' | 'stretch';
type CornerPanMode = 'off' | 'on';

export function LivePreview() {
  const [cameras, setCameras] = useState<CameraType[]>([]);
  const [splitCount, setSplitCount] = useState(4);

  const showAll = useCallback(() => {
    const total = cameras.length;
    const target = LAYOUTS.find(n => n >= total) ?? LAYOUTS[LAYOUTS.length - 1];
    setSplitCount(target);
  }, [cameras]);
  const [fullscreen, setFullscreen] = useState(false);
  const [showPtz, setShowPtz] = useState(false);
  const [showFavorites, setShowFavorites] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [showPatrol, setShowPatrol] = useState(false);
  const [showParams, setShowParams] = useState(false);
  const [showInstantPlayback, setShowInstantPlayback] = useState(false);
  const [selectedCameraId, setSelectedCameraId] = useState<string>('');
  const [mainSub, setMainSub] = useState<'main' | 'sub' | 'auto'>('main');
  const [displayRatio, setDisplayRatio] = useState<DisplayRatio>('aspect');
  const [corridorMode, setCorridorMode] = useState<CornerPanMode>('off');
  const [virtualPtz, setVirtualPtz] = useState<CornerPanMode>('off');
  const [electronicZoom, setElectronicZoom] = useState<CornerPanMode>('off');
  const [favorites, setFavorites] = useState<{ id: string; name: string; cameraId: string }[]>([]);
  const [history] = useState<{ id: string; name: string; time: string; cameraId: string }[]>([
    { id: 'h1', name: '大门入口', time: '2026-06-22 14:30', cameraId: '' },
    { id: 'h2', name: '停车场', time: '2026-06-22 14:25', cameraId: '' },
  ]);
  const [patrolPlans, setPatrolPlans] = useState<{ id: string; name: string; windows: number; duration: number; cameras: string[] }[]>([
    { id: 'p1', name: '大门巡逻', windows: 4, duration: 30, cameras: ['cam-1', 'cam-2'] },
  ]);
  const [editingPatrol, setEditingPatrol] = useState<typeof patrolPlans[0] | null>(null);
  const [cellOrder, setCellOrder] = useState<number[]>([]);
  const [draggedIdx, setDraggedIdx] = useState<number | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const startRequestsRef = useRef(new Set<string>());

  const load = useCallback(async () => {
    const list = await api.cameras();
    setCameras(list);
    setSelectedCameraId(prev => prev || list[0]?.id || '');
  }, []);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    setCellOrder(Array.from({ length: splitCount }, (_, i) => i));
  }, [splitCount]);

  const splitLayout = splitLayoutClass(splitCount);
  const selectedCameraIndex = useMemo(() => {
    const index = cameras.findIndex(c => c.id === selectedCameraId);
    return index >= 0 ? index : 0;
  }, [cameras, selectedCameraId]);
  const visibleCameras = useMemo(() => {
    if (splitCount === 1) {
      const camera = cameras[selectedCameraIndex];
      return camera ? [camera] : [];
    }
    return cameras.slice(0, splitCount);
  }, [cameras, selectedCameraIndex, splitCount]);

  useEffect(() => {
    const stoppedCameras = visibleCameras.filter(camera => camera.status !== 'RUNNING'
      && !startRequestsRef.current.has(camera.id));
    for (const camera of stoppedCameras) {
      startRequestsRef.current.add(camera.id);
      void api.startCamera(camera.id)
        .then(started => {
          setCameras(current => current.map(item => item.id === started.id ? started : item));
        })
        .catch(() => undefined)
        .finally(() => {
          startRequestsRef.current.delete(camera.id);
        });
    }
  }, [visibleCameras]);

  const selectedCamera = useMemo(
    () => cameras.find(c => c.id === selectedCameraId),
    [cameras, selectedCameraId],
  );

  useEffect(() => {
    if (cameras.length === 0) {
      if (selectedCameraId) setSelectedCameraId('');
      return;
    }
    if (!cameras.some(c => c.id === selectedCameraId)) {
      setSelectedCameraId(cameras[0].id);
    }
  }, [cameras, selectedCameraId]);

  useEffect(() => {
    if (showPtz && !selectedCameraId && visibleCameras[0]) {
      setSelectedCameraId(visibleCameras[0].id);
    }
  }, [showPtz, selectedCameraId, visibleCameras]);

  const toggleFullscreen = () => {
    if (!fullscreen) {
      containerRef.current?.requestFullscreen?.();
    } else {
      document.exitFullscreen?.();
    }
    setFullscreen(!fullscreen);
  };

  const swapCells = (from: number, to: number) => {
    setCellOrder(prev => {
      const next = [...prev];
      [next[from], next[to]] = [next[to], next[from]];
      return next;
    });
  };

  const handleDragStart = (idx: number) => setDraggedIdx(idx);
  const handleDragOver = (e: React.DragEvent, idx: number) => {
    e.preventDefault();
    if (draggedIdx !== null && draggedIdx !== idx) {
      swapCells(draggedIdx, idx);
      setDraggedIdx(idx);
    }
  };
  const handleDragEnd = () => setDraggedIdx(null);

  const handleSingleCameraSwitch = (direction: -1 | 1, event: MouseEvent<HTMLButtonElement>) => {
    event.stopPropagation();
    if (splitCount !== 1 || cameras.length <= 1) return;

    const nextIndex = (selectedCameraIndex + direction + cameras.length) % cameras.length;
    setSelectedCameraId(cameras[nextIndex].id);
  };

  const captureSnapshot = () => {
    alert(`抓图成功：${selectedCameraId ? cameras.find(c => c.id === selectedCameraId)?.name : '当前画面'}`);
  };

  const startLocalRecord = () => {
    alert('本地录像已开始，MP4 文件保存到下载目录');
  };

  const addToFavorites = () => {
    const cam = cameras.find(c => c.id === selectedCameraId);
    if (cam && !favorites.find(f => f.cameraId === cam.id)) {
      setFavorites([...favorites, { id: `f${Date.now()}`, name: cam.name, cameraId: cam.id }]);
    }
  };

  return (
    <div className="live-preview" ref={containerRef}>
      <header className="topbar">
        <div><h1>实时预览</h1><p>多窗口实时视频监控 · {cameras.length} 路</p></div>
        <div className="button-row">
          <select value={mainSub} onChange={e => setMainSub(e.target.value as 'main' | 'sub' | 'auto')} title="码流">
            <option value="main">主码流</option>
            <option value="sub">子码流</option>
            <option value="auto">自动切换</option>
          </select>
          <button className={showFavorites ? 'active-toggle' : ''} onClick={() => setShowFavorites(!showFavorites)}>
            <Bookmark size={16} />收藏夹
          </button>
          <button className={showHistory ? 'active-toggle' : ''} onClick={() => setShowHistory(!showHistory)}>
            <History size={16} />播放历史
          </button>
          <button onClick={load}><RefreshCw size={16} />刷新</button>
          <button onClick={showAll} disabled={cameras.length === 0}>
            <Layers size={16} />全部 ({cameras.length})
          </button>
        </div>
      </header>

      <div className="live-toolbar">
        <div className="toolbar-group">
          <span className="toolbar-label">分屏：</span>
          {[1, 4, 9, 16, 25].map(n => (
            <button key={n} className={splitCount === n ? 'active' : ''} onClick={() => setSplitCount(n)}>
              {n === 1 ? <Camera size={14} /> : n === 4 ? <Grid3X3 size={14} /> : n === 9 ? <Columns3 size={14} /> : n === 16 ? <Columns4 size={14} /> : <Layers size={14} />}
              <span>{n}</span>
            </button>
          ))}
          <span className="toolbar-sep" />
          <button className={showPtz ? 'active' : ''} onClick={() => setShowPtz(!showPtz)}>
            <Target size={14} />云台控制
          </button>
          <button className={showPatrol ? 'active' : ''} onClick={() => setShowPatrol(!showPatrol)}>
            <Repeat size={14} />轮巡计划
          </button>
          <button className={showParams ? 'active' : ''} onClick={() => setShowParams(!showParams)}>
            <Settings size={14} />视频参数
          </button>
          <button onClick={toggleFullscreen}><Maximize2 size={14} />全屏</button>
        </div>
        <div className="toolbar-group">
          <span className="toolbar-label">画面：</span>
          <button className={displayRatio === 'aspect' ? 'active' : ''} onClick={() => setDisplayRatio('aspect')}>原始比例</button>
          <button className={displayRatio === 'stretch' ? 'active' : ''} onClick={() => setDisplayRatio('stretch')}>满屏</button>
          <span className="toolbar-sep" />
          <button className={virtualPtz === 'on' ? 'active' : ''} onClick={() => setVirtualPtz(virtualPtz === 'on' ? 'off' : 'on')}>虚拟云台</button>
          <button className={electronicZoom === 'on' ? 'active' : ''} onClick={() => setElectronicZoom(electronicZoom === 'on' ? 'off' : 'on')}>电子放大</button>
          <button className={corridorMode === 'on' ? 'active' : ''} onClick={() => setCorridorMode(corridorMode === 'on' ? 'off' : 'on')}>走廊模式</button>
          <span className="toolbar-sep" />
          <button onClick={captureSnapshot} title="抓图"><ImageIcon size={14} />抓图</button>
          <button onClick={startLocalRecord} title="本地录像"><VideoIcon size={14} />录像</button>
          <button onClick={() => setShowInstantPlayback(true)} title="即时回放">即时回放</button>
          <button onClick={addToFavorites} title="收藏"><Bookmark size={14} />收藏</button>
        </div>
        <div className="toolbar-group">
          <span className="toolbar-label">自定义：</span>
          <select value={splitCount} onChange={e => setSplitCount(Number(e.target.value))}>
            {LAYOUTS.map(n => <option key={n} value={n}>{n} 画面</option>)}
          </select>
        </div>
      </div>

      <div className="live-content">
        <div className="live-main">
          <div
            className={`split-grid ${splitLayout} ${displayRatio === 'stretch' ? 'stretch-mode' : 'aspect-mode'} ${corridorMode === 'on' ? 'corridor-mode' : ''}`}
          >
            {cellOrder.map((cellIdx, displayIdx) => {
              const camera = visibleCameras[cellIdx];
              return (
                <div
                  key={`${cellIdx}-${displayIdx}`}
                  className={`split-cell ${camera?.id === selectedCameraId ? 'selected' : ''}`}
                  draggable
                  onDragStart={() => handleDragStart(displayIdx)}
                  onDragOver={(e) => handleDragOver(e, displayIdx)}
                  onDragEnd={handleDragEnd}
                  onClick={() => camera && setSelectedCameraId(camera.id)}
                >
                  {camera ? (
                    <>
                      <div className="split-label">
                        <span>{camera.name}</span>
                        <span className={`status-dot ${camera.status === 'RUNNING' ? 'running' : 'stopped'}`}>
                          {camera.status === 'RUNNING' ? '●' : '○'}
                        </span>
                        {virtualPtz === 'on' && <span className="hint-pill">虚拟云台</span>}
                        {electronicZoom === 'on' && <span className="hint-pill">电子放大</span>}
                        {camera.objectDetectionEnabled && <span className="hint-pill">DINO</span>}
                      </div>
                      <VideoPlayer key={`${camera.id}:${camera.playbackUrl}:${camera.objectDetectionEnabled ? 'dino' : 'raw'}`} url={cameraStreamUrl(camera)} />
                      {splitCount === 1 && cameras.length > 1 && (
                        <>
                          <button
                            type="button"
                            className="split-switch-arrow split-switch-prev"
                            title="上一个视频"
                            aria-label="上一个视频"
                            onClick={(event) => handleSingleCameraSwitch(-1, event)}
                          >
                            <ChevronLeft size={28} />
                          </button>
                          <button
                            type="button"
                            className="split-switch-arrow split-switch-next"
                            title="下一个视频"
                            aria-label="下一个视频"
                            onClick={(event) => handleSingleCameraSwitch(1, event)}
                          >
                            <ChevronRight size={28} />
                          </button>
                        </>
                      )}
                    </>
                  ) : (
                    <div className="split-empty">
                      <span>无摄像头</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {(showPtz || showFavorites || showHistory || showPatrol || showParams) && (
          <aside className="live-sidebar">
            {showPtz && <PtzPanel camera={selectedCamera} />}
            {showFavorites && <FavoritesPanel favorites={favorites} cameras={cameras} onSelect={setSelectedCameraId} />}
            {showHistory && <HistoryPanel history={history} onSelect={setSelectedCameraId} />}
            {showPatrol && <PatrolPanel plans={patrolPlans} setPlans={setPatrolPlans} editing={editingPatrol} setEditing={setEditingPatrol} cameras={cameras} />}
            {showParams && <VideoParamsPanel />}
          </aside>
        )}
      </div>

      {showInstantPlayback && (
        <div className="modal-overlay" onClick={() => setShowInstantPlayback(false)}>
          <div className="modal modal-wide" onClick={e => e.stopPropagation()}>
            <div className="modal-title">即时回放</div>
            <p className="hint">即时回放当前时间点的前 15 秒录像</p>
            <div className="instant-playback">
              <VideoPlayer
                key={`instant:${selectedCameraId}`}
                url={cameraStreamUrl(cameras.find(c => c.id === selectedCameraId))}
              />
              <div className="instant-timeline">
                <span>-15s</span>
                <div className="instant-track">
                  <div className="instant-fill instant-fill-60" />
                  <div className="instant-thumb instant-thumb-60" />
                </div>
                <span>现在</span>
              </div>
            </div>
            <div className="button-row modal-actions">
              <button>导出该片段</button>
              <button onClick={() => setShowInstantPlayback(false)}>关闭</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function PtzPanel({ camera }: { camera?: CameraType }) {
  const [step, setStep] = useState(5);
  const [busyCommand, setBusyCommand] = useState<PtzCommand | null>(null);
  const [lastAction, setLastAction] = useState('');
  const [error, setError] = useState('');
  const [currentUser] = useState('admin');
  const activePointerRef = useRef<number | null>(null);
  const pressStartedAtRef = useRef(0);
  const stopTimerRef = useRef<number | null>(null);
  const minMoveDurationMs = 900;

  const clearStopTimer = useCallback(() => {
    if (stopTimerRef.current !== null) {
      window.clearTimeout(stopTimerRef.current);
      stopTimerRef.current = null;
    }
  }, []);

  const sendPtz = useCallback(async (command: PtzCommand, preset?: number) => {
    if (!camera) return;
    setError('');
    setBusyCommand(command);
    try {
      const response = await api.ptzControl(camera.id, { command, step, preset });
      setLastAction(`${response.command} · 通道 ${response.channel}`);
    } catch (err) {
      setError(readableError(err));
    } finally {
      setBusyCommand(null);
    }
  }, [camera, step]);

  const scheduleStop = useCallback((pointerId?: number) => {
    if (pointerId !== undefined && activePointerRef.current !== pointerId) return;
    activePointerRef.current = null;
    const elapsed = Date.now() - pressStartedAtRef.current;
    const delay = Math.max(0, minMoveDurationMs - elapsed);
    clearStopTimer();
    stopTimerRef.current = window.setTimeout(() => {
      stopTimerRef.current = null;
      void sendPtz('stop');
    }, delay);
  }, [clearStopTimer, sendPtz]);

  useEffect(() => () => {
    const hadPendingStop = stopTimerRef.current !== null;
    clearStopTimer();
    if (camera && (activePointerRef.current !== null || hadPendingStop)) {
      void api.ptzControl(camera.id, { command: 'stop', step });
    }
    activePointerRef.current = null;
  }, [camera, clearStopTimer, step]);

  const handlePtzPointerDown = useCallback((event: React.PointerEvent<HTMLButtonElement>) => {
    const command = event.currentTarget.dataset.command as PtzCommand | undefined;
    if (!command) return;
    event.preventDefault();
    clearStopTimer();
    activePointerRef.current = event.pointerId;
    pressStartedAtRef.current = Date.now();
    event.currentTarget.setPointerCapture?.(event.pointerId);
    void sendPtz(command);
  }, [clearStopTimer, sendPtz]);

  const handlePtzPointerUp = useCallback((event: React.PointerEvent<HTMLButtonElement>) => {
    event.currentTarget.releasePointerCapture?.(event.pointerId);
    scheduleStop(event.pointerId);
  }, [scheduleStop]);

  const handlePtzPointerLeave = useCallback((event: React.PointerEvent<HTMLButtonElement>) => {
    if (activePointerRef.current !== null && event.buttons === 0) {
      scheduleStop();
    }
  }, [scheduleStop]);

  const handlePtzPointerCancel = useCallback((event: React.PointerEvent<HTMLButtonElement>) => {
    scheduleStop(event.pointerId);
  }, [scheduleStop]);

  const holdHandlers = {
    onPointerDown: handlePtzPointerDown,
    onPointerUp: handlePtzPointerUp,
    onPointerLeave: handlePtzPointerLeave,
    onPointerCancel: handlePtzPointerCancel,
  };

  const disabled = !camera;

  return (
    <div className="panel ptz-panel">
      <div className="panel-title">云台控制 {camera && <span className="hint-pill">{camera.name}</span>}</div>
      {!camera && <div className="ptz-message">请先在多分屏中选择一路摄像头</div>}
      <div className="ptz-direction-pad">
        <div className="ptz-row">
          <button className="ptz-btn" title="左上" disabled={disabled} data-command="up_left" {...holdHandlers}><ArrowUp size={16} className="icon-rotate-n45" /></button>
          <button className="ptz-btn" title="上" disabled={disabled} data-command="up" {...holdHandlers}><ArrowUp size={16} /></button>
          <button className="ptz-btn" title="右上" disabled={disabled} data-command="up_right" {...holdHandlers}><ArrowUp size={16} className="icon-rotate-45" /></button>
        </div>
        <div className="ptz-row">
          <button className="ptz-btn" title="左" disabled={disabled} data-command="left" {...holdHandlers}><ArrowLeft size={16} /></button>
          <button className="ptz-btn ptz-home" title="回中" disabled={disabled} onClick={() => void sendPtz('home')}><RotateCcw size={16} /></button>
          <button className="ptz-btn" title="右" disabled={disabled} data-command="right" {...holdHandlers}><ArrowRight size={16} /></button>
        </div>
        <div className="ptz-row">
          <button className="ptz-btn" title="左下" disabled={disabled} data-command="down_left" {...holdHandlers}><ArrowDown size={16} className="icon-rotate-45" /></button>
          <button className="ptz-btn" title="下" disabled={disabled} data-command="down" {...holdHandlers}><ArrowDown size={16} /></button>
          <button className="ptz-btn" title="右下" disabled={disabled} data-command="down_right" {...holdHandlers}><ArrowDown size={16} className="icon-rotate-n45" /></button>
        </div>
      </div>
      <div className="ptz-zoom-row">
        <button title="拉近" disabled={disabled} data-command="zoom_in" {...holdHandlers}><Plus size={16} /></button>
        <span>变倍</span>
        <button title="拉远" disabled={disabled} data-command="zoom_out" {...holdHandlers}><Minus size={16} /></button>
      </div>
      <div className="ptz-zoom-row">
        <button title="聚焦+：设备能力未接入" disabled><Plus size={16} /></button>
        <span>变焦</span>
        <button title="聚焦-：设备能力未接入" disabled><Minus size={16} /></button>
      </div>
      <div className="ptz-zoom-row">
        <button title="光圈+：设备能力未接入" disabled><Plus size={16} /></button>
        <span>光圈</span>
        <button title="光圈-：设备能力未接入" disabled><Minus size={16} /></button>
      </div>
      <hr />
      <div className="ptz-aux">
        <button disabled title="灯光控制：设备能力未接入">
          <Lightbulb size={14} />灯光
        </button>
        <button disabled title="雨刷控制：设备能力未接入">
          <Cloud size={14} />雨刷
        </button>
        <button disabled title="锁定控制：设备能力未接入">
          <Unlock size={14} />锁定
        </button>
      </div>
      <div className="ptz-presets">
        <div className="panel-title-small">预置点</div>
        <div className="preset-grid">
          {[1, 2, 3, 4, 5, 6].map(n => (
            <button key={n} className="preset-btn" disabled={disabled} onClick={() => void sendPtz('preset_goto', n)}>P{n}</button>
          ))}
        </div>
      </div>
      <div className="ptz-presets">
        <div className="panel-title-small">巡航轨迹</div>
        <div className="preset-grid">
          <button className="preset-btn" disabled title="巡航轨迹：设备能力未接入">轨迹 1</button>
          <button className="preset-btn" disabled title="巡航轨迹：设备能力未接入">轨迹 2</button>
        </div>
      </div>
      <div className="ptz-step">
        <label>步长：<select value={step} onChange={e => setStep(Number(e.target.value))}>
          <option value={1}>1</option>
          <option value={5}>5</option>
          <option value={10}>10</option>
        </select></label>
      </div>
      <div className="ptz-user">
        <User size={14} /> <span>当前操作：<strong>{currentUser}</strong>{busyCommand && ` · 发送 ${busyCommand}`}</span>
      </div>
      {lastAction && <div className="ptz-message success">最近命令：{lastAction}</div>}
      {error && <div className="ptz-message error">{error}</div>}
    </div>
  );
}

function readableError(error: unknown) {
  const text = error instanceof Error ? error.message : String(error);
  try {
    const parsed = JSON.parse(text) as { detail?: string };
    return parsed.detail || text;
  } catch {
    return text;
  }
}

function FavoritesPanel({ favorites, cameras, onSelect }: { favorites: { id: string; name: string; cameraId: string }[]; cameras: CameraType[]; onSelect: (id: string) => void }) {
  return (
    <div className="panel">
      <div className="panel-title">收藏夹</div>
      {favorites.length === 0 && <div className="empty">暂无收藏的监控点</div>}
      {favorites.map(f => (
        <div key={f.id} className="favorite-item" onClick={() => onSelect(f.cameraId)}>
          <Camera size={16} />
          <div>
            <strong>{f.name}</strong>
            <span>{cameras.find(c => c.id === f.cameraId)?.sourceUrl || '-'}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

function HistoryPanel({ history, onSelect }: { history: { id: string; name: string; time: string; cameraId: string }[]; onSelect: (id: string) => void }) {
  return (
    <div className="panel">
      <div className="panel-title">播放历史</div>
      {history.length === 0 && <div className="empty">暂无播放历史</div>}
      {history.map(h => (
        <div key={h.id} className="history-item" onClick={() => onSelect(h.cameraId)}>
          <History size={16} />
          <div>
            <strong>{h.name}</strong>
            <span>{h.time}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

type PatrolPlan = { id: string; name: string; windows: number; duration: number; cameras: string[] };

function PatrolPanel({ plans, setPlans, editing, setEditing, cameras }: {
  plans: PatrolPlan[]; setPlans: (p: PatrolPlan[]) => void; editing: PatrolPlan | null; setEditing: (p: PatrolPlan | null) => void; cameras: CameraType[];
}) {
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState('');
  const [windows, setWindows] = useState(4);
  const [duration, setDuration] = useState(30);
  const [selectedCameras, setSelectedCameras] = useState<string[]>([]);

  const openForm = (plan?: PatrolPlan) => {
    if (plan) { setEditing(plan); setName(plan.name); setWindows(plan.windows); setDuration(plan.duration); setSelectedCameras(plan.cameras); }
    else { setEditing(null); setName(''); setWindows(4); setDuration(30); setSelectedCameras([]); }
    setShowForm(true);
  };

  const save = () => {
    if (editing) {
      setPlans(plans.map(p => p.id === editing.id ? { ...p, name, windows, duration, cameras: selectedCameras } : p));
    } else {
      setPlans([...plans, { id: `p${Date.now()}`, name, windows, duration, cameras: selectedCameras }]);
    }
    setShowForm(false);
    setEditing(null);
  };

  return (
    <div className="panel">
      <div className="panel-title-row">
        <div className="panel-title">轮巡计划</div>
        <button onClick={() => openForm()} title="新增"><Save size={14} /></button>
      </div>
      {plans.length === 0 && <div className="empty">暂无轮巡计划</div>}
      {plans.map(p => (
        <div key={p.id} className="patrol-item">
          <Repeat size={16} />
          <div>
            <strong>{p.name}</strong>
            <span>{p.windows} 窗口 · 停留 {p.duration}s · {p.cameras.length} 监控点</span>
          </div>
          <div className="actions">
            <button onClick={() => openForm(p)}><Edit3 size={14} /></button>
            <button onClick={() => setPlans(plans.filter(x => x.id !== p.id))}><Trash2 size={14} /></button>
          </div>
        </div>
      ))}
      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-title">{editing ? '编辑' : '新建'}轮巡计划</div>
            <div className="device-form">
              <label><span>计划名称</span><input value={name} onChange={e => setName(e.target.value)} /></label>
              <label><span>轮巡窗口数</span>
                <select value={windows} onChange={e => setWindows(Number(e.target.value))}>
                  {[1, 2, 4, 6, 9, 16].map(n => <option key={n} value={n}>{n}</option>)}
                </select>
              </label>
              <label><span>停留时间(秒)</span><input type="number" value={duration} onChange={e => setDuration(Number(e.target.value))} /></label>
              <div>
                <span className="form-section-title">选择监控点</span>
                <div className="patrol-cameras">
                  {cameras.map(c => (
                    <label key={c.id} className="checkbox-label">
                      <input type="checkbox" checked={selectedCameras.includes(c.id)} onChange={e => {
                        setSelectedCameras(prev => e.target.checked ? [...prev, c.id] : prev.filter(id => id !== c.id));
                      }} />
                      {c.name}
                    </label>
                  ))}
                </div>
              </div>
            </div>
            <div className="button-row modal-actions">
              <button onClick={save}>保存</button>
              <button onClick={() => setShowForm(false)}>取消</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function VideoParamsPanel() {
  return (
    <div className="panel">
      <div className="panel-title">视频参数</div>
      <div className="params-tabs">
        <button className="active">基础配置</button>
        <button>视频配置</button>
        <button>回放配置</button>
        <button>抓图配置</button>
      </div>
      <div className="param-group">
        <label><span>视频编码</span>
          <select><option>H.264</option><option>H.265</option><option>Smart 264</option><option>Smart 265</option></select>
        </label>
        <label><span>分辨率</span>
          <select><option>4K (3840×2160)</option><option>1080P (1920×1080)</option><option>720P (1280×720)</option></select>
        </label>
        <label><span>帧率</span>
          <select><option>25 fps</option><option>30 fps</option><option>15 fps</option></select>
        </label>
        <label><span>码率</span>
          <select><option>4 Mbps</option><option>2 Mbps</option><option>1 Mbps</option><option>512 Kbps</option></select>
        </label>
        <label><span>音频</span>
          <select><option>开启</option><option>关闭</option></select>
        </label>
      </div>
    </div>
  );
}
