import { useCallback, useEffect, useRef, useState } from 'react';
import { RefreshCw, ChevronLeft, ChevronRight, Video, UserRound, Camera, Bell } from 'lucide-react';
import { api, API_BASE_URL, cameraStreamUrl } from '../api';
import type { Camera as CameraType, FaceEvent, FaceProfile, ModelInfo } from '../types';
import { VideoPlayer } from '../VideoPlayer';

export function Dashboard() {
  const [cameras, setCameras] = useState<CameraType[]>([]);
  const [faces, setFaces] = useState<FaceProfile[]>([]);
  const [events, setEvents] = useState<FaceEvent[]>([]);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [selectedCameraId, setSelectedCameraId] = useState<string>('');
  const [error, setError] = useState('');
  const [backendOnline, setBackendOnline] = useState(true);

  const loadAll = useCallback(async () => {
    try {
      setError('');
      setBackendOnline(true);
      const [cameraList, faceList, eventList, modelList] = await Promise.all([
        api.cameras(),
        api.faces(),
        api.events(),
        api.models().catch(() => [] as ModelInfo[]),
      ]);
      setCameras(cameraList);
      setFaces(faceList);
      setEvents(eventList);
      setModels(modelList);
      const hasSelected = cameraList.some(c => c.id === selectedCameraId);
      if (cameraList.length > 0 && (!selectedCameraId || !hasSelected)) {
        setSelectedCameraId(cameraList[0].id);
      }
    } catch (err) {
      setBackendOnline(false);
      setError(messageOf(err));
    }
  }, [selectedCameraId]);

  useEffect(() => { loadAll(); }, [loadAll]);

  useEffect(() => {
    const source = new EventSource(`${API_BASE_URL}/api/events/stream`);
    source.addEventListener('face-event', (event) => {
      const item = JSON.parse((event as MessageEvent).data) as FaceEvent;
      setEvents(current => [item, ...current].slice(0, 100));
    });
    source.onerror = () => undefined;
    return () => source.close();
  }, []);

  return (
    <>
      <header className="topbar">
        <div>
          <h1>总览</h1>
          <p>{cameras.length} 路摄像头 · {faces.length} 个人脸 · {events.length} 条事件 · {models.length} 个模型</p>
        </div>
        <button className="icon-text" onClick={loadAll}><RefreshCw size={16} />刷新</button>
      </header>
      {!backendOnline && <div className="notice">后端服务未连接。部分功能需要启动后端服务。</div>}
      {error && <div className="alert">{error}</div>}

      <div className="stat-cards">
        <div className="stat-card"><Camera size={22} /><div><strong>{cameras.length}</strong><span>摄像头</span></div></div>
        <div className="stat-card"><Video size={22} /><div><strong>{cameras.filter(c => c.status === 'RUNNING').length}</strong><span>在线</span></div></div>
        <div className="stat-card"><UserRound size={22} /><div><strong>{faces.length}</strong><span>人脸库</span></div></div>
        <div className="stat-card"><Bell size={22} /><div><strong>{events.length}</strong><span>告警事件</span></div></div>
      </div>

      <MonitorSection cameras={cameras} />
    </>
  );
}

function MonitorSection({
  cameras,
}: {
  cameras: CameraType[];
}) {
  const PAGE_SIZE = 4;
  const [monitorPage, setMonitorPage] = useState(0);
  const totalPages = Math.max(1, Math.ceil(cameras.length / PAGE_SIZE));
  const safePage = Math.min(Math.max(0, monitorPage), totalPages - 1);
  if (safePage !== monitorPage) setMonitorPage(safePage);
  const pageCameras = cameras.slice(safePage * PAGE_SIZE, (safePage + 1) * PAGE_SIZE);
  const autoStartedPage = useRef(-1);

  useEffect(() => {
    if (autoStartedPage.current === safePage) return;
    autoStartedPage.current = safePage;
    for (const camera of cameras.slice(safePage * PAGE_SIZE, (safePage + 1) * PAGE_SIZE)) {
      api.startCamera(camera.id).catch(() => {});
    }
  }, [safePage, cameras]);

  return (
    <div className="monitor-grid">
      <section className="multi-video-grid">
        {cameras.length === 0 && <div className="notice">暂无摄像头，请先在「设备管理」页面添加。</div>}
        {pageCameras.map(camera => (
          <div key={camera.id} className="video-panel-item">
            <div className="section-head">
              <strong>{camera.name}</strong>
              <span className={`status-dot ${camera.status === 'RUNNING' ? 'running' : 'stopped'}`}>
                {camera.status === 'RUNNING' ? '● 运行中' : '○ 已停止'}
              </span>
              {camera.objectDetectionEnabled && <span className="hint-pill">DINO</span>}
            </div>
            <VideoPlayer url={cameraStreamUrl(camera)} />
          </div>
        ))}
      </section>
      {cameras.length > PAGE_SIZE && (
        <div className="pagination-bar">
          <button onClick={() => setMonitorPage(p => Math.max(0, p - 1))} disabled={safePage === 0}>
            <ChevronLeft size={16} />上一页
          </button>
          <span className="page-indicator">{safePage + 1} / {totalPages}</span>
          <button onClick={() => setMonitorPage(p => Math.min(totalPages - 1, p + 1))} disabled={safePage >= totalPages - 1}>
            下一页<ChevronRight size={16} />
          </button>
        </div>
      )}
    </div>
  );
}

function messageOf(error: unknown) {
  return error instanceof Error ? error.message : String(error);
}
