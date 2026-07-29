import { Link } from 'react-router-dom';
import { useMemo, useState, type ReactNode } from 'react';
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  BellRing,
  Bot,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  CircleHelp,
  Clock3,
  Copy,
  Database,
  Edit3,
  Eye,
  Gauge,
  HardDrive,
  Image as ImageIcon,
  Layers3,
  ListChecks,
  Menu,
  Monitor,
  Plus,
  RefreshCw,
  Search,
  Server,
  SlidersHorizontal,
  Trash2,
  Upload,
  X,
} from 'lucide-react';

type EventLevel = '高' | '中' | '低';
type RunStatus = '运行中' | '暂停' | '连接失败';
type ModelStatus = '运行良好' | '连接异常' | '离线';

type EventInfo = {
  name: string;
  code: string;
  level: EventLevel;
  category: string;
  enabled: boolean;
  order: number;
};

type IngestionSource = {
  name: string;
  endpoint: string;
  eventTypes: string[];
  frequency: string;
  status: RunStatus;
  lastSync: string;
};

type DedupRule = {
  name: string;
  algorithm: string;
  strategy: string;
  params: string;
  enabled: boolean;
  effective?: boolean;
};

type SubscriptionTask = {
  id: number;
  name: string;
  type: 'mq' | 'http';
  address: string;
  enabled: boolean;
  desc: string;
};

type LargeModel = {
  name: string;
  status: ModelStatus;
  checkedAt: string;
  latency: string;
  availability: string;
  deployment: '云端服务' | '本地部署';
  concurrency: number;
};

type GpuServer = {
  ip: string;
  mn: string;
  status: '在线' | '离线';
  updatedAt: string;
};

const eventInfos: EventInfo[] = [
  { name: '家禽检测', code: 'FOWL_DETECTION', level: '低', category: '待完成', enabled: true, order: 25 },
  { name: '区域入侵', code: 'INTRUSION_DEC', level: '低', category: '安防事件', enabled: true, order: 24 },
  { name: '烟火识别', code: 'SMOKE', level: '低', category: '消防事件', enabled: true, order: 23 },
  { name: 'RK_周界入侵', code: 'RK_INTRUSION_DEC', level: '高', category: '安防事件', enabled: true, order: 22 },
  { name: '污水应急监控', code: 'PERSON_WADE', level: '低', category: '环境事件', enabled: true, order: 21 },
  { name: '睡岗', code: 'SLEEP', level: '低', category: '行为事件', enabled: true, order: 20 },
  { name: '离岗', code: 'LEAVE', level: '低', category: '行为事件', enabled: true, order: 19 },
  { name: 'RK_抽烟', code: 'RK_SMOKING', level: '中', category: '行为事件', enabled: true, order: 18 },
  { name: 'RK_物品占用通道', code: 'RK_OCCUPIED_AREA', level: '低', category: '安防事件', enabled: true, order: 17 },
  { name: '非机动车识别', code: 'NONVEHICLE', level: '低', category: '交通事件', enabled: true, order: 14 },
];

const ingestionSources: IngestionSource[] = [
  { name: '云边协同平台 - 边缘算法', endpoint: 'api.edge-cloud.com/v1/alerts', eventTypes: ['人员入侵', '车辆检测'], frequency: '每 5 分钟', status: '运行中', lastSync: '2024-01-15 14:30' },
  { name: '中心端布控算法平台', endpoint: 'center-control.gov.cn/api/events', eventTypes: ['烟火检测', '安全帽'], frequency: '实时推送', status: '运行中', lastSync: '2024-01-15 14:32' },
  { name: '下游业务系统 A', endpoint: 'business-system-a.com/webhook', eventTypes: ['区域入侵'], frequency: '每 10 分钟', status: '暂停', lastSync: '2024-01-15 12:00' },
  { name: '视频事件平台', endpoint: 'video-event.platform.cn/api', eventTypes: ['跌倒检测', '聚集检测'], frequency: '实时推送', status: '运行中', lastSync: '2024-01-15 14:31' },
  { name: '第三方告警服务', endpoint: 'third-party-alerts.io/v2', eventTypes: ['设备异常'], frequency: '每 30 分钟', status: '连接失败', lastSync: '2024-01-15 10:00' },
];

