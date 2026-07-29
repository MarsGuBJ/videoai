import { useCallback, useEffect, useMemo, useState, useRef, Fragment } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Plus, Search, Upload, X, LogIn, Star, ToggleLeft, ToggleRight,
  ChevronLeft, ChevronRight, Copy, ArrowLeft, Car, Box, UserRound, Mic, GitBranch, BellRing,
} from 'lucide-react';
import { api, assetUrl } from '../../api';
import type { Camera, DeploymentTask, DeploymentTaskCreate, FaceMatchEvent, FaceProfile, ModelGpuConfig, ModelInfo } from '../../types';

type AlgoType = '目标检测' | '图像识别' | '语义分割' | '行为分析';

type Algorithm = {
  id: string;
  name: string;
  version: string;
  type: AlgoType;
  updatedAt: string;
  desc: string;
};

type VersionFile = { name: string };

type AlgorithmVersion = {
  id: string;
  version: string;
  desc: string;
  updatedAt: string;
  files: VersionFile[];
  configFile: string;
};

type AlgorithmCreateData = {
  algorithm: Algorithm;
  initialVersion: Omit<AlgorithmVersion, 'id'>;
};

const ALGO_TYPES: AlgoType[] = ['目标检测', '图像识别', '语义分割', '行为分析'];
const ALGORITHMS_STORAGE_KEY = 'videoai.algorithmDeploy.algorithms.v1';
const ALGORITHM_VERSIONS_STORAGE_KEY = 'videoai.algorithmDeploy.versions.v1';
const FACE_MODEL_KEYWORDS = ['face', 'arcface', 'retinaface', 'scrfd'];

const SAMPLE_CONFIG_JSON = `{
  "name": "claude-code-local",
  "version": "0.0.46",
  "mode": "bypassPermissions",
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash|Read|Write|Edit",
        "hooks": [
          { "type": "command", "command": "echo $TOOL_INPUT" }
        ]
      }
    ]
  },
  "permissions": {
    "allow": ["Bash", "Read", "Edit", "Write"],
    "deny": ["WebFetch", "WebSearch"]
  },
  "env": {
    "ANTHROPIC_API_KEY": "sk-ant-xxxxxx",
    "MODEL": "claude-3-5-sonnet"
  },
  "maxTokens": 8192,
  "temperature": 1.0,
  "topP": 0.95,
  "topK": 40
}`;

const INITIAL_ALGORITHMS: Algorithm[] = [
  { id: '1', name: '人员检测', version: 'v1.0', type: '目标检测', updatedAt: '2026-04-22', desc: '用于检测特定人员的算法' },
  { id: '2', name: '车辆检测', version: 'v1.2', type: '目标检测', updatedAt: '2026-04-15', desc: '识别监控区域内的机动车与非机动车' },
  { id: '3', name: '人脸识别', version: 'v2.0', type: '图像识别', updatedAt: '2026-04-10', desc: '提取人脸特征进行身份比对与确认' },
  { id: '4', name: '车牌识别', version: 'v1.1', type: '图像识别', updatedAt: '2026-04-18', desc: '自动识别车辆车牌号码及颜色' },
  { id: '5', name: '周界入侵', version: 'v1.0', type: '目标检测', updatedAt: '2026-04-05', desc: '监测并报警非法跨越警戒区域的行为' },
];

const INITIAL_VERSIONS: Record<string, AlgorithmVersion[]> = {
  '1': [
    {
      id: 'v1', version: 'v2.2', desc: '这是版本说明', updatedAt: '2026-04-25',
      files: [
        { name: 'Yolov8m_person_310B.om' },
        { name: 'libilogic_process.so' },
        { name: 'hrmet_310B.om' },
        { name: 'libalgo_yolov8_climbing.so' },
        { name: 'default_config.yaml' },
        { name: 'infer_cfg.yml' },
      ],
      configFile: 'algo_config.json',
    },
    { id: 'v2', version: 'v2.1', desc: '这是版本说明', updatedAt: '2026-04-25', files: [{ name: 'Yolov8m_person_310B.om' }], configFile: 'algo_config.json' },
    { id: 'v3', version: 'v2.0', desc: '这是版本说明', updatedAt: '2026-04-25', files: [{ name: 'Yolov8m_person_310B.om' }], configFile: 'algo_config.json' },
    { id: 'v4', version: 'v1.9', desc: '这是版本说明', updatedAt: '2026-04-25', files: [{ name: 'Yolov8m_person_310B.om' }], configFile: 'algo_config.json' },
    { id: 'v5', version: 'v1.8', desc: '这是版本说明', updatedAt: '2026-04-20', files: [{ name: 'Yolov8m_person_310B.om' }], configFile: 'algo_config.json' },
  ],
};

function readStorageJson<T>(key: string, fallback: T): T {
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) return fallback;
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

function writeStorageJson<T>(key: string, value: T) {
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Local persistence is best-effort in private/incognito contexts.
  }
}

function loadStoredAlgorithms() {
  return readStorageJson<Algorithm[]>(ALGORITHMS_STORAGE_KEY, INITIAL_ALGORITHMS);
}

function saveStoredAlgorithms(algorithms: Algorithm[]) {
  writeStorageJson(ALGORITHMS_STORAGE_KEY, algorithms);
}

function loadStoredAlgorithmVersions() {
  return readStorageJson<Record<string, AlgorithmVersion[]>>(ALGORITHM_VERSIONS_STORAGE_KEY, INITIAL_VERSIONS);
}

function saveStoredAlgorithmVersions(versions: Record<string, AlgorithmVersion[]>) {
  writeStorageJson(ALGORITHM_VERSIONS_STORAGE_KEY, versions);
}

function todayText() {
  return new Date().toISOString().slice(0, 10);
}

function messageOf(error: unknown) {
  return error instanceof Error ? error.message : String(error);
}

function isFaceModel(name: string) {
  const normalized = name.toLowerCase();
  return FACE_MODEL_KEYWORDS.some(keyword => normalized.includes(keyword));
}

type AlgoSubTab = 'algorithms' | 'orchestration' | 'tasks';

function SubTabs({ active, mode }: { active: AlgoSubTab; mode?: 'versions' }) {
  if (mode === 'versions') return null;
  return (
    <div className="alarm-sub-tabs">
      <a href="/algo-deploy/algorithms" className={active === 'algorithms' ? 'active' : ''}>算法管理</a>
      <a href="/algo-deploy/orchestration" className={active === 'orchestration' ? 'active' : ''}>算法编排</a>
      <a href="/algo-deploy/tasks" className={active === 'tasks' ? 'active' : ''}>布控任务</a>
    </div>
  );
}

