import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ChevronLeft, ChevronRight, Database, Pause, Pencil, Play, RefreshCw, Server, Trash2, Upload, UserRound, Video } from 'lucide-react';
import { API_BASE_URL, api, assetUrl, streamUrl } from './api';
import type { Camera, FaceEvent, FaceProfile, ModelInfo, WindowsCameraStatus } from './types';
import { VideoPlayer } from './VideoPlayer';

type Tab = 'monitor' | 'faces' | 'cameras' | 'models';

export function App() {
  const [tab, setTab] = useState<Tab>('monitor');
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [faces, setFaces] = useState<FaceProfile[]>([]);
  const [events, setEvents] = useState<FaceEvent[]>([]);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [selectedCameraId, setSelectedCameraId] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [backendOnline, setBackendOnline] = useState(true);
  const selectedCamera = useMemo(
    () => cameras.find((camera) => camera.id === selectedCameraId) ?? cameras[0],
    [cameras, selectedCameraId],
  );

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
      const hasSelectedCamera = cameraList.some((camera) => camera.id === selectedCameraId);
      if (cameraList.length > 0 && (!selectedCameraId || !hasSelectedCamera)) {
        setSelectedCameraId(cameraList[0].id);
      }
    } catch (err) {
      setBackendOnline(false);
      setError(messageOf(err));
    }
  }, [selectedCameraId]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  useEffect(() => {
    const source = new EventSource(`${API_BASE_URL}/api/events/stream`);
    source.addEventListener('face-event', (event) => {
      const item = JSON.parse((event as MessageEvent).data) as FaceEvent;
      setEvents((current) => [item, ...current].slice(0, 100));
    });
    source.onerror = () => undefined;
    return () => source.close();
  }, []);

  const refreshModels = async () => {
    setModels(await api.models());
  };

  return (
    <main className="app">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark"><Video size={20} /></div>
          <div>
            <strong>VideoAI</strong>
            <span>Monitoring MVP</span>
          </div>
        </div>
        <nav className="nav">
          <NavButton active={tab === 'monitor'} onClick={() => setTab('monitor')} icon={<Video size={17} />} label="监控" />
          <NavButton active={tab === 'faces'} onClick={() => setTab('faces')} icon={<UserRound size={17} />} label="人脸库" />
          <NavButton active={tab === 'cameras'} onClick={() => setTab('cameras')} icon={<Database size={17} />} label="摄像头" />
          <NavButton active={tab === 'models'} onClick={() => setTab('models')} icon={<Server size={17} />} label="模型" />
        </nav>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <h1>{tabTitle(tab)}</h1>
            <p>{statusLine(cameras, faces, events, models)}</p>
          </div>
          <button className="icon-text" onClick={loadAll}><RefreshCw size={16} />刷新</button>
        </header>
        {!backendOnline && <div className="notice">后端服务未连接。摄像头管理、人脸库和识别事件需要启动后端。</div>}
        {error && <div className="alert">{error}</div>}
        {tab === 'monitor' && (
          <MonitorView
            cameras={cameras}
            selectedCamera={selectedCamera}
            selectedCameraId={selectedCameraId}
            setSelectedCameraId={setSelectedCameraId}
            events={events}
          />
        )}
        {tab === 'faces' && <FacesView faces={faces} reload={loadAll} />}
        {tab === 'cameras' && <CamerasView cameras={cameras} reload={loadAll} />}
        {tab === 'models' && <ModelsView models={models} reload={refreshModels} />}
      </section>
    </main>
  );
}