const dedupRules: DedupRule[] = [
  { name: '1221', algorithm: '测试图像过滤', strategy: '时间维度去重', params: '过滤时长 23.0m', enabled: true, effective: true },
  { name: '1221', algorithm: '测试图像过滤', strategy: '时间维度去重', params: '过滤时长 23.0m', enabled: true, effective: true },
  { name: '123', algorithm: '区域入侵', strategy: '时间维度去重', params: '过滤时长 2.0h', enabled: false },
  { name: '123', algorithm: '区域入侵', strategy: '时间维度去重', params: '过滤时长 10.0m', enabled: false },
  { name: '车辆违停算法过滤车辆违停', algorithm: '车辆违停乱放', strategy: '实时重叠图像去重', params: '相似度 0.95', enabled: true, effective: true },
  { name: '垃圾识别过滤', algorithm: '垃圾识别', strategy: '区间重叠图像去重', params: '过滤时长 2.0h  相似度 0.5', enabled: true, effective: true },
];

const subscriptionTasks: SubscriptionTask[] = [
  { id: 1, name: '安防推送', type: 'mq', address: 'anfang_topic', enabled: true, desc: '这里推送部分安防的事件' },
  { id: 2, name: '场景编排', type: 'http', address: 'http:123.123.123.132', enabled: false, desc: '-' },
  { id: 3, name: 'SXIN', type: 'mq', address: 'sin_topic', enabled: true, desc: '推给sxin' },
  { id: 4, name: '物业推送', type: 'http', address: 'http:234.243.234.324', enabled: false, desc: '-' },
];

const largeModels: LargeModel[] = [
  { name: '通义千问-Max', status: '运行良好', checkedAt: '2026-08-07 09:18:43', latency: '124ms', availability: '94.35%', deployment: '云端服务', concurrency: 5 },
  { name: '硅基流动-DeepSeek', status: '连接异常', checkedAt: '2026-08-07 09:18:43', latency: '124ms', availability: '94.35%', deployment: '云端服务', concurrency: 5 },
  { name: '本地私有化模型-Llama3', status: '运行良好', checkedAt: '2026-08-07 09:18:43', latency: '124ms', availability: '94.35%', deployment: '本地部署', concurrency: 5 },
  { name: '本地私有化模型-Qwen3', status: '离线', checkedAt: '2026-08-07 09:18:43', latency: '124ms', availability: '94.35%', deployment: '本地部署', concurrency: 5 },
  { name: '通义千问-Plus', status: '运行良好', checkedAt: '2026-08-07 09:18:43', latency: '124ms', availability: '94.35%', deployment: '云端服务', concurrency: 5 },
];

const gpuServers: GpuServer[] = [
  { ip: '192.168.1.100', mn: 'MN24010001', status: '在线', updatedAt: '2024-01-18 15:30:45' },
  { ip: '192.168.1.101', mn: 'MN24010002', status: '离线', updatedAt: '2024-01-18 14:15:30' },
  { ip: '192.168.1.102', mn: 'MN24010003', status: '在线', updatedAt: '2024-01-18 15:28:15' },
  { ip: '192.168.1.103', mn: 'MN 2401003', status: '在线', updatedAt: '2024-01-18 15:28:15' },
];

function PageHeader({ title, desc, action }: { title: string; desc: string; action?: ReactNode }) {
  return (
    <header className="topbar basic-topbar">
      <div>
        <h1>{title}</h1>
        <p>{desc}</p>
      </div>
      {action}
    </header>
  );
}

function StatusBadge({ status }: { status: RunStatus | ModelStatus | GpuServer['status'] }) {
  return <span className={`basic-status ${statusClass(status)}`}>{status}</span>;
}

function statusClass(status: RunStatus | ModelStatus | GpuServer['status']) {
  if (status === '运行中' || status === '运行良好' || status === '在线') return 'ok';
  if (status === '暂停' || status === '离线') return 'muted';
  return 'error';
}

function ToggleSwitch({ checked = true }: { checked?: boolean }) {
  const [active, setActive] = useState(checked);
  return (
    <button
      className={`basic-switch ${active ? 'active' : ''}`}
      onClick={() => setActive(value => !value)}
      type="button"
      aria-label={active ? '已启用' : '已停用'}
    >
      <span />
    </button>
  );
}

function Pagination() {
  return (
    <div className="basic-pagination">
      <button disabled type="button"><ChevronLeft size={15} /></button>
      <button className="active" type="button">1</button>
      <button type="button">2</button>
      <button type="button">3</button>
      <span>...</span>
      <button type="button">9</button>
      <select defaultValue="10"><option value="10">10条/页</option><option value="20">20条/页</option></select>
      <span>跳至</span>
      <input type="number" defaultValue={5} min={1} />
      <span>页</span>
    </div>
  );
}

function SectionTitle({ children }: { children: ReactNode }) {
  return <div className="basic-section-title">{children}</div>;
}

