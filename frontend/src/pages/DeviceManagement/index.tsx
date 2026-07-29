import { FormEvent, useState, useEffect, useCallback, useMemo } from 'react';
import {
  Plus, Pencil, Trash2, Play, Pause, Upload, Download, Search, FolderClosed, FolderOpen,
  Eye, Filter, Radar, Settings2, X, FileText, Cpu,
} from 'lucide-react';
import { api, streamUrl } from '../../api';
import type { Camera } from '../../types';
import { VideoPlayer } from '../../VideoPlayer';
import { SAMPLE_AREAS, type AreaNode } from '../../data/areas';

const PROTOCOLS = [
  { value: 'rtsp', label: 'RTSP' },
  { value: 'rtmp', label: 'RTMP' },
  { value: 'onvif', label: 'ONVIF' },
  { value: 'gb28181', label: 'GB/T 28181' },
  { value: 'hik-sdk', label: '海康 SDK' },
  { value: 'dahua-sdk', label: '大华 SDK' },
  { value: 'ehome', label: 'Ehome/ISUP 5.0' },
];

const sampleAreas: AreaNode[] = SAMPLE_AREAS;
const defaultPasswordStrength = '中' as const;

function AreaTree({
  nodes, allNodes, depth = 0, selectedAreaId, onSelect, cameraCounts,
}: {
  nodes: AreaNode[];
  allNodes: AreaNode[];
  depth?: number;
  selectedAreaId: string;
  onSelect: (id: string) => void;
  cameraCounts: Record<string, number>;
}) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set(['root', 'area-3']));
  const toggle = (id: string) => {
    setExpanded(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };
  return (
    <div className="area-tree">
      {nodes.map(node => {
        const count = cameraCounts[node.id] ?? 0;
        const children = allNodes.filter(n => n.id.startsWith(node.id + '-') && n.id !== node.id);
        return (
          <div key={node.id}>
            <div
              className={`area-node area-depth-${Math.min(depth, 5)} ${selectedAreaId === node.id ? 'selected' : ''}`}
              onClick={() => onSelect(node.id)}
            >
              <span onClick={(e) => { e.stopPropagation(); toggle(node.id); }} className="area-toggle">
                {expanded.has(node.id) ? <FolderOpen size={14} /> : <FolderClosed size={14} />}
              </span>
              <span className="area-name">{node.name}</span>
              {count > 0 && <span className="area-count">{count}</span>}
            </div>
            {expanded.has(node.id) && children.length > 0 && (
              <AreaTree nodes={children} allNodes={allNodes} depth={depth + 1}
                selectedAreaId={selectedAreaId} onSelect={onSelect} cameraCounts={cameraCounts} />
            )}
          </div>
        );
      })}
    </div>
  );
}