function MonitorView({
  cameras,
  selectedCamera,
  selectedCameraId,
  setSelectedCameraId,
  events,
}: {
  cameras: Camera[];
  selectedCamera?: Camera;
  selectedCameraId: string;
  setSelectedCameraId: (id: string) => void;
  events: FaceEvent[];
}) {
  const PAGE_SIZE = 4;
  const [monitorPage, setMonitorPage] = useState(0);
  const totalPages = Math.max(1, Math.ceil(cameras.length / PAGE_SIZE));
  const safePage = Math.min(Math.max(0, monitorPage), totalPages - 1);
  if (safePage !== monitorPage) {
    setMonitorPage(safePage);
  }
  const pageCameras = cameras.slice(safePage * PAGE_SIZE, (safePage + 1) * PAGE_SIZE);
  const autoStartedPage = useRef(-1);

  useEffect(() => {
    if (autoStartedPage.current === safePage) {
      return;
    }
    autoStartedPage.current = safePage;
    const visible = cameras.slice(safePage * PAGE_SIZE, (safePage + 1) * PAGE_SIZE);
    for (const camera of visible) {
      api.startCamera(camera.id).catch(() => {});
    }
  }, [safePage, cameras]);

  return (
    <div className="monitor-grid">
      <section className="multi-video-grid">
        {cameras.length === 0 && <div className="notice">暂无摄像头，请先在「摄像头」页面添加。</div>}
        {pageCameras.map((camera) => (
          <div key={camera.id} className="video-panel-item">
            <div className="section-head">
              <strong>{camera.name}</strong>
              <span className="status-dot" style={{ color: camera.status === 'RUNNING' ? '#22c55e' : '#888' }}>
                {camera.status === 'RUNNING' ? '● 运行中' : '○ 已停止'}
              </span>
            </div>
            <VideoPlayer url={streamUrl(camera.playbackUrl)} />
          </div>
        ))}
      </section>
      {cameras.length > PAGE_SIZE && (
        <div className="pagination-bar">
          <button onClick={() => setMonitorPage((p) => Math.max(0, p - 1))} disabled={safePage === 0}>
            <ChevronLeft size={16} />上一页
          </button>
          <span className="page-indicator">
            {safePage + 1} / {totalPages}
          </span>
          <button onClick={() => setMonitorPage((p) => Math.min(totalPages - 1, p + 1))} disabled={safePage >= totalPages - 1}>
            下一页<ChevronRight size={16} />
          </button>
        </div>
      )}
      <EventList events={events} />
    </div>
  );
}

function EventList({ events }: { events: FaceEvent[] }) {
  return (
    <section className="panel">
      <div className="panel-title">实时匹配</div>
      <div className="event-list">
        {events.map((event) => (
          <article className="event-item" key={event.id}>
            <img src={assetUrl(event.facePhotoUrl)} alt={event.profileName} />
            <div>
              <strong>{event.profileName}</strong>
              <span>{event.cameraName} · {new Date(event.videoTime).toLocaleString()}</span>
              <p>{event.profileDescription || '无描述'}</p>
            </div>
            <b>{Math.round(event.similarity * 100)}%</b>
          </article>
        ))}
        {events.length === 0 && <Empty text="暂无匹配事件" />}
      </div>
    </section>
  );
}

function FacesView({ faces, reload }: { faces: FaceProfile[]; reload: () => Promise<void> }) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [photo, setPhoto] = useState<File | null>(null);
  const [editing, setEditing] = useState<FaceProfile | null>(null);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState('');

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!editing && !photo) {
      setFormError('请选择一张人脸照片');
      return;
    }
    try {
      setSaving(true);
      setFormError('');
      const form = new FormData();
      form.append('name', name);
      form.append('description', description);
      if (photo) form.append('photo', photo);
      if (editing) {
        await api.updateFace(editing.id, form);
      } else {
        await api.createFace(form);
      }
      reset();
      await reload();
    } catch (err) {
      setFormError(messageOf(err));
    } finally {
      setSaving(false);
    }
  };

  const editFace = (face: FaceProfile) => {
    setEditing(face);
    setName(face.name);
    setDescription(face.description || '');
    setPhoto(null);
  };

  const reset = () => {
    setEditing(null);
    setName('');
    setDescription('');
    setPhoto(null);
    setFormError('');
  };

  return (
    <div className="two-column">
      <form className="panel form" onSubmit={submit}>
        <div className="panel-title">{editing ? '编辑人脸' : '新增人脸'}</div>
        <input value={name} onChange={(event) => setName(event.target.value)} placeholder="姓名" required />
        <textarea value={description} onChange={(event) => setDescription(event.target.value)} placeholder="描述" />
        <label className="file-box">
          <Upload size={17} />
          <span>{photo ? photo.name : editing ? '不更换照片' : '选择照片'}</span>
          <input type="file" accept="image/*" onChange={(event) => setPhoto(event.target.files?.[0] ?? null)} />
        </label>
        {formError && <div className="inline-error">{formError}</div>}
        <div className="button-row">
          <button type="submit" disabled={saving}>{saving ? '保存中' : '保存'}</button>
          {editing && <button type="button" onClick={reset} disabled={saving}>取消</button>}
        </div>
      </form>
      <section className="face-grid">
        {faces.map((face) => (
          <article className="face-card" key={face.id}>
            <img src={assetUrl(face.photoUrl)} alt={face.name} />
            <div>
              <strong>{face.name}</strong>
              <span>{face.description || '无描述'}</span>
            </div>
            <div className="stack-actions">
              <button title="编辑" onClick={() => editFace(face)}><Pencil size={16} /></button>
              <button title="删除" onClick={async () => { await api.deleteFace(face.id); await reload(); }}><Trash2 size={16} /></button>
            </div>
          </article>
        ))}
        {faces.length === 0 && <Empty text="暂无人脸数据" />}
      </section>
    </div>
  );
}