function ConfigEntry({ to, icon, title, desc }: { to: string; icon: ReactNode; title: string; desc: string }) {
  return (
    <Link className="basic-entry-card" to={to}>
      <span className="basic-entry-icon">{icon}</span>
      <div>
        <strong>{title}</strong>
        <span>{desc}</span>
      </div>
      <ArrowRight size={16} />
    </Link>
  );
}

function UploadTile({ label }: { label: string }) {
  const [fileName, setFileName] = useState('');
  return (
    <label className={`basic-upload-tile ${fileName ? 'has-file' : ''}`}>
      <Upload size={22} />
      <span>{fileName || label}</span>
      <input type="file" onChange={event => setFileName(event.target.files?.[0]?.name ?? '')} />
    </label>
  );
}

function JsonPreview() {
  return (
    <pre className="basic-json-preview">{`{
  "deviceId": "string",
  "deviceCode": "string",
  "deviceData": {
    "lightControlGridActivePower": {
      "id": null,
      "deviceId": "yunzhisheng89",
      "name": "灯控功率",
      "code": "lightControlGridActivePower",
      "dataType": "STRING",
      "value": {
        "value_real": "0",
        "value_format": "0",
        "value": "0"
      },
      "lastTime": "2023-02-17 16:01:19"
    }
  },
  "deviceStatus": "NORMAL",
  "warnMessages": []
}`}</pre>
  );
}

export function BasicConfigHome() {
  return (
    <>
      <PageHeader title="基础配置" desc="集中维护视频、事件、大模型和复用系统配置" />
      <section className="basic-home-grid">
        <ConfigEntry to="/basic-config/video" icon={<Monitor size={24} />} title="视频管理" desc="进入设备管理、实时预览、录像回放、电视墙和告警联动。" />
        <ConfigEntry to="/basic-config/events" icon={<BellRing size={24} />} title="事件配置" desc="配置事件信息、事件接入、事件去重和消息订阅。" />
        <ConfigEntry to="/basic-config/large-model" icon={<Bot size={24} />} title="大模型配置" desc="维护模型接入配置、运行状态、部署方式和资源监控。" />
      </section>
      <section className="basic-summary-grid">
        <div><span>启用事件</span><strong>{eventInfos.length}</strong></div>
        <div><span>告警数据源</span><strong>{ingestionSources.length}</strong></div>
        <div><span>去重规则</span><strong>{dedupRules.length}</strong></div>
        <div><span>大模型配置</span><strong>{largeModels.length}</strong></div>
      </section>
    </>
  );
}

export function BasicVideoConfigPage() {
  return (
    <>
      <PageHeader title="视频管理" desc="复用已有视频能力入口" />
      <section className="basic-home-grid">
        <ConfigEntry to="/devices" icon={<Database size={24} />} title="设备管理" desc="管理设备列表、新增设备、通道配置、批量添加与设备详情。" />
        <ConfigEntry to="/live" icon={<Monitor size={24} />} title="实时预览" desc="查看摄像机实时视频，多画面分屏与基础云台操作。" />
        <ConfigEntry to="/playback" icon={<Clock3 size={24} />} title="录像回放" desc="按设备和时间范围查看历史视频。" />
        <ConfigEntry to="/tvwall" icon={<Layers3 size={24} />} title="电视墙" desc="维护上墙布局和屏幕轮巡。" />
        <ConfigEntry to="/alarm" icon={<AlertCircle size={24} />} title="告警联动" desc="配置报警预案、模板、类型和事件订阅。" />
      </section>
    </>
  );
}

export function BasicEventConfigHome() {
  return (
    <>
      <PageHeader title="事件配置" desc="配置事件字典、接入、去重和消息订阅" />
      <section className="basic-home-grid">
        <ConfigEntry to="/basic-config/events/info" icon={<ListChecks size={24} />} title="事件信息配置" desc="复用能力仓事件字典，维护事件等级、状态、图标和排序。" />
        <ConfigEntry to="/basic-config/events/ingestion" icon={<Server size={24} />} title="事件接入" desc="管理外部告警数据源、接口地址、拉取方式和事件映射。" />
        <ConfigEntry to="/basic-config/events/dedup" icon={<SlidersHorizontal size={24} />} title="事件去重配置" desc="配置时间维度、区域重叠和实时图像相似度去重规则。" />
        <ConfigEntry to="/basic-config/events/subscriptions" icon={<BellRing size={24} />} title="消息订阅配置" desc="维护 MQ/HTTP 推送任务，查看推送日志。" />
      </section>
    </>
  );
}