function Pagination({
  page, totalPages, pageSize, onPageChange, onPageSizeChange,
}: {
  page: number;
  totalPages: number;
  pageSize: number;
  onPageChange: (p: number) => void;
  onPageSizeChange: (n: number) => void;
}) {
  const pages = useMemo(() => {
    const set = new Set<number>([1, totalPages, page, page - 1, page + 1]);
    return Array.from(set).filter(p => p >= 1 && p <= totalPages).sort((a, b) => a - b);
  }, [page, totalPages]);

  return (
    <div className="pagination-bar">
      <button onClick={() => onPageChange(Math.max(1, page - 1))} disabled={page === 1}>
        <ChevronLeft size={14} />上一页
      </button>
      {pages.map((p, idx) => {
        const prev = pages[idx - 1];
        const gap = prev !== undefined && p - prev > 1;
        return (
          <Fragment key={p}>
            {gap && <span className="page-indicator">...</span>}
            <button
              onClick={() => onPageChange(p)}
              className={p === page ? 'active-toggle' : ''}
            >{p}</button>
          </Fragment>
        );
      })}
      <button onClick={() => onPageChange(Math.min(totalPages, page + 1))} disabled={page === totalPages}>
        下一页<ChevronRight size={14} />
      </button>
      <select
        value={pageSize}
        onChange={e => onPageSizeChange(Number(e.target.value))}
        className="pagination-size-select"
      >
        <option value={5}>5条/页</option>
        <option value={10}>10条/页</option>
        <option value={20}>20条/页</option>
        <option value={50}>50条/页</option>
      </select>
      <span className="pagination-text">跳至</span>
      <input
        type="number"
        min={1}
        max={totalPages}
        defaultValue={page}
        className="pagination-jump-input"
        onKeyDown={e => {
          if (e.key === 'Enter') {
            const v = Number((e.target as HTMLInputElement).value);
            if (v >= 1 && v <= totalPages) onPageChange(v);
          }
        }}
      />
      <span className="pagination-text">页</span>
    </div>
  );
}