function CamerasView({ cameras, reload }: { cameras: Camera[]; reload: () => Promise<void> }) {
  const [name, setName] = useState('本机摄像头');
  const [sourceUrl, setSourceUrl] = useState('/dev/video0');
  const [description, setDescription] = useState('');
  const [nvrId, setNvrId] = useState('');
  const [nvrChannel, setNvrChannel] = useState('');
  const [nvrTrackId, setNvrTrackId] = useState('');
  const [nvrStreamType, setNvrStreamType] = useState('');
  const [editing, setEditing] = useState<Camera | null>(null);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const payload = { name, sourceUrl, description, nvrId, nvrChannel, nvrTrackId, nvrStreamType };
    if (editing) {
      await api.updateCamera(editing.id, payload);
    } else {
      await api.createCamera(payload);
    }
    reset();
    await reload();
  };

  const editCamera = (camera: Camera) => {
    setEditing(camera);
    setName(camera.name);
    setSourceUrl(camera.sourceUrl);
    setDescription(camera.description || '');
    setNvrId(camera.nvrId || '');
    setNvrChannel(camera.nvrChannel || '');
    setNvrTrackId(camera.nvrTrackId || '');
    setNvrStreamType(camera.nvrStreamType || '');
  };

  const reset = () => {
    setEditing(null);
    setName('本机摄像头');
    setSourceUrl('/dev/video0');
    setDescription('');
    setNvrId('');
    setNvrChannel('');
    setNvrTrackId('');
    setNvrStreamType('');
  };

  return (
    <div className="two-column">
      <form className="panel form" onSubmit={submit}>
        <div className="panel-title">{editing ? '编辑摄像头' : '新增摄像头'}</div>
        <input value={name} onChange={(event) => setName(event.target.value)} placeholder="名称" required />
        <input value={sourceUrl} onChange={(event) => setSourceUrl(event.target.value)} placeholder="/dev/video0 或 rtsp://..." required />
        <textarea value={description} onChange={(event) => setDescription(event.target.value)} placeholder="描述" />
        <input value={nvrId} onChange={(event) => setNvrId(event.target.value)} placeholder="NVR 标识（可选）" />
        <input value={nvrChannel} onChange={(event) => setNvrChannel(event.target.value)} placeholder="NVR 通道（可选，例如 1）" />
        <input value={nvrTrackId} onChange={(event) => setNvrTrackId(event.target.value)} placeholder="海康 trackID（可选，例如 101）" />
        <input value={nvrStreamType} onChange={(event) => setNvrStreamType(event.target.value)} placeholder="码流类型（可选，例如 main/sub）" />
        <div className="button-row">
          <button type="submit">保存</button>
          {editing && <button type="button" onClick={reset}>取消</button>}
        </div>
      </form>
      <section className="panel table-panel">
        <div className="panel-title">摄像头列表</div>
        <table>
          <thead><tr><th>名称</th><th>源</th><th>NVR</th><th>状态</th><th>操作</th></tr></thead>
          <tbody>
            {cameras.map((camera) => (
              <tr key={camera.id}>
                <td>{camera.name}</td>
                <td>{camera.sourceUrl}</td>
                <td>{camera.nvrTrackId || camera.nvrChannel || '-'}</td>
                <td><Status value={camera.status} /></td>
                <td className="actions">
                  <button title="编辑" onClick={() => editCamera(camera)}><Pencil size={15} /></button>
                  <button onClick={async () => { await api.startCamera(camera.id); await reload(); }}><Play size={15} /></button>
                  <button onClick={async () => { await api.stopCamera(camera.id); await reload(); }}><Pause size={15} /></button>
                  <button onClick={async () => { await api.deleteCamera(camera.id); await reload(); }}><Trash2 size={15} /></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

function ModelsView({ models, reload }: { models: ModelInfo[]; reload: () => Promise<void> }) {
  const [name, setName] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [modelType, setModelType] = useState('FACE_RECOGNITION');
  const [description, setDescription] = useState('');
  const [configText, setConfigText] = useState('');

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    await api.registerModel({ name, displayName, repositoryPath: `/models/${name}`, modelType, description });
    setName('');
    setDisplayName('');
    setDescription('');
    await reload();
  };

  return (
    <div className="two-column">
      <form className="panel form" onSubmit={submit}>
        <div className="panel-title">注册模型目录</div>
        <input value={name} onChange={(event) => setName(event.target.value)} placeholder="Triton 模型名" required />
        <input value={displayName} onChange={(event) => setDisplayName(event.target.value)} placeholder="显示名称" required />
        <select value={modelType} onChange={(event) => setModelType(event.target.value)}>
          <option value="FACE_DETECTION">人脸检测</option>
          <option value="FACE_RECOGNITION">人脸识别</option>
          <option value="LICENSE_PLATE">车牌识别</option>
          <option value="OTHER">其他</option>
        </select>
        <textarea value={description} onChange={(event) => setDescription(event.target.value)} placeholder="描述" />
        <button type="submit">注册</button>
      </form>
      <section className="panel table-panel">
        <div className="panel-title">Triton 模型服务</div>
        <table>
          <thead><tr><th>模型</th><th>类型</th><th>状态</th><th>操作</th></tr></thead>
          <tbody>
            {models.map((model) => (
              <tr key={model.id}>
                <td>{model.displayName}<small>{model.name}</small></td>
                <td>{model.modelType}</td>
                <td><Status value={model.state} /></td>
                <td className="actions">
                  <button onClick={async () => { await api.loadModel(model.name); await reload(); }}>加载</button>
                  <button onClick={async () => { await api.unloadModel(model.name); await reload(); }}>卸载</button>
                  <button onClick={async () => setConfigText(JSON.stringify((await api.modelConfig(model.name)).config, null, 2))}>配置</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {configText && <pre className="config-box">{configText}</pre>}
      </section>
    </div>
  );
}

function NavButton({ active, onClick, icon, label }: { active: boolean; onClick: () => void; icon: React.ReactNode; label: string }) {
  return <button className={active ? 'active' : ''} onClick={onClick}>{icon}<span>{label}</span></button>;
}

function Status({ value }: { value: string }) {
  return <span className={`status ${value.toLowerCase()}`}>{value}</span>;
}

function Empty({ text }: { text: string }) {
  return <div className="empty">{text}</div>;
}

function tabTitle(tab: Tab) {
  return {
    monitor: '视频监控',
    faces: '人脸库',
    cameras: '摄像头管理',
    models: '模型管理',
  }[tab];
}

function statusLine(cameras: Camera[], faces: FaceProfile[], events: FaceEvent[], models: ModelInfo[]) {
  return `${cameras.length} 路摄像头 · ${faces.length} 个人脸 · ${events.length} 条事件 · ${models.length} 个模型`;
}

function messageOf(error: unknown) {
  return error instanceof Error ? error.message : String(error);
}