export function EventInfoPage() {
  return (
    <>
      <PageHeader
        title="事件信息配置"
        desc="复用能力仓事件信息，维护事件名称、编码、等级和状态"
        action={<Link className="button-like omni-primary-btn" to="/basic-config/events/info/create"><Plus size={16} />新增</Link>}
      />
      <section className="panel basic-table-panel">
        <div className="basic-filter-row">
          <input placeholder="请输入名称" />
          <button type="button"><RefreshCw size={15} />重置</button>
          <button className="omni-primary-btn" type="button"><Search size={15} />查询</button>
        </div>
        <table>
          <thead>
            <tr><th>名称</th><th>编码</th><th>事件等级</th><th>事件分类</th><th>状态</th><th>图标</th><th>排序(倒序)</th><th>操作</th></tr>
          </thead>
          <tbody>
            {eventInfos.map(item => (
              <tr key={item.code}>
                <td>{item.name}</td>
                <td><code>{item.code}</code></td>
                <td>{item.level}</td>
                <td>{item.category}</td>
                <td><span className="basic-dot-status"><span />启用中</span></td>
                <td><span className="basic-event-icon"><ImageIcon size={18} /></span></td>
                <td>{item.order}⌄</td>
                <td className="actions"><button type="button">修改</button><button type="button">停用</button><button type="button">删除</button></td>
              </tr>
            ))}
          </tbody>
        </table>
        <Pagination />
      </section>
    </>
  );
}

export function EventInfoCreatePage() {
  return (
    <>
      <EventInfoPage />
      <div className="modal-overlay">
        <div className="modal basic-config-modal" onClick={event => event.stopPropagation()}>
          <div className="modal-header">
            <div className="modal-title">新增配置信息</div>
            <Link className="icon-btn" to="/basic-config/events/info"><X size={18} /></Link>
          </div>
          <div className="basic-modal-grid">
            <label><span>* 事件名称</span><input placeholder="请输入内容" /></label>
            <label><span>* 事件编码</span><input placeholder="请输入内容" /></label>
            <label><span>事件等级</span><select defaultValue="低"><option>低</option><option>中</option><option>高</option></select></label>
            <label><span>标注方式</span><select defaultValue="10"><option>10</option><option>20</option><option>30</option></select></label>
            <label><span>是否启用</span><ToggleSwitch /></label>
            <label><span>事件图标</span><UploadTile label="上传" /></label>
            <div className="basic-attribute-editor">
              <span>事件属性</span>
              <div>
                <div><input placeholder="confidence" /><span>:</span><input placeholder="置信度" /><button type="button">⊖</button></div>
                <div><input placeholder="type" /><span>:</span><input placeholder="类型" /><button type="button">⊖</button></div>
                <button type="button"><Plus size={14} />添加属性</button>
              </div>
            </div>
          </div>
          <div className="button-row modal-actions"><Link className="button-like" to="/basic-config/events/info">取消</Link><button className="omni-primary-btn" type="button">保存</button></div>
        </div>
      </div>
    </>
  );
}