function FileDropzone({
  fileName, onSelect, label = '点击上传算法包', accept,
}: {
  fileName?: string;
  onSelect: (name: string) => void;
  label?: string;
  accept?: string;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  return (
    <label className={`file-dropzone ${fileName ? 'has-file' : ''}`}>
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        onChange={e => {
          const f = e.target.files?.[0];
          if (f) onSelect(f.name);
        }}
      />
      <Upload size={28} />
      <span>{fileName || label}</span>
    </label>
  );
}

function SlideDrawer({
  title, onClose, children, footer,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
  footer?: React.ReactNode;
}) {
  return (
    <div className="slide-drawer-overlay" onClick={onClose}>
      <div className="slide-drawer" onClick={e => e.stopPropagation()}>
        <div className="slide-drawer-header">
          <div className="slide-drawer-title">{title}</div>
          <button className="icon-btn" onClick={onClose} title="关闭">
            <LogIn size={18} className="icon-rotate-180" />
          </button>
        </div>
        <div className="slide-drawer-body">{children}</div>
        {footer && <div className="slide-drawer-footer">{footer}</div>}
      </div>
    </div>
  );
}

function AlgorithmCreateDrawer({
  onClose, onSave,
}: {
  onClose: () => void;
  onSave: (data: AlgorithmCreateData) => void;
}) {
  const [name, setName] = useState('');
  const [pkg, setPkg] = useState('');
  const [type, setType] = useState<AlgoType>('目标检测');
  const [initialVersion, setInitialVersion] = useState('v1.0');
  const [versionDesc, setVersionDesc] = useState('');
  const [desc, setDesc] = useState('');

  const handleSave = () => {
    if (!name.trim()) { alert('请填写算法名称'); return; }
    const id = String(Date.now());
    const version = initialVersion.trim() || 'v1.0';
    const updatedAt = todayText();
    onSave({
      algorithm: {
        id,
        name: name.trim(),
        version,
        type,
        updatedAt,
        desc: desc.trim(),
      },
      initialVersion: {
        version,
        desc: versionDesc.trim() || '这是版本说明',
        updatedAt,
        files: pkg ? [{ name: pkg }] : [],
        configFile: 'algo_config.json',
      },
    });
  };

  return (
    <SlideDrawer
      title="新增算法"
      onClose={onClose}
      footer={
        <>
          <button onClick={onClose}>取消</button>
          <button onClick={handleSave} className="omni-primary-btn">保存</button>
        </>
      }
    >
      <label className="form-label"><span><span className="required-mark">*</span>算法名称</span><input value={name} onChange={e => setName(e.target.value)} placeholder="请输入算法名称" /></label>
      <div className="form-section">
        <div className="form-section-title">算法包</div>
        <FileDropzone fileName={pkg} onSelect={setPkg} />
      </div>
      <label className="form-label"><span>算法类型</span>
        <select value={type} onChange={e => setType(e.target.value as AlgoType)}>
          {ALGO_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
      </label>
      <label className="form-label"><span>初始版本</span><input value={initialVersion} onChange={e => setInitialVersion(e.target.value)} placeholder="v1.0" /></label>
      <label className="form-label"><span>版本说明</span><textarea value={versionDesc} onChange={e => setVersionDesc(e.target.value)} placeholder="请输入版本说明" /></label>
      <label className="form-label"><span>算法描述</span><textarea value={desc} onChange={e => setDesc(e.target.value)} placeholder="请输入算法描述" /></label>
    </SlideDrawer>
  );
}

function VersionCreateModal({
  onClose, onSave,
}: {
  onClose: () => void;
  onSave: (v: Omit<AlgorithmVersion, 'id'>) => void;
}) {
  const [version, setVersion] = useState('');
  const [pkg, setPkg] = useState('');
  const [desc, setDesc] = useState('');

  const handleSave = () => {
    if (!version.trim()) { alert('请填写版本号'); return; }
    onSave({
      version: version.trim(),
      desc: desc.trim() || '这是版本说明',
      updatedAt: todayText(),
      files: pkg ? [{ name: pkg }] : [],
      configFile: 'algo_config.json',
    });
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal modal-wide" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title">新增版本</div>
          <button className="icon-btn" onClick={onClose}><X size={18} /></button>
        </div>
        <div className="device-form">
          <label className="form-label"><span>版本号</span><input value={version} onChange={e => setVersion(e.target.value)} placeholder="例如 v2.3" /></label>
          <div>
            <div className="form-section-title">算法包</div>
            <FileDropzone fileName={pkg} onSelect={setPkg} />
          </div>
          <label className="form-label"><span>版本说明</span><textarea value={desc} onChange={e => setDesc(e.target.value)} placeholder="请输入版本说明" /></label>
        </div>
        <div className="button-row modal-actions">
          <button onClick={onClose}>取消</button>
          <button onClick={handleSave} className="omni-primary-btn">保存</button>
        </div>
      </div>
    </div>
  );
}

function FilePreviewModal({
  fileName, onClose,
}: {
  fileName: string;
  onClose: () => void;
}) {
  const handleCopy = () => {
    navigator.clipboard?.writeText(SAMPLE_CONFIG_JSON).catch(() => {});
    alert('已拷贝到剪贴板');
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal modal-x-wide" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title">文件详情预览</div>
          <div className="button-row">
            <button onClick={handleCopy} className="omni-primary-btn">
              <Copy size={14} />拷贝
            </button>
            <button onClick={onClose}>关闭</button>
          </div>
        </div>
        <pre className="config-box config-box-preview">{SAMPLE_CONFIG_JSON}</pre>
        <div className="file-preview-name">{fileName}</div>
      </div>
    </div>
  );
}

function VersionDetailDrawer({
  version, onClose, onPreviewFile,
}: {
  version: AlgorithmVersion;
  onClose: () => void;
  onPreviewFile: (name: string) => void;
}) {
  return (
    <SlideDrawer title="版本详情" onClose={onClose}>
      <div className="form-section">
        <div className="detail-row"><span className="detail-label">版本号</span><span className="detail-value">{version.version}</span></div>
        <div className="detail-row full-width"><span className="detail-label">版本描述</span><span className="detail-value">{version.desc}，包含...等</span></div>
      </div>
      <div>
        <div className="form-section-title">算法文件</div>
        <div className="file-list">
          {version.files.map(f => (
            <div key={f.name} className="file-list-item">
              <span>📄 {f.name}</span>
              <button className="icon-link" onClick={() => onPreviewFile(f.name)} title="查看内容">
                <Star size={14} className="icon-accent" />
              </button>
            </div>
          ))}
        </div>
      </div>
      <div>
        <div className="form-section-title">配置文件</div>
        <div className="file-list">
          <div className="file-list-item">
            <span>📄 {version.configFile}</span>
            <button className="icon-link" onClick={() => onPreviewFile(version.configFile)} title="查看内容">
              <Star size={14} className="icon-accent" />
            </button>
          </div>
        </div>
      </div>
    </SlideDrawer>
  );
}

function DeploymentTaskDrawer({
  initial, onClose, onSave,
}: {
  initial?: DeploymentTask;
  onClose: () => void;
  onSave: (t: DeploymentTask) => void | Promise<void>;
}) {
  const [faceProfileId, setFaceProfileId] = useState(initial?.faceProfileId || '');
  const [faceProfileName, setFaceProfileName] = useState(initial?.faceProfileName || '');
  const [faceProfilePhotoUrl, setFaceProfilePhotoUrl] = useState(initial?.faceProfilePhotoUrl || '');
  const [desc, setDesc] = useState(initial?.desc || '');
  const [enabled, setEnabled] = useState<boolean>(initial?.enabled ?? true);
  const [cameraIds, setCameraIds] = useState<string[]>(initial?.cameraIds || []);
  const [recognitionPerMinute, setRecognitionPerMinute] = useState(initial?.recognitionPerMinute || 60);
  const [faceProfiles, setFaceProfiles] = useState<FaceProfile[]>([]);
  const [faceUploadName, setFaceUploadName] = useState('');
  const [faceUploadDesc, setFaceUploadDesc] = useState('');
  const [faceUploadFile, setFaceUploadFile] = useState<File | null>(null);
  const [faceUploadPreview, setFaceUploadPreview] = useState('');
  const [uploadingFace, setUploadingFace] = useState(false);
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [saving, setSaving] = useState(false);
  const pipeline = '人脸识别流程';

  useEffect(() => {
    Promise.all([api.faces(), api.cameras()])
      .then(([faces, cams]) => {
        setFaceProfiles(faces);
        const sortedCams = [...cams].sort((a, b) => a.createdAt.localeCompare(b.createdAt));
        setCameras(sortedCams);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!faceUploadFile) {
      setFaceUploadPreview('');
      return undefined;
    }
    const previewUrl = URL.createObjectURL(faceUploadFile);
    setFaceUploadPreview(previewUrl);
    return () => URL.revokeObjectURL(previewUrl);
  }, [faceUploadFile]);

  const toggleCamera = (id: string) => {
    setCameraIds(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]);
  };

  const selectAllCameras = () => {
    if (cameraIds.length === cameras.length) {
      setCameraIds([]);
    } else {
      setCameraIds(cameras.map(c => c.id));
    }
  };

  const selectedCams = cameraIds
    .map(id => cameras.find(c => c.id === id))
    .filter((c): c is Camera => Boolean(c));
  const areas = Array.from(new Set(selectedCams.map(c => (c.area || '').trim()).filter(Boolean)));
  const previewName = selectedCams.length === 0
    ? '布控任务'
    : selectedCams.length === 1
      ? `${selectedCams[0].name} 布控`
      : `${selectedCams[0].name} 等 ${selectedCams.length} 路 布控`;
  const previewArea = initial?.area || areas[0] || '—';

  const uploadSelectedFace = async () => {
    if (!faceUploadFile) {
      throw new Error('请先选择人脸照片');
    }
    const displayName = faceUploadName.trim() || faceUploadFile.name.replace(/\.[^.]+$/, '') || '人脸库照片';
    const form = new FormData();
    form.append('name', displayName);
    form.append('description', faceUploadDesc.trim());
    form.append('photo', faceUploadFile);
    setUploadingFace(true);
    try {
      const face = await api.createFace(form);
      setFaceProfiles(prev => [face, ...prev.filter(item => item.id !== face.id)]);
      setFaceProfileId(face.id);
      setFaceProfileName(face.name);
      setFaceProfilePhotoUrl(face.photoUrl);
      setFaceUploadName('');
      setFaceUploadDesc('');
      setFaceUploadFile(null);
      return face;
    } finally {
      setUploadingFace(false);
    }
  };

  const handleUploadFace = async () => {
    try {
      await uploadSelectedFace();
    } catch (e: unknown) {
      alert(`上传失败：${messageOf(e)}`);
    }
  };

  const handleSave = async () => {
    let selectedFaceId = faceProfileId;
    let selectedFaceName = faceProfileName;
    let selectedFacePhotoUrl = faceProfilePhotoUrl;
    if (!selectedFaceId && faceUploadFile) {
      try {
        const uploadedFace = await uploadSelectedFace();
        selectedFaceId = uploadedFace.id;
        selectedFaceName = uploadedFace.name;
        selectedFacePhotoUrl = uploadedFace.photoUrl;
      } catch (e: unknown) {
        alert(`上传失败：${messageOf(e)}`);
        return;
      }
    }
    if (!selectedFaceId) { alert('请选择布控目标（人脸库）或上传人脸照片'); return; }
    if (cameraIds.length === 0) { alert('请至少选择一个摄像头'); return; }
    if (!Number.isInteger(recognitionPerMinute) || recognitionPerMinute < 1) {
      alert('每分钟识别次数必须是正整数');
      return;
    }
    setSaving(true);
    try {
      await onSave({
        id: initial?.id || '',
        name: previewName,
        pipeline,
        area: previewArea === '—' ? '' : previewArea,
        areaCount: cameraIds.length,
        enabled,
        taskStatus: initial?.taskStatus || (enabled ? 'running' : 'stopped'),
        desc: desc.trim(),
        faceProfileId: selectedFaceId,
        faceProfileName: selectedFaceName || null,
        faceProfilePhotoUrl: selectedFacePhotoUrl || null,
        cameraIds,
        recognitionPerMinute,
        createdAt: initial?.createdAt || new Date().toISOString(),
        updatedAt: initial?.updatedAt || new Date().toISOString(),
      });
    } catch (e: unknown) {
      alert(`保存失败：${messageOf(e)}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <SlideDrawer
      title={initial ? '编辑布控任务' : '新建布控任务'}
      onClose={onClose}
      footer={
        <>
          <button onClick={onClose} disabled={saving}>取消</button>
          <button onClick={handleSave} disabled={saving} className="omni-primary-btn">
            {saving ? '保存中…' : '保存'}
          </button>
        </>
      }
    >
      <div className="task-preview-panel">
        <div className="task-preview-row">
          <strong>任务名称：</strong>
          <span>{previewName}</span>
        </div>
        <div className="task-preview-row">
          <strong>布控区域：</strong>
          <span>📍 {previewArea}（来自摄像头）</span>
        </div>
        <div className="task-preview-help">保存后由后端根据所选摄像头自动写入数据库</div>
      </div>
      <div>
        <div className="form-section-title">布控目标（人脸库）</div>
        <div className="deploy-face-card">
          <div className="deploy-card-head">
            <strong>上传新人脸照片</strong>
            <span>保存到人脸库后自动选中</span>
          </div>
          <label className="form-label">
            <span>人员名称</span>
            <input value={faceUploadName} onChange={e => setFaceUploadName(e.target.value)} placeholder="默认使用图片文件名" />
          </label>
          <label className="form-label">
            <span>备注</span>
            <input value={faceUploadDesc} onChange={e => setFaceUploadDesc(e.target.value)} placeholder="请输入备注" />
          </label>
          <div className="deploy-face-upload-grid">
            <label className={`file-dropzone face-dropzone ${faceUploadFile ? 'has-file' : ''}`}>
              <input
                type="file"
                accept="image/*"
                onChange={event => {
                  const file = event.target.files?.[0] || null;
                  setFaceUploadFile(file);
                  if (file && !faceUploadName.trim()) {
                    setFaceUploadName(file.name.replace(/\.[^.]+$/, ''));
                  }
                }}
              />
              <Upload size={26} />
              <span>{faceUploadFile?.name || '点击上传人脸照片'}</span>
            </label>
            {faceUploadPreview ? (
              <img
                src={faceUploadPreview}
                alt={faceUploadName || '人脸照片预览'}
                className="face-preview-image"
              />
            ) : (
              <div className="face-preview-placeholder">预览</div>
            )}
          </div>
          <button
            type="button"
            onClick={handleUploadFace}
            disabled={!faceUploadFile || uploadingFace || saving}
            className="omni-primary-btn align-start"
          >
            {uploadingFace ? '上传中…' : '上传到人脸库并选择'}
          </button>
        </div>
        <label className="form-label">
          <span><span className="required-mark">*</span>选择人脸库照片</span>
          <select
            value={faceProfileId}
            onChange={e => {
              const id = e.target.value;
              setFaceProfileId(id);
              const p = faceProfiles.find(x => x.id === id);
              if (p) {
                setFaceProfileName(p.name);
                setFaceProfilePhotoUrl(p.photoUrl);
              } else {
                setFaceProfileName('');
                setFaceProfilePhotoUrl('');
              }
            }}
          >
            <option value="">请选择人脸库照片</option>
            {faceProfiles.map(p => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </label>
        {faceProfilePhotoUrl && (
          <div className="face-selected-preview">
            <img
              src={assetUrl(faceProfilePhotoUrl)}
              alt={faceProfileName || ''}
              className="face-selected-image"
            />
            <span>{faceProfileName}</span>
          </div>
        )}
      </div>
      <div>
        <div className="form-section-title">编排算法</div>
        <div className="form-label">
          <span>算法流程</span>
          <input value={pipeline} readOnly disabled className="readonly-input" />
        </div>
        <label className="form-label">
          <span><span className="required-mark">*</span>每分钟识别次数</span>
          <input
            type="number"
            min={1}
            step={1}
            value={recognitionPerMinute}
            onChange={e => {
              const next = Number(e.target.value);
              setRecognitionPerMinute(Number.isFinite(next) ? Math.max(1, Math.floor(next)) : 1);
            }}
          />
        </label>
        <div className="field-note">人脸检测 → 人脸特征提取 → 1:N 比对 → 命中告警</div>
      </div>
      <div>
        <div className="form-section-title">
          <span><span className="required-mark">*</span>布控摄像头（从设备管理加载）</span>
          <span className="form-section-note">
            已选 {cameraIds.length} / {cameras.length}
          </span>
        </div>
        <div className="compact-action-row">
          <button type="button" onClick={selectAllCameras} className="small-btn">
            {cameraIds.length === cameras.length ? '清空选择' : '全选'}
          </button>
        </div>
        <div className="deploy-camera-list">
          {cameras.length === 0 && <div className="field-note">正在加载摄像头…</div>}
          {cameras.map(c => (
            <label key={c.id} className="deploy-camera-option">
              <input
                type="checkbox"
                checked={cameraIds.includes(c.id)}
                onChange={() => toggleCamera(c.id)}
              />
              <span className="deploy-camera-name">{c.name}</span>
              <span className="deploy-camera-meta">{c.area || '—'}</span>
              <span className="deploy-camera-status">{c.status}</span>
            </label>
          ))}
        </div>
      </div>
      <label className="form-label"><span>启用</span>
        <button
          type="button"
          onClick={() => setEnabled(e => !e)}
          className={`toggle-action ${enabled ? 'enabled' : 'disabled'}`}
        >
          {enabled ? <ToggleRight size={18} /> : <ToggleLeft size={18} />}
          {enabled ? '启用' : '禁用'}
        </button>
      </label>
      <label className="form-label"><span>任务描述</span>
        <textarea value={desc} onChange={e => setDesc(e.target.value)} placeholder="请输入任务描述" />
      </label>
    </SlideDrawer>
  );
}

type OrchestrationNodeKind = 'person' | 'vehicle' | 'object' | 'face' | 'plate' | 'voice' | 'condition' | 'alarm' | 'attribute';

type OrchestrationNode = {
  id: string;
  label: string;
  kind: OrchestrationNodeKind;
  input: string;
  output: string;
  left: number;
  top: number;
};

const ORCHESTRATION_FLOWS = ['人员检测流程', '车辆识别流程', '综合布控流程'];

const ORCHESTRATION_NODE_CATEGORIES: { title: string; nodes: { label: string; kind: OrchestrationNodeKind }[] }[] = [
  {
    title: '检测类',
    nodes: [
      { label: '人员检测', kind: 'person' },
      { label: '车辆检测', kind: 'vehicle' },
      { label: '物体检测', kind: 'object' },
    ],
  },
  {
    title: '识别类',
    nodes: [
      { label: '人脸识别', kind: 'face' },
      { label: '车牌识别', kind: 'plate' },
      { label: '声纹识别', kind: 'voice' },
    ],
  },
  {
    title: '逻辑节点',
    nodes: [
      { label: '条件判断', kind: 'condition' },
      { label: '告警触发', kind: 'alarm' },
    ],
  },
];

const ORCHESTRATION_CANVAS_NODES: OrchestrationNode[] = [
  { id: 'person-detect', label: '人员检测', kind: 'person', input: '图像', output: '检测框', left: 80, top: 80 },
  { id: 'face-identify', label: '人脸识别', kind: 'face', input: '人脸', output: '身份信息', left: 280, top: 80 },
  { id: 'attribute', label: '属性分析', kind: 'attribute', input: '图像', output: '属性', left: 80, top: 200 },
  { id: 'condition', label: '条件判断', kind: 'condition', input: '检测结果', output: 'Yes', left: 280, top: 200 },
];

function OrchestrationIcon({ kind, size = 14 }: { kind: OrchestrationNodeKind; size?: number }) {
  switch (kind) {
    case 'vehicle':
    case 'plate':
      return <Car size={size} />;
    case 'object':
    case 'attribute':
      return <Box size={size} />;
    case 'face':
      return <UserRound size={size} />;
    case 'voice':
      return <Mic size={size} />;
    case 'condition':
      return <GitBranch size={size} />;
    case 'alarm':
      return <BellRing size={size} />;
    case 'person':
    default:
      return <Search size={size} />;
  }
}

export function AlgorithmManagement() {
  const navigate = useNavigate();
  const [algorithms, setAlgorithms] = useState<Algorithm[]>(loadStoredAlgorithms);
  const [showCreate, setShowCreate] = useState(false);
  const [filterName, setFilterName] = useState('');
  const [filterType, setFilterType] = useState<string>('');
  const [filterDate, setFilterDate] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [tritonModels, setTritonModels] = useState<ModelInfo[]>([]);
  const [modelGpus, setModelGpus] = useState<Record<string, ModelGpuConfig>>({});
  const [gpuDrafts, setGpuDrafts] = useState<Record<string, number>>({});
  const [gpuSaving, setGpuSaving] = useState('');

  useEffect(() => {
    saveStoredAlgorithms(algorithms);
  }, [algorithms]);

  const loadTritonModelGpuConfigs = useCallback(async () => {
    try {
      const models = await api.models();
      const faceModels = models.filter(model => isFaceModel(model.name));
      setTritonModels(faceModels);
      const configs = await Promise.all(
        faceModels.map(async model => {
          try {
            return await api.modelGpu(model.name);
          } catch {
            return null;
          }
        })
      );
      const byName: Record<string, ModelGpuConfig> = {};
      const drafts: Record<string, number> = {};
      configs.forEach(config => {
        if (!config) return;
        byName[config.modelName] = config;
        drafts[config.modelName] = config.gpuIds[0] ?? 0;
      });
      setModelGpus(byName);
      setGpuDrafts(drafts);
    } catch (error) {
      console.error('load model gpu configs failed', error);
    }
  }, []);

  useEffect(() => {
    loadTritonModelGpuConfigs();
  }, [loadTritonModelGpuConfigs]);

  const filtered = useMemo(() => algorithms.filter(a => {
    if (filterName && !a.name.includes(filterName)) return false;
    if (filterType && a.type !== filterType) return false;
    if (filterDate && a.updatedAt !== filterDate) return false;
    return true;
  }), [algorithms, filterName, filterType, filterDate]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
  const paged = filtered.slice((page - 1) * pageSize, page * pageSize);

  const handleReset = () => { setFilterName(''); setFilterType(''); setFilterDate(''); setPage(1); };

  const handleCreate = ({ algorithm, initialVersion }: AlgorithmCreateData) => {
    setAlgorithms(prev => [algorithm, ...prev]);
    const versions = loadStoredAlgorithmVersions();
    saveStoredAlgorithmVersions({
      ...versions,
      [algorithm.id]: [{ id: `${algorithm.id}-v-${Date.now()}`, ...initialVersion }],
    });
    setShowCreate(false);
    setPage(1);
  };

  const handleDelete = (id: string) => {
    if (confirm('确认删除该算法？')) {
      setAlgorithms(prev => prev.filter(a => a.id !== id));
      const versions = loadStoredAlgorithmVersions();
      delete versions[id];
      saveStoredAlgorithmVersions(versions);
    }
  };

  const handleSaveGpu = async (modelName: string) => {
    const nextGpu = gpuDrafts[modelName] ?? 0;
    if (!Number.isInteger(nextGpu) || nextGpu < 0) {
      alert('GPU 卡号必须是非负整数');
      return;
    }
    setGpuSaving(modelName);
    try {
      const config = await api.updateModelGpu(modelName, [nextGpu]);
      setModelGpus(prev => ({ ...prev, [modelName]: config }));
      await loadTritonModelGpuConfigs();
    } catch (error) {
      alert(`保存 GPU 配置失败：${messageOf(error)}`);
    } finally {
      setGpuSaving('');
    }
  };

  return (
    <>
      <header className="topbar">
        <div><h1>算法布控</h1><p>Triton 算法模型管理</p></div>
        <button onClick={() => setShowCreate(true)} className="omni-primary-btn">
          <Plus size={16} />新增算法
        </button>
      </header>

      <SubTabs active="algorithms" />

      <div className="toolbar-row toolbar-row-wrap">
        <div className="filter-toolbar filter-toolbar-compact">
          <div className="filter-group">
            <label>算法名称</label>
            <input value={filterName} onChange={e => setFilterName(e.target.value)} placeholder="请输入" className="filter-input-name" />
          </div>
          <div className="filter-group">
            <label>算法类型</label>
            <select value={filterType} onChange={e => setFilterType(e.target.value)} className="filter-input-type">
              <option value="">请选择</option>
              {ALGO_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div className="filter-group">
            <label>更新时间</label>
            <input type="date" value={filterDate} onChange={e => setFilterDate(e.target.value)} className="filter-input-date" />
          </div>
          <button onClick={() => setPage(1)} className="omni-primary-btn">查询</button>
          <button onClick={handleReset}>重置</button>
        </div>
      </div>

      <div className="panel">
        <table>
          <thead>
            <tr>
              <th className="col-checkbox"><input type="checkbox" /></th>
              <th>算法名称</th>
              <th>版本号</th>
              <th>算法类型</th>
              <th>更新时间</th>
              <th>描述</th>
              <th className="col-actions">操作</th>
            </tr>
          </thead>
          <tbody>
            {paged.map(a => (
              <tr key={a.id}>
                <td><input type="checkbox" /></td>
                <td>{a.name}</td>
                <td>
                  <button
                    className="icon-link link-accent"
                    onClick={() => navigate(`/algo-deploy/versions/${a.id}`)}
                  >
                    {a.version}
                  </button>
                  <Star size={12} className="icon-accent icon-inline" />
                </td>
                <td>{a.type}</td>
                <td>{a.updatedAt}</td>
                <td>{a.desc}</td>
                <td><button onClick={() => handleDelete(a.id)} className="icon-link link-danger">删除</button></td>
              </tr>
            ))}
            {paged.length === 0 && (
              <tr><td colSpan={7} className="empty-cell">暂无数据</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="panel model-gpu-panel">
        <div className="section-head">
          <strong>人脸识别模型 GPU 配置</strong>
          <button type="button" onClick={loadTritonModelGpuConfigs}>刷新</button>
        </div>
        <table>
          <thead>
            <tr>
              <th>模型名称</th>
              <th>状态</th>
              <th>当前 GPU</th>
              <th>指定 GPU 卡</th>
              <th className="col-actions">操作</th>
            </tr>
          </thead>
          <tbody>
            {tritonModels.map(model => {
              const current = modelGpus[model.name]?.gpuIds ?? [];
              const draft = gpuDrafts[model.name] ?? current[0] ?? 0;
              return (
                <tr key={model.name}>
                  <td>{model.displayName || model.name}</td>
                  <td>{model.state}</td>
                  <td>{current.length ? current.join(', ') : '未指定'}</td>
                  <td>
                    <select
                      value={draft}
                      onChange={event => {
                        const next = Number(event.target.value);
                        setGpuDrafts(prev => ({ ...prev, [model.name]: next }));
                      }}
                      className="gpu-select"
                    >
                      {[0, 1, 2, 3, 4, 5, 6, 7].map(gpu => (
                        <option key={gpu} value={gpu}>GPU-{gpu}</option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <button
                      type="button"
                      onClick={() => handleSaveGpu(model.name)}
                      disabled={gpuSaving === model.name}
                      className="icon-link link-accent"
                    >
                      {gpuSaving === model.name ? '保存中…' : '保存并重载'}
                    </button>
                  </td>
                </tr>
              );
            })}
            {tritonModels.length === 0 && (
              <tr><td colSpan={5} className="empty-cell">暂无可配置的人脸识别模型</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {filtered.length > 0 && (
        <Pagination page={page} totalPages={totalPages} pageSize={pageSize} onPageChange={setPage} onPageSizeChange={n => { setPageSize(n); setPage(1); }} />
      )}

      {showCreate && <AlgorithmCreateDrawer onClose={() => setShowCreate(false)} onSave={handleCreate} />}
    </>
  );
}

export function AlgorithmOrchestration() {
  const [activeFlow, setActiveFlow] = useState(ORCHESTRATION_FLOWS[0]);
  const [selectedNodeId, setSelectedNodeId] = useState(ORCHESTRATION_CANVAS_NODES[0].id);
  const selectedNode = ORCHESTRATION_CANVAS_NODES.find(node => node.id === selectedNodeId) || ORCHESTRATION_CANVAS_NODES[0];

  return (
    <>
      <header className="topbar">
        <div><h1>算法编排</h1><p>可视化算法流程编排</p></div>
        <button type="button" className="omni-primary-btn">
          <Plus size={16} />新建编排流程
        </button>
      </header>

      <SubTabs active="orchestration" />

      <section className="panel algo-orchestration-page">
        <div className="algo-orchestration-heading">
          <h2>算法编排</h2>
          <button type="button" className="omni-primary-btn">
            <Plus size={16} />新建编排流程
          </button>
        </div>

        <div className="algo-flow-tabs">
          {ORCHESTRATION_FLOWS.map(flow => (
            <button
              type="button"
              key={flow}
              className={`algo-flow-tab ${activeFlow === flow ? 'active' : ''}`}
              onClick={() => setActiveFlow(flow)}
            >
              {flow}
            </button>
          ))}
          <button type="button" className="algo-flow-tab add">+ 新建</button>
        </div>

        <div className="algo-orchestration-layout">
          <aside className="algo-node-panel">
            {ORCHESTRATION_NODE_CATEGORIES.map(category => (
              <div className="algo-node-category" key={category.title}>
                <div className="algo-node-category-title">{category.title}</div>
                {category.nodes.map(node => (
                  <div className="algo-node-item" key={node.label} draggable>
                    <OrchestrationIcon kind={node.kind} />
                    {node.label}
                  </div>
                ))}
              </div>
            ))}
            <p className="algo-node-hint">拖拽节点到画布</p>
          </aside>

          <div className="algo-canvas-panel">
            <div className="algo-canvas-grid" />
            <svg className="algo-canvas-lines" viewBox="0 0 600 380" aria-hidden="true">
              <path d="M220 118 C245 118 255 118 280 118" />
              <path d="M220 238 C245 238 255 238 280 238" />
              <path d="M350 153 C350 172 350 181 350 200" />
            </svg>
            {ORCHESTRATION_CANVAS_NODES.map(node => (
              <button
                type="button"
                key={node.id}
                className={`algo-flow-node ${selectedNodeId === node.id ? 'selected' : ''}`}
                style={{ left: node.left, top: node.top }}
                onClick={() => setSelectedNodeId(node.id)}
              >
                <div className="algo-flow-node-header">
                  <span className="algo-flow-node-icon"><OrchestrationIcon kind={node.kind} /></span>
                  <span>{node.label}</span>
                </div>
                <div className="algo-flow-node-ports">
                  <span><i className="dot in" />输入: {node.input}</span>
                  <span>输出: <i className="dot out" />{node.output}</span>
                </div>
              </button>
            ))}
          </div>

          <aside className="algo-config-panel">
            <div className="algo-config-title">节点配置</div>
            <label className="algo-config-group">
              <span>节点名称</span>
              <input key={`${selectedNode.id}-name`} type="text" defaultValue={selectedNode.label} />
            </label>
            <label className="algo-config-group">
              <span>类型</span>
              <select key={`${selectedNode.id}-type`} defaultValue={selectedNode.kind === 'condition' || selectedNode.kind === 'alarm' ? '逻辑节点' : selectedNode.kind === 'face' || selectedNode.kind === 'plate' || selectedNode.kind === 'voice' ? '识别类' : '检测类'}>
                <option>检测类</option>
                <option>识别类</option>
                <option>逻辑节点</option>
              </select>
            </label>
            <div className="algo-config-group">
              <span>输入参数</span>
              <pre>{'{ "image": "bitmap" }'}</pre>
            </div>
            <div className="algo-config-group">
              <span>输出参数</span>
              <pre>{'{\n  "bbox": [],\n  "attributes": {}\n}'}</pre>
            </div>
            <label className="algo-config-group">
              <span>规则配置</span>
              <textarea key={`${selectedNode.id}-rule`} defaultValue="score > 0.85 && region == '重点区域'" />
            </label>
            <label className="algo-config-group">
              <span>告警设置</span>
              <select key={`${selectedNode.id}-alarm`} defaultValue="检测到目标时">
                <option>不触发告警</option>
                <option>检测到目标时</option>
                <option>符合条件时</option>
              </select>
            </label>
          </aside>
        </div>
      </section>
    </>
  );
}

export function AlgorithmVersions() {
  const navigate = useNavigate();
  const { algoId } = useParams<{ algoId?: string }>();
  const activeAlgoId = algoId || '1';
  const [algorithms, setAlgorithms] = useState<Algorithm[]>(loadStoredAlgorithms);
  const [versionsByAlgo, setVersionsByAlgo] = useState<Record<string, AlgorithmVersion[]>>(loadStoredAlgorithmVersions);

  const algo = algorithms.find(a => a.id === activeAlgoId) || algorithms[0];
  const versions = algo ? versionsByAlgo[algo.id] || [] : [];

  const [showCreateVersion, setShowCreateVersion] = useState(false);
  const [detailVersion, setDetailVersion] = useState<AlgorithmVersion | null>(null);
  const [previewFile, setPreviewFile] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  useEffect(() => {
    saveStoredAlgorithms(algorithms);
  }, [algorithms]);

  useEffect(() => {
    saveStoredAlgorithmVersions(versionsByAlgo);
  }, [versionsByAlgo]);

  const totalPages = Math.max(1, Math.ceil(versions.length / pageSize));
  const paged = versions.slice((page - 1) * pageSize, page * pageSize);

  const handleCreateVersion = (v: Omit<AlgorithmVersion, 'id'>) => {
    if (!algo) return;
    const nextVersion = { id: String(Date.now()), ...v };
    setVersionsByAlgo(prev => ({
      ...prev,
      [algo.id]: [nextVersion, ...(prev[algo.id] || [])],
    }));
    setAlgorithms(prev => prev.map(a => a.id === algo.id ? { ...a, version: v.version, updatedAt: v.updatedAt } : a));
    setShowCreateVersion(false);
    setPage(1);
  };

  const handleDeleteVersion = (vid: string) => {
    if (!algo) return;
    if (confirm('确认删除该版本？')) {
      const nextVersions = (versionsByAlgo[algo.id] || []).filter(v => v.id !== vid);
      setVersionsByAlgo(prev => ({ ...prev, [algo.id]: nextVersions }));
      setAlgorithms(prev => prev.map(a => (
        a.id === algo.id
          ? { ...a, version: nextVersions[0]?.version || a.version, updatedAt: nextVersions[0]?.updatedAt || a.updatedAt }
          : a
      )));
    }
  };

  const handleDeleteAlgo = () => {
    if (!algo) return;
    if (confirm(`确认删除算法「${algo.name}」？此操作不可恢复`)) {
      setAlgorithms(prev => prev.filter(a => a.id !== algo.id));
      setVersionsByAlgo(prev => {
        const next = { ...prev };
        delete next[algo.id];
        return next;
      });
      navigate('/algo-deploy/algorithms');
    }
  };

  const handleDownload = (ver: AlgorithmVersion) => {
    alert(`下载版本 ${ver.version} 的算法包`);
  };

  if (!algo) {
    return (
      <>
        <header className="topbar">
          <div className="algo-heading">
            <button
              className="icon-btn panel-icon-btn"
              onClick={() => navigate('/algo-deploy/algorithms')}
              title="返回算法管理"
            >
              <ArrowLeft size={18} />
            </button>
            <div><h1>算法版本管理</h1></div>
          </div>
        </header>
        <div className="panel"><div className="empty-cell">暂无算法数据</div></div>
      </>
    );
  }

  return (
    <>
      <header className="topbar">
        <div className="algo-heading">
          <button
            className="icon-btn panel-icon-btn"
            onClick={() => navigate('/algo-deploy/algorithms')}
            title="返回算法管理"
          >
            <ArrowLeft size={18} />
          </button>
          <div>
            <div className="breadcrumb">
              <a href="/algo-deploy/algorithms">算法管理</a>
              <span className="breadcrumb-sep">/</span>
              <span>{algo.name}</span>
            </div>
            <h1>算法版本管理</h1>
          </div>
        </div>
        <div className="button-row">
          <button onClick={() => setShowCreateVersion(true)} className="omni-primary-btn">
            <Plus size={16} />新增版本
          </button>
          <button onClick={handleDeleteAlgo} className="danger-btn">
            删除算法
          </button>
        </div>
      </header>

      <div className="panel version-summary-panel">
        <div className="version-summary">
          <span>版本数量：<strong>{versions.length}</strong></span>
          <span>算法类型：<strong>{algo.type}</strong></span>
          <span>最近更新时间：<strong>{versions[0]?.updatedAt || algo.updatedAt}</strong></span>
        </div>
      </div>

      <div className="panel">
        <table>
          <thead>
            <tr>
              <th className="col-checkbox"><input type="checkbox" /></th>
              <th>版本号</th>
              <th>版本说明</th>
              <th>更新时间</th>
              <th className="col-actions-wide">操作</th>
            </tr>
          </thead>
          <tbody>
            {paged.map(v => (
              <tr key={v.id}>
                <td><input type="checkbox" /></td>
                <td>{v.version}</td>
                <td>{v.desc}</td>
                <td>{v.updatedAt}</td>
                <td>
                  <button className="icon-link link-accent" onClick={() => setDetailVersion(v)}>详情</button>
                  <span className="table-separator">|</span>
                  <button className="icon-link link-muted" onClick={() => handleDownload(v)}>下载</button>
                  <span className="table-separator">|</span>
                  <button className="icon-link link-danger" onClick={() => handleDeleteVersion(v.id)}>删除</button>
                  <Star size={12} className="icon-accent icon-inline" />
                </td>
              </tr>
            ))}
            {paged.length === 0 && (
              <tr><td colSpan={5} className="empty-cell">暂无版本数据</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {versions.length > 0 && (
        <Pagination page={page} totalPages={totalPages} pageSize={pageSize} onPageChange={setPage} onPageSizeChange={n => { setPageSize(n); setPage(1); }} />
      )}

      {showCreateVersion && (
        <VersionCreateModal onClose={() => setShowCreateVersion(false)} onSave={handleCreateVersion} />
      )}
      {detailVersion && (
        <VersionDetailDrawer
          version={detailVersion}
          onClose={() => setDetailVersion(null)}
          onPreviewFile={name => setPreviewFile(name)}
        />
      )}
      {previewFile && (
        <FilePreviewModal fileName={previewFile} onClose={() => setPreviewFile(null)} />
      )}
    </>
  );
}

export function DeploymentTasks() {
  const [tasks, setTasks] = useState<DeploymentTask[]>([]);
  const [search, setSearch] = useState('');
  const [editing, setEditing] = useState<DeploymentTask | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [loading, setLoading] = useState(false);
  const [matchEvents, setMatchEvents] = useState<FaceMatchEvent[]>([]);
  const [matchLoading, setMatchLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const list = await api.deploymentTasks();
      setTasks(list);
    } catch (e) {
      console.error('load deployment tasks failed', e);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadMatchEvents = useCallback(async () => {
    setMatchLoading(true);
    try {
      const list = await api.faceMatchEvents(5);
      setMatchEvents(list);
    } catch (e) {
      console.error('load face match events failed', e);
    } finally {
      setMatchLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { loadMatchEvents(); }, [loadMatchEvents]);
  useEffect(() => {
    const timer = window.setInterval(() => { loadMatchEvents(); }, 5000);
    return () => window.clearInterval(timer);
  }, [loadMatchEvents]);

  const filtered = tasks.filter(t => !search || t.name.includes(search) || t.area.includes(search));

  const toggleEnabled = async (t: DeploymentTask) => {
    const next = !t.enabled;
    setTasks(prev => prev.map(x => x.id === t.id ? { ...x, enabled: next } : x));
    try {
      await api.updateDeploymentTask(t.id, { enabled: next });
    } catch (e: unknown) {
      setTasks(prev => prev.map(x => x.id === t.id ? { ...x, enabled: t.enabled } : x));
      alert(`切换失败：${messageOf(e)}`);
    }
  };

  const handleSave = async (t: DeploymentTask) => {
    const payload: DeploymentTaskCreate = {
      name: t.name,
      pipeline: t.pipeline,
      area: t.area,
      areaCount: t.areaCount,
      enabled: t.enabled,
      desc: t.desc,
      faceProfileId: t.faceProfileId || null,
      faceProfileName: t.faceProfileName || null,
      faceProfilePhotoUrl: t.faceProfilePhotoUrl || null,
      cameraIds: t.cameraIds,
      recognitionPerMinute: t.recognitionPerMinute || 60,
    };
    if (t.id) {
      const updated = await api.updateDeploymentTask(t.id, payload);
      setTasks(prev => prev.map(x => x.id === t.id ? updated : x));
    } else {
      const created = await api.createDeploymentTask(payload);
      setTasks(prev => [created, ...prev]);
    }
    setEditing(null);
    setShowCreate(false);
  };

  const handleDelete = async (id: string) => {
    if (!confirm('确认删除该布控任务？')) return;
    const prev = tasks;
    setTasks(curr => curr.filter(t => t.id !== id));
    try {
      await api.deleteDeploymentTask(id);
    } catch (e: unknown) {
      setTasks(prev);
      alert(`删除失败：${messageOf(e)}`);
    }
  };

  const formatMatchedAt = (iso?: string | null) => {
    if (!iso) return '—';
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    const pad = (n: number) => n.toString().padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
  };

  return (
    <>
      <header className="topbar">
        <div><h1>布控任务</h1><p>实时算法布控任务管理 · 共 {tasks.length} 个任务</p></div>
        <button onClick={() => setShowCreate(true)} className="omni-primary-btn">
          <Plus size={16} />新建布控任务
        </button>
      </header>

      <SubTabs active="tasks" />

      <div className="deployment-tasks-layout">
        <div className="deployment-tasks-main">
          <div className="search-bar task-search">
            <Search size={16} />
            <input value={search} onChange={e => setSearch(e.target.value)} placeholder="搜索任务名/区域..." />
          </div>

          {loading && tasks.length === 0 ? (
            <div className="empty">加载中…</div>
          ) : filtered.length === 0 ? (
            <div className="empty">{tasks.length === 0 ? '暂无布控任务，点击右上角"新建布控任务"开始' : '未找到匹配任务'}</div>
          ) : (
            <div className="task-grid">
              {filtered.map(t => (
                <div key={t.id} className="task-card">
                  <div className="task-card-title">
                    {t.name}
                    <span className={`task-status-badge ${t.taskStatus === 'running' ? 'running' : 'stopped'}`}>{t.taskStatus === 'running' ? '运行中' : '已停止'}</span>
                  </div>
                  <div className="task-card-row"><span>编排</span><span>{t.pipeline}</span></div>
                  <div className="task-card-row"><span>区域</span><span>{t.area}</span></div>
                  <div className="task-card-row"><span>摄像头</span><span>{t.cameraIds?.length ?? 0} 个</span></div>
                  <div className="task-card-row"><span>识别频率</span><span>{t.recognitionPerMinute || 60} 次/分钟</span></div>
                  {t.faceProfileName && (
                    <div className="task-card-row">
                      <span>布控目标</span>
                      <span className="task-target">
                        {t.faceProfilePhotoUrl && (
                          <img
                            src={assetUrl(t.faceProfilePhotoUrl)}
                            alt={t.faceProfileName}
                            className="task-target-image"
                          />
                        )}
                        <span>{t.faceProfileName}</span>
                      </span>
                    </div>
                  )}
                  <div className="task-card-row">
                    <span>状态</span>
                    <button
                      className="toggle-icon"
                      onClick={() => toggleEnabled(t)}
                    >
                      <span className={`toggle-badge ${t.enabled ? 'enabled' : 'disabled'}`}>{t.enabled ? '启用' : '禁用'}</span>
                      {t.enabled ? <ToggleRight size={22} className="toggle-icon-enabled" /> : <ToggleLeft size={22} className="toggle-icon-disabled" />}
                    </button>
                  </div>
                  <div className="task-card-actions">
                    <button onClick={() => setEditing(t)}>编辑</button>
                    <button onClick={() => handleDelete(t.id)} className="link-danger">删除</button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <aside className="match-feed-panel">
          <div className="match-feed-header">
            <span className="match-feed-title">最近人脸匹配</span>
            <span className="match-feed-count">最新 {matchEvents.length} 条</span>
          </div>
          {matchLoading && matchEvents.length === 0 ? (
            <div className="match-feed-empty">加载中…</div>
          ) : matchEvents.length === 0 ? (
            <div className="match-feed-empty">暂无匹配记录</div>
          ) : (
            <ul className="match-feed-list">
              {matchEvents.map(ev => (
                <li key={ev.id} className="match-feed-item">
                  <div className="match-feed-photos">
                    <div className="match-feed-photo-cell">
                      <span className="match-feed-photo-label">布控目标</span>
                      {ev.faceProfilePhotoUrl ? (
                        <img
                          src={assetUrl(ev.faceProfilePhotoUrl)}
                          alt={ev.faceProfileName || '布控目标'}
                          className="match-feed-photo"
                        />
                      ) : (
                        <div className="match-feed-photo placeholder">无图</div>
                      )}
                    </div>
                    <div className="match-feed-photo-cell">
                      <span className="match-feed-photo-label">屏幕截屏</span>
                      {ev.snapshotUrl ? (
                        <img
                          src={assetUrl(ev.snapshotUrl)}
                          alt={ev.cameraName ? `${ev.cameraName} 抓拍` : '截屏'}
                          className="match-feed-photo"
                        />
                      ) : (
                        <div className="match-feed-photo placeholder">无图</div>
                      )}
                    </div>
                  </div>
                  <div className="match-feed-meta">
                    <span className="match-feed-name" title={ev.faceProfileName || ''}>
                      {ev.faceProfileName || '未知目标'}
                    </span>
                    <span className="match-feed-time">⏱ {formatMatchedAt(ev.matchedAt)}</span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </aside>
      </div>

      {showCreate && <DeploymentTaskDrawer onClose={() => setShowCreate(false)} onSave={handleSave} />}
      {editing && <DeploymentTaskDrawer initial={editing} onClose={() => setEditing(null)} onSave={handleSave} />}
    </>
  );
}