export function DeviceList() {
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [search, setSearch] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Camera | null>(null);
  const [viewing, setViewing] = useState<Camera | null>(null);
  const [name, setName] = useState('');
  const [sourceUrl, setSourceUrl] = useState('');
  const [protocol, setProtocol] = useState('rtsp');
  const [area, setArea] = useState('办公楼');
  const [description, setDescription] = useState('');
  const [nvrId, setNvrId] = useState('');
  const [nvrChannel, setNvrChannel] = useState('');
  const [nvrTrackId, setNvrTrackId] = useState('');
  const [nvrStreamType, setNvrStreamType] = useState('main');
  const [formError, setFormError] = useState('');
  const [savingForm, setSavingForm] = useState(false);
  const [selectedAreaId, setSelectedAreaId] = useState('area-3');
  const [filterNeverConnected, setFilterNeverConnected] = useState(false);
  const [showChannelConfig, setShowChannelConfig] = useState(false);
  const [showBatch, setShowBatch] = useState(false);
  const [showDiscover, setShowDiscover] = useState(false);
  const [showBatchConfig, setShowBatchConfig] = useState(false);
  const [selectedCamera, setSelectedCamera] = useState<Camera | null>(null);
  const [discoveredDevices] = useState<{ ip: string; port: string; protocol: string; mac: string }[]>([
    { ip: '192.168.1.64', port: '8000', protocol: 'ONVIF', mac: '00:0C:29:XX:XX:XX' },
    { ip: '192.168.1.65', port: '8000', protocol: 'ONVIF', mac: '00:0C:29:YY:YY:YY' },
    { ip: '192.168.1.20', port: '554', protocol: 'RTSP', mac: 'BC:AD:28:XX:XX:XX' },
  ]);

  const load = useCallback(async () => {
    setCameras(await api.cameras());
  }, []);

  useEffect(() => { load(); }, [load]);

  const cameraCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    counts['area-3'] = cameras.length;
    counts.root = cameras.length;
    return counts;
  }, [cameras]);

  const selectedAreaName = useMemo(() => (
    sampleAreas.find(item => item.id === selectedAreaId)?.name || '办公楼'
  ), [selectedAreaId]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setFormError('');
    setSavingForm(true);
    const payload = {
      name: name.trim(),
      sourceUrl: sourceUrl.trim(),
      area: area.trim() || selectedAreaName,
      description: description.trim(),
      nvrId: nvrId.trim(),
      nvrChannel: nvrChannel.trim(),
      nvrTrackId: nvrTrackId.trim(),
      nvrStreamType,
    };
    try {
      if (editing) {
        await api.updateCamera(editing.id, payload);
      } else {
        await api.createCamera(payload);
      }
      await load();
      reset();
    } catch (error) {
      setFormError(error instanceof Error ? error.message : '设备保存失败');
      setSavingForm(false);
    }
  };

  const editCamera = (camera: Camera) => {
    setEditing(camera);
    setName(camera.name);
    setSourceUrl(camera.sourceUrl);
    setProtocol(protocolFromUrl(camera.sourceUrl));
    setArea(camera.area || '办公楼');
    setDescription(camera.description || '');
    setNvrId(camera.nvrId || '');
    setNvrChannel(camera.nvrChannel || '');
    setNvrTrackId(camera.nvrTrackId || '');
    setNvrStreamType(camera.nvrStreamType || 'main');
    setFormError('');
    setSavingForm(false);
    setShowForm(true);
  };

  const reset = () => {
    setEditing(null);
    setName('');
    setSourceUrl('');
    setProtocol('rtsp');
    setArea('办公楼');
    setDescription('');
    setNvrId('');
    setNvrChannel('');
    setNvrTrackId('');
    setNvrStreamType('main');
    setFormError('');
    setSavingForm(false);
    setShowForm(false);
  };

  const openCreateForm = () => {
    reset();
    setArea(selectedAreaName);
    setShowForm(true);
  };

  const filtered = cameras.filter(c => {
    if (search && !c.name.toLowerCase().includes(search.toLowerCase())) return false;
    if (filterNeverConnected && c.status === 'RUNNING') return false;
    return true;
  });

  return (
    <>
      <header className="topbar">
        <div><h1>设备管理</h1><p>管理音视频编码设备，共 {cameras.length} 台</p></div>
        <div className="button-row">
          <button onClick={() => setShowDiscover(true)}><Radar size={16} />主动发现</button>
          <button onClick={() => setShowBatch(true)}><Upload size={16} />批量导入</button>
          <button onClick={() => setShowBatchConfig(true)}><Cpu size={16} />批量配置能力</button>
          <button onClick={openCreateForm}><Plus size={16} />新增设备</button>
        </div>
      </header>

      <div className="device-layout">
        <aside className="device-tree-panel">
          <div className="panel-title">区域列表</div>
          <AreaTree nodes={sampleAreas.filter(n => n.id === 'root' || !n.id.slice(0, n.id.lastIndexOf('-')).includes('-'))} allNodes={sampleAreas} selectedAreaId={selectedAreaId} onSelect={setSelectedAreaId} cameraCounts={cameraCounts} />
        </aside>

        <section className="panel device-table-panel">
          <div className="filter-toolbar">
            <div className="search-bar">
              <Search size={16} />
              <input value={search} onChange={e => setSearch(e.target.value)} placeholder="搜索设备名称..." />
            </div>
            <label className="filter-toggle">
              <input type="checkbox" checked={filterNeverConnected} onChange={e => setFilterNeverConnected(e.target.checked)} />
              <Filter size={14} />仅显示未连接成功的设备
            </label>
          </div>
          <table>
            <thead>
              <tr>
                <th>设备名称</th>
                <th>所在区域</th>
                <th>接入协议</th>
                <th>IP地址</th>
                <th>端口号</th>
                <th>设备编号</th>
                <th>设备序列号</th>
                <th>密码强度</th>
                <th>状态</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((camera, idx) => (
                <tr key={camera.id}>
                  <td>{camera.name}</td>
                  <td>{camera.area || '未分配'}</td>
                  <td><span className="protocol-badge">{guessProtocol(camera.sourceUrl)}</span></td>
                  <td>{extractHost(camera.sourceUrl) || camera.sourceUrl}</td>
                  <td>{extractPort(camera.sourceUrl) || '-'}</td>
                  <td>{(idx + 1).toString().padStart(4, '0')}</td>
                  <td>{camera.id.slice(0, 12).toUpperCase()}</td>
                  <td><span className={`pwd-strength ${passwordStrengthClass(defaultPasswordStrength)}`}>{defaultPasswordStrength}</span></td>
                  <td><StatusBadge status={camera.status} /></td>
                  <td className="actions">
                    <button title="详情" onClick={() => setViewing(camera)}><Eye size={14} /></button>
                    <button title="编辑" onClick={() => editCamera(camera)}><Pencil size={14} /></button>
                    <button title="通道配置" onClick={() => { setSelectedCamera(camera); setShowChannelConfig(true); }}><Settings2 size={14} /></button>
                    <button title="启动" onClick={async () => { await api.startCamera(camera.id); await load(); }}><Play size={14} /></button>
                    <button title="停止" onClick={async () => { await api.stopCamera(camera.id); await load(); }}><Pause size={14} /></button>
                    <button title="删除" onClick={async () => { await api.deleteCamera(camera.id); await load(); }}><Trash2 size={14} /></button>
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr><td colSpan={10} className="empty-cell">暂无设备</td></tr>
              )}
            </tbody>
          </table>
        </section>
      </div>

      {showForm && (
        <div className="modal-overlay" onClick={reset}>
          <div className="modal modal-wide" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title">{editing ? '编辑设备' : '新增设备'}</div>
              <button className="icon-btn" onClick={reset}><X size={18} /></button>
            </div>
            <form onSubmit={submit} className="device-form">
              {formError && <div className="alert">{formError}</div>}
              <div className="form-section">
                <div className="form-section-title">基本信息</div>
                <label><span>设备名称</span><input value={name} onChange={e => setName(e.target.value)} required /></label>
                <label><span>接入协议</span>
                  <select value={protocol} onChange={e => setProtocol(e.target.value)}>
                    {PROTOCOLS.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
                  </select>
                </label>
                <label><span>所在区域</span><input value={area} onChange={e => setArea(e.target.value)} required /></label>
                <label><span>源地址</span><input value={sourceUrl} onChange={e => setSourceUrl(e.target.value)} placeholder="rtsp://, rtmp://, /dev/video0..." required /></label>
                <label><span>描述</span><textarea value={description} onChange={e => setDescription(e.target.value)} /></label>
              </div>
              <div className="form-section">
                <div className="form-section-title">NVR 绑定（可选）</div>
                <label><span>NVR 标识</span><input value={nvrId} onChange={e => setNvrId(e.target.value)} placeholder="例如 main-nvr" /></label>
                <label><span>通道号</span><input value={nvrChannel} onChange={e => setNvrChannel(e.target.value)} placeholder="例如 1" /></label>
                <label><span>Track ID</span><input value={nvrTrackId} onChange={e => setNvrTrackId(e.target.value)} placeholder="例如 101" /></label>
                <label><span>码流类型</span>
                  <select value={nvrStreamType} onChange={e => setNvrStreamType(e.target.value)}>
                    <option value="main">主码流</option>
                    <option value="sub">子码流</option>
                  </select>
                </label>
              </div>
              <div className="button-row modal-actions">
                <button type="submit" disabled={savingForm}>{savingForm ? '保存中...' : '保存'}</button>
                <button type="button" onClick={reset} disabled={savingForm}>取消</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {viewing && (
        <div className="modal-overlay" onClick={() => setViewing(null)}>
          <div className="modal modal-wide" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title">设备详情 - {viewing.name}</div>
              <button className="icon-btn" onClick={() => setViewing(null)}><X size={18} /></button>
            </div>
            <div className="device-detail">
              <div className="detail-preview">
                <VideoPlayer url={streamUrl(viewing.playbackUrl)} />
              </div>
              <div className="detail-tabs">
                <div className="detail-tab active">基础配置</div>
                <div className="detail-tab">视频配置</div>
                <div className="detail-tab">回放配置</div>
                <div className="detail-tab">抓图配置</div>
                <div className="detail-tab">设备能力</div>
              </div>
              <div className="detail-grid">
                <DetailRow label="设备ID" value={viewing.id} />
                <DetailRow label="设备名称" value={viewing.name} />
                <DetailRow label="所在区域" value={viewing.area || '未分配'} />
                <DetailRow label="接入协议" value={guessProtocol(viewing.sourceUrl)} />
                <DetailRow label="源地址" value={viewing.sourceUrl} />
                <DetailRow label="播放地址" value={viewing.playbackUrl} />
                <DetailRow label="设备编号" value="0001" />
                <DetailRow label="设备序列号" value={viewing.id.slice(0, 12).toUpperCase()} />
                <DetailRow label="密码强度" value={defaultPasswordStrength} />
                <DetailRow label="码流类型" value={viewing.nvrStreamType || 'main'} />
                <DetailRow label="状态" value={viewing.status} />
                <DetailRow label="创建时间" value={new Date(viewing.createdAt).toLocaleString()} />
                <DetailRow label="更新时间" value={new Date(viewing.updatedAt).toLocaleString()} />
                <DetailRow label="描述" value={viewing.description || '无'} fullWidth />
              </div>
            </div>
            <div className="button-row modal-actions">
              <button onClick={() => setViewing(null)}>关闭</button>
            </div>
          </div>
        </div>
      )}

      {showChannelConfig && selectedCamera && (
        <div className="modal-overlay" onClick={() => setShowChannelConfig(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-title">通道配置 - {selectedCamera.name}</div>
            <div className="channel-config">
              <p className="hint">配置通道参数，包含通道名称、码流、录像计划等。</p>
              <table>
                <thead><tr><th>通道号</th><th>通道名称</th><th>协议</th><th>主码流</th><th>子码流</th><th>状态</th></tr></thead>
                <tbody>
                  {[1, 2, 3, 4].map(n => (
                    <tr key={n}>
                      <td>{n}</td>
                      <td><input defaultValue={`通道 ${n}`} /></td>
                      <td>RTSP</td>
                      <td><span className="status running">在线</span></td>
                      <td><span className="status running">在线</span></td>
                      <td>
                        <button className="toggle-icon" title="启用"><Eye size={16} /></button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="button-row modal-actions">
              <button>保存配置</button>
              <button onClick={() => setShowChannelConfig(false)}>取消</button>
            </div>
          </div>
        </div>
      )}

      {showBatch && (
        <div className="modal-overlay" onClick={() => setShowBatch(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-title">批量导入设备</div>
            <div className="batch-import">
              <p className="hint">支持 CSV/JSON 格式批量导入设备配置。下载导入模板，按格式填写后上传。</p>
              <div className="button-row">
                <button><Download size={15} />下载模板</button>
                <button><FileText size={15} />查看格式说明</button>
              </div>
              <label className="file-box"><Upload size={17} /><span>选择 CSV/JSON 文件</span><input type="file" accept=".csv,.json" /></label>
            </div>
            <div className="button-row modal-actions">
              <button>开始导入</button>
              <button onClick={() => setShowBatch(false)}>取消</button>
            </div>
          </div>
        </div>
      )}

      {showDiscover && (
        <div className="modal-overlay" onClick={() => setShowDiscover(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-title">主动发现设备</div>
            <div className="discover-panel">
              <p className="hint">平台正在扫描局域网内的 ONVIF/RTSP 设备，可勾选发现到的设备添加到平台。</p>
              <div className="discover-controls">
                <label>扫描网段：<input defaultValue="192.168.1.0/24" /></label>
                <button><Radar size={15} />开始扫描</button>
              </div>
              <table>
                <thead><tr><th><input type="checkbox" /></th><th>IP地址</th><th>端口</th><th>协议</th><th>MAC地址</th><th>操作</th></tr></thead>
                <tbody>
                  {discoveredDevices.map((d, i) => (
                    <tr key={i}>
                      <td><input type="checkbox" /></td>
                      <td>{d.ip}</td>
                      <td>{d.port}</td>
                      <td>{d.protocol}</td>
                      <td>{d.mac}</td>
                      <td>
                        <button title="添加"><Plus size={14} /></button>
                        <button title="详情"><Eye size={14} /></button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="button-row modal-actions">
              <button>添加选中</button>
              <button onClick={() => setShowDiscover(false)}>关闭</button>
            </div>
          </div>
        </div>
      )}

      {showBatchConfig && (
        <div className="modal-overlay" onClick={() => setShowBatchConfig(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-title">批量配置设备能力</div>
            <div className="batch-config">
              <p className="hint">对多个设备进行统一的设备能力配置，如云台、报警输入、音频等。</p>
              <div className="capability-grid">
                {[
                  '云台控制', '预置点', '巡航轨迹', '雨刷控制', '灯光控制',
                  '音频输入', '音频输出', '报警输入', '报警输出',
                  '移动侦测', '视频遮挡', '区域入侵', '智能跟踪',
                ].map(cap => (
                  <label key={cap} className="checkbox-label">
                    <input type="checkbox" /> {cap}
                  </label>
                ))}
              </div>
            </div>
            <div className="button-row modal-actions">
              <button>应用到选中设备</button>
              <button onClick={() => setShowBatchConfig(false)}>取消</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function DetailRow({ label, value, fullWidth }: { label: string; value: string; fullWidth?: boolean }) {
  return (
    <div className={`detail-row ${fullWidth ? 'full-width' : ''}`}>
      <span className="detail-label">{label}</span>
      <span className="detail-value">{value}</span>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  return <span className={`status ${status.toLowerCase()}`}>{status}</span>;
}

function passwordStrengthClass(strength: '弱' | '中' | '强') {
  if (strength === '弱') {
    return 'pwd-weak';
  }
  if (strength === '强') {
    return 'pwd-strong';
  }
  return 'pwd-medium';
}

function guessProtocol(url: string): string {
  if (url.startsWith('rtsp://')) return 'RTSP';
  if (url.startsWith('rtmp://')) return 'RTMP';
  if (url.startsWith('http://') || url.startsWith('https://')) return 'HTTP';
  if (url.startsWith('/dev/video')) return '本地设备';
  return '未知';
}

function protocolFromUrl(url: string): string {
  if (url.startsWith('rtmp://')) return 'rtmp';
  if (url.startsWith('http://') || url.startsWith('https://')) return 'onvif';
  if (url.startsWith('/dev/video')) return 'rtsp';
  return 'rtsp';
}

function extractHost(url: string): string {
  try { return new URL(url).hostname; } catch { return ''; }
}

function extractPort(url: string): string {
  try { const p = new URL(url).port; return p || (url.startsWith('rtsp') ? '554' : ''); } catch { return ''; }
}