export function EventIngestionPage() {
  return (
    <>
      <PageHeader
        title="事件接入"
        desc="管理外部告警数据源、接口地址、拉取方式和同步状态"
        action={<Link className="button-like omni-primary-btn" to="/basic-config/events/ingestion/alarm-source"><Plus size={16} />新增数据源</Link>}
      />
      <section className="panel basic-table-panel">
        <div className="section-head"><strong>告警数据源列表</strong><div className="search-bar"><Search size={16} /><input placeholder="搜索数据源..." /></div></div>
        <table>
          <thead><tr><th>数据源名称</th><th>接口地址</th><th>事件类型</th><th>拉取频率</th><th>状态</th><th>最后同步</th><th>操作</th></tr></thead>
          <tbody>
            {ingestionSources.map(item => (
              <tr key={item.name}>
                <td><span className={`basic-source-dot ${statusClass(item.status)}`} />{item.name}</td>
                <td><code>{item.endpoint}</code></td>
                <td><div className="basic-tag-row">{item.eventTypes.map(type => <span key={type}>{type}</span>)}</div></td>
                <td>{item.frequency}</td>
                <td><StatusBadge status={item.status} /></td>
                <td>{item.lastSync}</td>
                <td className="actions"><button type="button">编辑</button><button type="button">日志</button><button type="button">删除</button></td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="basic-table-footer">显示 1-5 共 8 条记录 <Pagination /></div>
      </section>
    </>
  );
}

export function AlarmSourceCreatePage() {
  return (
    <>
      <EventIngestionPage />
      <div className="modal-overlay">
        <div className="modal basic-source-modal" onClick={event => event.stopPropagation()}>
          <div className="modal-header"><div className="modal-title">新增告警数据源</div><Link className="icon-btn" to="/basic-config/events/ingestion"><X size={18} /></Link></div>
          <div className="basic-source-form">
            <label><span>数据源名称*</span><input placeholder="请输入数据源名称" /></label>
            <label><span>启停状态</span><select><option>启用</option><option>停用</option></select></label>
            <label className="wide"><span>接口地址*</span><input placeholder="https://api.example.com/v1/alerts" /></label>
            <label><span>拉取方式</span><select><option>定时拉取</option><option>实时推送</option></select></label>
            <label><span>拉取频率</span><select><option>每 5 分钟</option><option>每 10 分钟</option><option>每 30 分钟</option></select></label>
            <div className="basic-mapping-box">
              <span>事件映射关系</span>
              <div><input placeholder="外部事件编码" /><ArrowRight size={15} /><select><option>选择标准事件类型</option><option>人员入侵</option><option>烟火检测</option></select><button type="button"><Trash2 size={14} /></button></div>
              <button type="button"><Plus size={14} />添加映射规则</button>
            </div>
            <label className="wide"><span>描述</span><textarea placeholder="请输入数据源描述（可选）" /></label>
          </div>
          <div className="button-row modal-actions"><Link className="button-like" to="/basic-config/events/ingestion">取消</Link><button className="omni-primary-btn" type="button">保存配置</button></div>
        </div>
      </div>
    </>
  );
}

export function EventDedupPage() {
  return (
    <>
      <PageHeader title="事件去重配置" desc="维护事件去重规则、执行策略和规则日志" />
      <section className="basic-dedup-grid">
        <Link className="basic-rule-create" to="/basic-config/events/dedup/create"><Plus size={24} /><span>点击创建事件过滤规则</span></Link>
        {dedupRules.concat(dedupRules, dedupRules.slice(0, 5)).map((rule, index) => (
          <article className="basic-rule-card" key={`${rule.name}-${index}`}>
            <div className="section-head">
              <strong>{rule.name}</strong>
              <div className="basic-rule-menu"><Menu size={16} /><div><Link to="/basic-config/events/dedup/logs/detail">详情</Link><Link to="/basic-config/events/dedup/logs">日志</Link><Link to="/basic-config/events/dedup/create">编辑</Link><button type="button">删除</button></div></div>
            </div>
            <span>{rule.effective && <em>已生效</em>}</span>
            <p>{rule.strategy}：{rule.params}</p>
            <ToggleSwitch checked={rule.enabled} />
          </article>
        ))}
      </section>
    </>
  );
}

export function DedupCreatePage() {
  return (
    <>
      <PageHeader title="新增去重规则" desc="配置事件属性、关联算法、摄像头范围和执行策略" action={<Link className="button-like" to="/basic-config/events/dedup"><ArrowLeft size={15} />返回</Link>} />
      <section className="basic-form-page">
        <div className="panel">
          <SectionTitle>事件属性</SectionTitle>
          <div className="basic-form-grid">
            <label><span>* 名称</span><input defaultValue="去重" /></label>
            <label><span>* 关联算法</span><select defaultValue="区域入侵"><option>区域入侵</option><option>车辆违停</option><option>垃圾识别</option></select></label>
            <label><span>* 摄像头</span><input placeholder="搜索摄像头" /></label>
            <label className="checkbox-line"><input type="checkbox" defaultChecked />全选</label>
            <label className="checkbox-line"><input type="checkbox" defaultChecked />test01</label>
          </div>
        </div>
        <div className="panel">
          <SectionTitle>执行策略</SectionTitle>
          <div className="template-tabs basic-tabs"><button className="active" type="button">时间维度去重</button><button type="button">区间重叠图像去重</button><button type="button">实时重叠图像去重</button></div>
          <div className="basic-strategy-grid">
            <label><span>* 时间长度</span><div className="basic-input-addon"><input /><em>分钟</em></div></label>
            <label><span>* 相似度</span><input /></label>
          </div>
        </div>
        <div className="panel">
          <SectionTitle>备注说明</SectionTitle>
          <textarea placeholder="请填写说明，最多不超过200字" />
        </div>
        <div className="button-row basic-page-actions"><button type="button">重置</button><button className="omni-primary-btn" type="button">提交</button><Link className="button-like" to="/basic-config/events/dedup">返回</Link></div>
      </section>
    </>
  );
}

function DedupLogsModal({ detail = false }: { detail?: boolean }) {
  return (
    <div className="modal-overlay">
      <div className={`modal ${detail ? 'basic-log-detail-modal' : 'basic-log-modal'}`} onClick={event => event.stopPropagation()}>
        {detail ? (
          <>
            <div className="modal-header"><div className="modal-title"><ArrowLeft size={16} />事件规则详情</div><Link className="icon-btn" to="/basic-config/events/dedup"><X size={18} /></Link></div>
            <div className="basic-detail-grid">
              <span>规则名称：车辆违停算法过滤车辆违停算法过滤</span><span>规则状态：已生效</span><span>关联算法：车辆违停乱放</span>
              <span>过滤类型：实时重叠图像去重</span><span>相似度：0.95</span><span>设备名称：室外-B1北侧道路2</span>
            </div>
            <SectionTitle>过滤详情</SectionTitle>
            <div className="basic-filter-preview"><em>已保留</em><b>相似度 95</b><strong>2024-09-27 13:33:46</strong></div>
          </>
        ) : (
          <>
            <div className="modal-header"><div className="modal-title">规则日志</div><Link className="icon-btn" to="/basic-config/events/dedup"><X size={18} /></Link></div>
            <div className="basic-log-filters">
              <select><option>事件类型</option></select><input placeholder="规则名称" /><select><option>设备名称</option></select><select><option>规则类型</option></select><select><option>执行状态</option></select><input placeholder="开始日期  ->  结束日期" /><button type="button">重置</button><button className="omni-primary-btn" type="button">查询</button>
            </div>
            <table><thead><tr><th>设备名称</th><th>规则名称</th><th>算法类型</th><th>规则类型</th><th>执行状态</th><th>过滤数量</th><th>执行时间</th><th>操作</th></tr></thead><tbody>{Array.from({ length: 10 }).map((_, index) => <tr key={index}><td>室外-B1北侧道路2</td><td>测试图像过滤</td><td>车辆违停乱放</td><td>实时重叠图像去重</td><td>{index > 5 ? '执行失败' : '执行成功'}</td><td>{index > 5 ? 0 : 1}</td><td>2024-09-27 15:{57 - index}:34</td><td><Link to="/basic-config/events/dedup/logs/detail">详情</Link></td></tr>)}</tbody></table>
            <Pagination />
          </>
        )}
      </div>
    </div>
  );
}

export function DedupLogsPage({ detail = false }: { detail?: boolean }) {
  return (
    <>
      <EventDedupPage />
      <DedupLogsModal detail={detail} />
    </>
  );
}

export function SubscriptionsPage() {
  return (
    <>
      <PageHeader title="消息订阅配置" desc="管理事件推送任务、推送地址、状态和推送日志" />
      <section className="panel basic-table-panel">
        <div className="basic-filter-row subscriptions">
          <label><span>搜索</span><input placeholder="请输入" /></label>
          <label><span>推送类型</span><select defaultValue=""><option value="">请选择</option><option>mq</option><option>http</option></select></label>
          <button className="omni-primary-btn" type="button"><Search size={15} />查询</button>
          <button type="button">重置</button>
          <button className="basic-danger-btn" type="button">一键删除</button>
          <Link className="button-like omni-primary-btn" to="/basic-config/events/subscriptions/create-mq"><Plus size={15} />新增推送</Link>
        </div>
        <table>
          <thead><tr><th><input type="checkbox" /></th><th>序号</th><th>任务名称</th><th>推送类型 <CircleHelp size={14} /></th><th>推送地址 <CircleHelp size={14} /></th><th>状态</th><th>描述</th><th>操作</th></tr></thead>
          <tbody>{subscriptionTasks.map(item => <tr key={item.id}><td><input type="checkbox" /></td><td>{item.id}</td><td>{item.name}</td><td>{item.type}</td><td>{item.address}</td><td><ToggleSwitch checked={item.enabled} /></td><td>{item.desc}</td><td className="actions"><Link to="/basic-config/events/subscriptions/push-logs-latest">推送日志</Link><Link to={item.type === 'mq' ? '/basic-config/events/subscriptions/create-mq' : '/basic-config/events/subscriptions/create-http'}>编辑</Link><button type="button">删除</button></td></tr>)}</tbody>
        </table>
        <Pagination />
      </section>
    </>
  );
}

function PushLogsModal({ tab }: { tab: 'latest' | 'history' }) {
  return (
    <div className="modal-overlay">
      <div className="modal basic-push-log-modal" onClick={event => event.stopPropagation()}>
        <div className="modal-header"><div className="modal-title">推送日志</div><Link className="icon-btn" to="/basic-config/events/subscriptions"><X size={18} /></Link></div>
        <div className="template-tabs basic-log-tabs"><Link className={`button-like ${tab === 'latest' ? 'active-toggle' : ''}`} to="/basic-config/events/subscriptions/push-logs-latest">最新推送</Link><Link className={`button-like ${tab === 'history' ? 'active-toggle' : ''}`} to="/basic-config/events/subscriptions/push-logs-history">历史推送</Link></div>
        {tab === 'latest' ? (
          <div className="basic-push-latest"><p>推送任务名称：公交车数据推送任务</p><p>最新推送时间：--</p><p>推送结果：--</p><div className="section-head"><span>推送内容：</span><button type="button"><Copy size={15} />复制示例</button></div><JsonPreview /></div>
        ) : (
          <div className="basic-push-history"><div className="basic-log-filters"><select><option>推送结果</option></select><input placeholder="开始日期  至  结束日期" /><button className="omni-primary-btn" type="button">查询</button></div><table><thead><tr><th>序号</th><th>推送任务名称</th><th>推送结果</th><th>失败信息</th><th>推送内容</th><th>推送时间</th></tr></thead><tbody><tr><td colSpan={6} className="empty-cell">暂无数据</td></tr></tbody></table><Pagination /></div>
        )}
      </div>
    </div>
  );
}

export function PushLogsPage({ tab }: { tab: 'latest' | 'history' }) {
  return (
    <>
      <SubscriptionsPage />
      <PushLogsModal tab={tab} />
    </>
  );
}

export function PushTaskFormPage({ type }: { type: 'mq' | 'http' }) {
  return (
    <>
      <div className="basic-form-titlebar"><Link to="/basic-config/events/subscriptions"><ArrowLeft size={15} />返回</Link><h1>新增推送任务</h1><div className="button-row"><Link className="button-like" to="/basic-config/events/subscriptions">取消</Link><button className="omni-primary-btn" type="button">确认</button></div></div>
      <section className="basic-form-page">
        <div className="panel">
          <SectionTitle>基础信息</SectionTitle>
          <div className="basic-push-form-grid">
            <label><span>* 推送任务名称</span><input placeholder="请输入推送任务名称" /></label>
            <label><span>* 推送类型</span><div className="basic-radio-row"><label><input type="radio" checked={type === 'mq'} readOnly />MQ</label><label><input type="radio" checked={type === 'http'} readOnly />HTTP</label></div></label>
            {type === 'mq' ? (
              <>
                <label><span>* MQ地址</span><input placeholder="请输入MQ地址" /></label>
                <label><span>MQ地址用户名</span><input placeholder="请输入MQ地址用户名" /></label>
                <label><span>MQ地址密码</span><input placeholder="请输入MQ地址密码" /></label>
              </>
            ) : (
              <label><span>* TOKEN</span><div className="basic-input-button"><input placeholder="请输入TOKEN" /><button type="button">自动生成</button></div></label>
            )}
            <label><span>* 推送地址</span><input placeholder="请输入推送地址" /></label>
            <label><span>* 推送记录过期时间</span><div className="basic-stepper"><button type="button">−</button><input defaultValue="30" /><button type="button">＋</button><em>天</em></div></label>
            <label><span>描述</span><textarea placeholder="请输入描述" /></label>
          </div>
        </div>
        <div className="panel">
          <SectionTitle>推送内容</SectionTitle>
          <div className="basic-push-content"><label><span>* 事件来源</span><input /></label><label><span>* 事件类型</span><input /></label></div>
        </div>
      </section>
    </>
  );
}

export function LargeModelPage() {
  return (
    <>
      <PageHeader title="大模型配置" desc="维护大模型接入配置、运行状态和部署方式" action={<Link className="button-like omni-primary-btn" to="/basic-config/large-model/create"><Plus size={16} />新增配置</Link>} />
      <section className="basic-filter-row basic-model-filter"><label><span>搜索</span><input placeholder="请输入名称" /></label><label><span>状态</span><input /></label><label><span>部署方式</span><input /></label></section>
      <section className="basic-model-grid">
        {largeModels.map(model => <ModelCard key={model.name} model={model} />)}
      </section>
      <Pagination />
    </>
  );
}

function ModelCard({ model }: { model: LargeModel }) {
  return (
    <article className="basic-model-card">
      <div className="section-head"><strong>{model.name}</strong><div className="button-row"><Link to="/basic-config/large-model/edit" title="编辑"><Edit3 size={18} /></Link><button title="删除" type="button"><Trash2 size={18} /></button></div></div>
      <StatusBadge status={model.status} />
      <p>检测时间：{model.checkedAt}</p>
      <div className="basic-model-line"><span><Clock3 size={14} />平均时延</span><b>{model.latency}</b></div>
      <div className="basic-progress"><span className="basic-progress-22" /></div>
      <div className="basic-model-line"><span><SlidersHorizontal size={14} />可用率（近24h）</span><b>{model.availability}</b></div>
      <div className="basic-progress"><span className="basic-progress-94" /></div>
      <footer><span>部署方式：{model.deployment}</span><span>并发限制：{model.concurrency}</span></footer>
    </article>
  );
}

function ModelDrawer({ mode }: { mode: 'create' | 'edit' }) {
  return (
    <div className="slide-drawer-overlay">
      <aside className="basic-model-drawer" onClick={event => event.stopPropagation()}>
        <h2>{mode === 'create' ? '新增配置' : '编辑配置'}</h2>
        <SectionTitle>基础配置</SectionTitle>
        <div className="basic-drawer-form">
          <label><span>* 模型名称</span><input /></label>
          <label><span>* 接口地址</span><input /></label>
          <label><span>* API Key</span><div className="basic-input-icon"><input /><Eye size={18} /></div></label>
          <label><span>* 部署方式</span><div className="basic-radio-row"><label><input type="radio" defaultChecked />云端部署</label><label><input type="radio" />本地部署</label></div></label>
        </div>
        <SectionTitle>高级配置</SectionTitle>
        <div className="basic-drawer-form">
          <label><span>超时时间（秒）<b>30s</b></span><input /></label>
          <small>请求的最大等待时间，建议范围：10 - 120s</small>
          <label><span>最大并发数 <b>5</b></span><input /></label>
          <small>同时处理的最大请求数量</small>
          <label><span>温度参数（Temperature）<b>0.7</b></span><input type="range" min="0" max="1" step="0.1" defaultValue="0.7" /></label>
          <small>控制输出的随机性：0 表示最稳定，1 表示最富创造力</small>
          <label><span>最大输出长度（Tokens）<b>2048</b></span><input /></label>
          <small>模型生成的最大 Token 数量</small>
          <label><span>视频帧数（FPS）<b>1</b></span><input /></label>
          <small>视频理解任务中的采样帧率</small>
        </div>
        <div className="button-row basic-drawer-actions"><Link className="button-like" to="/basic-config/large-model">取消</Link><button className="omni-primary-btn" type="button">保存</button></div>
      </aside>
    </div>
  );
}

export function LargeModelDrawerPage({ mode }: { mode: 'create' | 'edit' }) {
  return (
    <>
      <LargeModelPage />
      <ModelDrawer mode={mode} />
    </>
  );
}

export function LargeModelResourcesPage() {
  const summary = useMemo(() => [
    { label: '总设备数', value: '4', icon: <Server size={22} /> },
    { label: '在线设备', value: '3', icon: <CheckCircle2 size={22} /> },
    { label: '离线设备', value: '1', icon: <AlertCircle size={22} /> },
    { label: '总GPU数', value: '8', icon: <HardDrive size={22} /> },
    { label: '繁忙 GPU', value: '4', icon: <Gauge size={22} /> },
  ], []);
  return (
    <>
      <PageHeader title="资源监控" desc="查看大模型推理资源、服务器和 GPU 使用状态" action={<button className="omni-primary-btn" type="button"><RefreshCw size={16} />手动同步</button>} />
      <section className="basic-resource-summary">{summary.map(item => <div key={item.label}><div><span>{item.label}</span><strong>{item.value}</strong></div>{item.icon}</div>)}</section>
      <section className="panel basic-resource-table">
        <table><thead><tr><th></th><th>服务器 IP</th><th>设备 MN 号</th><th>状态</th><th>最后更新时间</th></tr></thead><tbody>{gpuServers.map((server, index) => <tr key={server.ip} className={index === 0 ? 'expanded' : ''}><td><ChevronRight size={16} /></td><td>{server.ip}</td><td>{server.mn}</td><td><StatusBadge status={server.status} /></td><td>{server.updatedAt}</td></tr>)}</tbody></table>
        <div className="basic-gpu-detail">
          <GpuCard name="NVIDIA A100" gpu="GPU-0" busy />
          <GpuCard name="NVIDIA A100" gpu="GPU-1" />
        </div>
      </section>
    </>
  );
}

function GpuCard({ name, gpu, busy = false }: { name: string; gpu: string; busy?: boolean }) {
  return (
    <article className="basic-gpu-card">
      <div className="section-head"><strong>{name}</strong><StatusBadge status={busy ? '暂停' : '运行中'} /></div>
      <span>{gpu}</span>
      <div><span>算力使用率</span><b>{busy ? 75 : 45}%</b></div>
      <div className="basic-progress"><span className={busy ? 'basic-progress-75' : 'basic-progress-45'} /></div>
      <p>显存 <b>{busy ? '40GB / 80GB' : '35GB / 80GB'}</b></p>
      <p>温度 <b>{busy ? '65°C' : '62°C'}</b></p>
      <p>功耗 <b>{busy ? '57.4w' : '57.3w'}</b></p>
      <button className="omni-primary-btn" type="button">查看详情</button>
    </article>
  );
}
