import { useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRight,
  ChevronLeft,
  Download,
  Edit3,
  FileCheck2,
  FileImage,
  FileVideo,
  ListChecks,
  Plus,
  RefreshCw,
  Search,
  Trash2,
  Upload,
  X,
} from 'lucide-react';

type ReviewTaskStatus = '已完成' | '进行中' | '待处理';
type EventStatus = '有效' | '复核过滤' | '去重过滤' | '人工过滤';
type EventLevel = '高' | '中' | '低';

type ReviewTask = {
  id: string;
  eventType: string;
  createdAt: string;
  status: ReviewTaskStatus;
};

type ReviewType = {
  id: number;
  name: string;
  code: string;
  prompt: string;
  note: string;
  injected: boolean;
  updatedAt: string;
};

type VisualEvent = {
  id: string;
  source: string;
  type: string;
  status: EventStatus;
  level: EventLevel;
  place: string;
  happenedAt: string;
  reportedAt: string;
  note: string;
};

const reviewTasks: ReviewTask[] = [
  { id: '#TM-2847', eventType: '人员入侵检测', createdAt: '2026-01-15 14:32:08', status: '已完成' },
  { id: '#TM-2846', eventType: '车辆违停识别', createdAt: '2026-01-15 13:14:17', status: '进行中' },
  { id: '#TM-2845', eventType: '烟火检测告警', createdAt: '2026-01-15 11:48:36', status: '待处理' },
  { id: '#TM-2844', eventType: '安全帽佩戴检测', createdAt: '2026-01-15 10:22:21', status: '已完成' },
  { id: '#TM-2843', eventType: '区域入侵检测', createdAt: '2026-01-15 09:15:12', status: '已完成' },
];

const reviewTypes: ReviewType[] = [
  { id: 1, name: '抽烟', code: 'SMOKING', prompt: '你是园区安防监控事件复检助手，请判断画面中是否存在抽烟行为。', note: '抽烟', injected: true, updatedAt: '2026-04-27 10:05:40' },
  { id: 2, name: '垃圾识别', code: 'RUBBISH', prompt: '你是园区安防监控事件复检助手，请识别画面中的垃圾堆放情况。', note: '-', injected: false, updatedAt: '2026-04-13 16:21:10' },
  { id: 3, name: '车辆违停', code: 'PARKING', prompt: '你是园区安防监控事件复检助手，请判断车辆是否处于违停区域。', note: '-', injected: false, updatedAt: '2026-04-10 14:31:29' },
  { id: 4, name: '人员入侵', code: 'PERSON_INTRUSION', prompt: '你是园区安防监控事件复检助手，请判断是否存在人员入侵。', note: '过滤保安、保洁、施工', injected: true, updatedAt: '2026-04-24 17:06:32' },
  { id: 6, name: '周界入侵', code: 'PERIMETER_INTRUSION', prompt: '你是园区安防监控事件复检助手，请复核周界入侵告警。', note: '过滤保安、保洁、施工', injected: true, updatedAt: '2026-04-09 16:56:50' },
  { id: 7, name: '电动车识别', code: 'EBIKE_DETECTION', prompt: '你是园区安防监控事件复检助手，请识别是否存在电动车。', note: '-', injected: false, updatedAt: '2026-04-10 16:32:45' },
  { id: 8, name: '老鼠监测', code: 'RAT_DETECTION', prompt: '你是园区安防监控事件复检助手，请判断是否出现鼠类目标。', note: '-', injected: true, updatedAt: '2026-04-14 09:48:19' },
  { id: 9, name: '烟火监测', code: 'SMOKE_FIRE_DETECTION', prompt: '你是园区安防监控事件复检助手，请判断是否出现烟雾或火光。', note: '-', injected: true, updatedAt: '2026-04-27 16:08:33' },
  { id: 10, name: '起雾检测', code: 'FOG_DETECTION', prompt: '你是园区安防监控事件复检助手，请判断画面是否受雾气影响。', note: '-', injected: false, updatedAt: '2026-04-27 16:07:20' },
];

const visualEvents: VisualEvent[] = [
  { id: 'EV-4301', source: '云边协同平台', type: '吸烟事件', status: '有效', level: '高', place: '园区A1-103', happenedAt: '2026-04-30 19:03:21', reportedAt: '2026-04-30 19:03:27', note: '暂无说明' },
  { id: 'EV-4302', source: '中心推理平台', type: '人员入侵', status: '复核过滤', level: '中', place: '实验室504', happenedAt: '2026-04-30 17:32:11', reportedAt: '2026-04-30 17:32:41', note: '这里是大模型复核后的批注' },
  { id: 'EV-4303', source: '第三方系统', type: '火情检测', status: '去重过滤', level: '低', place: '园区B消防通道', happenedAt: '2026-04-30 16:22:11', reportedAt: '2026-04-30 16:22:12', note: '这里是人工校验后的批注' },
  { id: 'EV-4304', source: '第三方系统', type: '垃圾识别', status: '人工过滤', level: '高', place: '大厅', happenedAt: '2026-04-30 12:42:11', reportedAt: '2026-04-30 12:42:11', note: '这里是大模型复核后的批注' },
  { id: 'EV-4305', source: '云边协同平台', type: '违停识别', status: '有效', level: '中', place: '园区北侧道路', happenedAt: '2026-04-30 11:35:51', reportedAt: '2026-04-30 11:35:51', note: '这里是大模型复核后的批注' },
];

const chartBars = [34, 86, 61, 72, 39, 25, 64, 14, 72, 64, 52, 34];
const flowSteps = [
  { label: '事件接入', time: '2026-04-30 10:33:27' },
  { label: '事件去重通过', time: '2026-04-30 10:33:30' },
  { label: '事件复核通过', time: '2026-04-30 10:33:35' },
  { label: '人工核验拦截', time: '2026-05-01 17:33:35' },
  { label: '人工核验通过', time: '2026-05-21 11:23:36' },
];

function ReviewHeader({ title, desc, action }: { title: string; desc: string; action?: ReactNode }) {
  return (
    <header className="topbar">
      <div>
        <h1>{title}</h1>
        <p>{desc}</p>
      </div>
      {action}
    </header>
  );
}

function ReviewStatusBadge({ status }: { status: ReviewTaskStatus | EventStatus }) {
  return <span className={`review-status ${statusClass(status)}`}>{status}</span>;
}

function statusClass(status: ReviewTaskStatus | EventStatus) {
  if (status === '已完成' || status === '有效') return 'done';
  if (status === '进行中') return 'running';
  if (status === '待处理') return 'pending';
  return 'muted';
}

function UploadBox({ label, icon }: { label: string; icon: ReactNode }) {
  const [fileName, setFileName] = useState('');
  return (
    <label className={`review-upload-box ${fileName ? 'has-file' : ''}`}>
      {icon}
      <strong>{fileName || label}</strong>
      <span>点击选择文件，仅用于前端展示</span>
      <input type="file" onChange={event => setFileName(event.target.files?.[0]?.name ?? '')} />
    </label>
  );
}

function ReviewPagination() {
  return (
    <div className="review-pagination">
      <button type="button" disabled><ChevronLeft size={15} /></button>
      <button type="button" className="active">1</button>
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

export function OmniReviewHome() {
  return (
    <>
      <ReviewHeader
        title="万物核"
        desc="异常事件复查、人工补核、离线分析与视觉事件统计"
        action={<Link className="button-like omni-primary-btn" to="/omni-review/tasks/create"><Upload size={16} />上传复核任务</Link>}
      />
      <section className="review-home-grid">
        <Link className="review-entry" to="/omni-review/tasks">
          <FileCheck2 size={24} />
          <div><strong>任务管理</strong><span>查看复核任务，按任务 ID、事件类型、状态和创建时间筛选。</span></div>
          <ArrowRight size={16} />
        </Link>
        <Link className="review-entry" to="/omni-review/types">
          <ListChecks size={24} />
          <div><strong>复核类型管理</strong><span>维护算法名称、算法编码、提示词和注入事件字段。</span></div>
          <ArrowRight size={16} />
        </Link>
      </section>
      <section className="review-kpi-grid">
        <div><span>接入事件数</span><strong>9999</strong></div>
        <div><span>过滤事件数</span><strong>999</strong></div>
        <div><span>待处理任务</span><strong>17</strong></div>
        <div><span>复核类型</span><strong>{reviewTypes.length}</strong></div>
      </section>
      <section className="panel">
        <div className="section-head">
          <strong>最近复核任务</strong>
          <Link className="button-like" to="/omni-review/tasks">查看全部</Link>
        </div>
        <ReviewTaskTable compact />
      </section>
    </>
  );
}

function ReviewTaskTable({ compact = false }: { compact?: boolean }) {
  return (
    <table className="review-task-table">
      <thead>
        <tr>
          {!compact && <th><input type="checkbox" /></th>}
          <th>任务ID</th>
          <th>事件类型</th>
          <th>创建时间</th>
          <th>任务状态</th>
        </tr>
      </thead>
      <tbody>
        {reviewTasks.map(task => (
          <tr key={task.id}>
            {!compact && <td><input type="checkbox" /></td>}
            <td>{task.id}</td>
            <td>{task.eventType}</td>
            <td>{task.createdAt}</td>
            <td><ReviewStatusBadge status={task.status} /></td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function ReviewTasksPage() {
  return (
    <>
      <ReviewHeader
        title="任务管理"
        desc="异常事件复查、人工补核、离线分析与效果测试"
        action={<Link className="button-like omni-primary-btn" to="/omni-review/tasks/create"><Upload size={16} />上传复核任务</Link>}
      />
      <section className="panel review-page-panel">
        <div className="review-tabbar"><button className="active" type="button">手动复核任务</button></div>
        <div className="review-filter-row">
          <label><span>搜索</span><input placeholder="搜索任务ID、事件类型..." /></label>
          <label><span>状态</span><select defaultValue=""><option value="">请选择</option><option>已完成</option><option>进行中</option><option>待处理</option></select></label>
          <label className="wide"><span>创建时间</span><input defaultValue="2024-9-10  ->  2024-11-24" /></label>
          <button type="button" className="omni-primary-btn"><Search size={15} />查询</button>
          <button type="button"><RefreshCw size={15} />重置</button>
        </div>
        <ReviewTaskTable />
        <div className="review-table-footer">
          <span>显示 1-5 共 127 条记录</span>
          <ReviewPagination />
        </div>
      </section>
    </>
  );
}

export function ReviewTaskCreatePage() {
  return (
    <>
      <ReviewTasksPage />
      <div className="modal-overlay">
        <div className="modal review-modal" onClick={event => event.stopPropagation()}>
          <div className="modal-header">
            <div className="modal-title">事件判断</div>
            <Link className="icon-btn" to="/omni-review/tasks"><X size={18} /></Link>
          </div>
          <div className="review-form-grid">
            <label className="form-label required"><span>事件编码</span><select defaultValue=""><option value="">请选择事件编码</option><option>PERSON_INTRUSION</option><option>SMOKING</option><option>PARKING</option></select></label>
            <div className="review-upload-section">
              <div className="review-upload-label"><span>*</span>图片</div>
              <div>
                <div className="button-row"><button className="active-toggle" type="button">批量上传</button><button type="button">图片地址</button></div>
                <UploadBox label="上传图片" icon={<FileImage size={24} />} />
              </div>
            </div>
            <div className="review-upload-section">
              <div className="review-upload-label">视频</div>
              <div>
                <div className="button-row"><button className="active-toggle" type="button">批量上传</button><button type="button">视频地址</button></div>
                <UploadBox label="上传视频" icon={<FileVideo size={24} />} />
              </div>
            </div>
          </div>
          <div className="button-row modal-actions">
            <Link className="button-like" to="/omni-review/tasks">取消</Link>
            <button className="omni-primary-btn" type="button">确定</button>
          </div>
        </div>
      </div>
    </>
  );
}

export function ReviewTypesPage() {
  const [editingType, setEditingType] = useState<ReviewType | null>(null);

  return (
    <>
      <ReviewHeader
        title="复核类型管理"
        desc="维护事件复核算法、提示词、备注和注入事件字段"
        action={<Link className="button-like omni-primary-btn" to="/omni-review/types/create"><Plus size={16} />新建</Link>}
      />
      <section className="panel review-page-panel">
        <table>
          <thead>
            <tr><th>ID</th><th>算法名称</th><th>算法编码</th><th>提示词</th><th>备注</th><th>注入事件字段</th><th>更新时间</th><th>操作</th></tr>
          </thead>
          <tbody>
            {reviewTypes.map(item => (
              <tr key={item.id}>
                <td>{item.id}</td>
                <td>{item.name}</td>
                <td><code>{item.code}</code></td>
                <td>{item.prompt}</td>
                <td>{item.note}</td>
                <td>{item.injected ? <span className="review-field-tag">识别对象</span> : '-'}</td>
                <td>{item.updatedAt}</td>
                <td className="actions">
                  <button title="编辑" type="button" onClick={() => setEditingType(item)}><Edit3 size={14} /></button>
                  <button title="删除" type="button"><Trash2 size={14} /></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      {editingType && (
        <div className="modal-overlay" onClick={() => setEditingType(null)}>
          <div className="modal review-type-modal" onClick={event => event.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title">编辑算法</div>
              <button className="icon-btn" type="button" onClick={() => setEditingType(null)}><X size={18} /></button>
            </div>
            <div className="review-type-form">
              <label className="form-label required"><span>算法名称</span><input defaultValue={editingType.name} /></label>
              <label className="form-label required"><span>算法编码</span><input defaultValue={editingType.code} /></label>
              <label className="form-label required tall"><span>提示词</span><textarea defaultValue={editingType.prompt} /></label>
              <label className="form-label"><span>备注</span><textarea defaultValue={editingType.note === '-' ? '' : editingType.note} /></label>
              <label className="form-label"><span>注入事件字段</span><select defaultValue={editingType.injected ? 'yes' : 'no'}><option value="yes">识别对象</option><option value="no">不注入</option></select></label>
            </div>
            <div className="button-row modal-actions">
              <button className="button-like" type="button" onClick={() => setEditingType(null)}>取消</button>
              <button className="omni-primary-btn" type="button" onClick={() => setEditingType(null)}>确定</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export function ReviewTypeCreatePage() {
  return (
    <>
      <ReviewTypesPage />
      <div className="modal-overlay">
        <div className="modal review-type-modal" onClick={event => event.stopPropagation()}>
          <div className="modal-header">
            <div className="modal-title">新增算法</div>
            <Link className="icon-btn" to="/omni-review/types"><X size={18} /></Link>
          </div>
          <div className="review-type-form">
            <label className="form-label required"><span>算法名称</span><input placeholder="请输入算法名称" /></label>
            <label className="form-label required tall"><span>提示词</span><textarea placeholder="请输入提示词" /></label>
            <label className="form-label"><span>备注</span><textarea placeholder="请输入备注" /></label>
          </div>
          <div className="button-row modal-actions">
            <Link className="button-like" to="/omni-review/types">取消</Link>
            <button className="omni-primary-btn" type="button">确定</button>
          </div>
        </div>
      </div>
    </>
  );
}

function StatNumberCard({ label, value }: { label: string; value: string }) {
  return <div className="review-stat-card"><span>{label}</span><strong>{value}</strong></div>;
}

function BarChart({ title, compact = false }: { title: string; compact?: boolean }) {
  return (
    <section className={`panel review-chart-card ${compact ? 'compact' : ''}`}>
      <div className="section-head">
        <strong>{title}</strong>
        <div className="button-row review-periods"><button type="button">年</button><button type="button">月</button><button type="button">日</button></div>
      </div>
      <div className="review-bars">
        {chartBars.map((height, index) => (
          <div key={index} className="review-bar-item">
            <span className={`review-bar-height-${height}`} />
            <em>模块{index + 1}</em>
          </div>
        ))}
      </div>
    </section>
  );
}

export function VisualEventStatisticsPage() {
  return (
    <>
      <ReviewHeader title="事件统计" desc="视觉事件接入、过滤、有效事件与高发事件统计" />
      <div className="review-stats-layout">
        <section className="panel review-stat-group">
          <div className="section-head"><strong>总事件统计</strong><input className="review-mini-input" /></div>
          <div className="review-stat-row">
            <StatNumberCard label="接入事件数" value="9999" />
            <StatNumberCard label="过滤事件数" value="999" />
          </div>
        </section>
        <section className="panel review-stat-group wide">
          <div className="panel-title">今日各类型事件统计</div>
          <div className="review-stat-row four">
            <StatNumberCard label="有效事件" value="9" />
            <StatNumberCard label="研判后事件" value="89" />
            <StatNumberCard label="过滤后事件" value="259" />
            <StatNumberCard label="原始事件" value="999" />
          </div>
        </section>
        <BarChart title="有效事件发生情况" />
        <BarChart title="高发事件" />
        <section className="panel review-index-card">
          <div className="panel-title">万物核指标</div>
          <div className="review-index-filter">
            <strong>时间范围</strong>
            <input placeholder="开始时间" />
            <span>-</span>
            <input placeholder="结束时间" />
            <button className="omni-primary-btn" type="button">查看</button>
            <button type="button">重置</button>
          </div>
          <div className="review-index-content">
            <div className="review-square-metric"><span>事件复核率</span><small>万物核过滤事件占比</small><b>25</b></div>
            <div className="review-square-metric"><span>复核准确率</span><small>万物核复核正确的占比</small><b>25</b></div>
            <BarChart title="过滤事件类型统计" compact />
          </div>
        </section>
      </div>
    </>
  );
}

function EventFilterBar() {
  return (
    <div className="review-filter-row visual">
      <label><span>事件来源</span><input placeholder="请输入" /></label>
      <label><span>事件类型</span><select defaultValue=""><option value="">请选择</option><option>吸烟事件</option><option>人员入侵</option><option>火情检测</option></select></label>
      <label><span>事件状态</span><input /></label>
      <label><span>发生地点</span><input placeholder="请输入" /></label>
      <label className="wide"><span>发生时间范围</span><input defaultValue="2024-1-1  ->  2024-12-31" /></label>
      <label className="wide"><span>上报时间范围</span><input defaultValue="2024-1-1  ->  2024-12-31" /></label>
      <button className="omni-primary-btn" type="button"><Search size={15} />查询</button>
      <button type="button"><RefreshCw size={15} />重置</button>
    </div>
  );
}

function VisualEventTable({ showAction = true }: { showAction?: boolean }) {
  return (
    <table>
      <thead>
        <tr>
          <th><input type="checkbox" /></th>
          <th>事件来源</th>
          <th>事件类型</th>
          <th>事件状态</th>
          <th>事件等级</th>
          <th>发生地点</th>
          <th>发生时间</th>
          <th>上报时间</th>
          <th>事件图片</th>
          <th>事件说明</th>
          {showAction && <th>操作</th>}
        </tr>
      </thead>
      <tbody>
        {visualEvents.map(event => (
          <tr key={event.id}>
            <td><input type="checkbox" /></td>
            <td>{event.source}</td>
            <td>{event.type}</td>
            <td><ReviewStatusBadge status={event.status} /></td>
            <td><span className={`review-level ${event.level}`}>{event.level}</span></td>
            <td>{event.place}</td>
            <td>{event.happenedAt}</td>
            <td>{event.reportedAt}</td>
            <td><span className="review-image-placeholder"><FileImage size={15} /></span></td>
            <td>{event.note}</td>
            {showAction && <td><Link to="/omni-review/visual-events/list/actions">状态详情</Link></td>}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function VisualEventListPage() {
  return (
    <>
      <ReviewHeader title="事件列表" desc="查询视觉事件、导出选中事件并查看状态流转详情" />
      <section className="panel review-page-panel">
        <EventFilterBar />
        <button className="omni-primary-btn review-export-btn" type="button"><Download size={15} />导出选中事件</button>
        <VisualEventTable />
        <ReviewPagination />
      </section>
    </>
  );
}

export function VisualEventActionsPage() {
  return (
    <>
      <ReviewHeader title="事件列表" desc="查看事件状态详情并进行人工核验" />
      <div className="review-detail-layout">
        <section className="panel review-page-panel">
          <EventFilterBar />
          <button className="omni-primary-btn review-export-btn" type="button"><Download size={15} />导出选中事件</button>
          <VisualEventTable showAction={false} />
          <ReviewPagination />
        </section>
        <aside className="review-detail-drawer">
          <h2>状态详情</h2>
          <h3>流转流程</h3>
          <div className="review-flow">
            {flowSteps.map(step => (
              <div key={step.label} className="review-flow-step">
                <span />
                <strong>{step.label}</strong>
                <time>{step.time}</time>
              </div>
            ))}
          </div>
          <h3>人工核验</h3>
          <div className="review-manual-form">
            <label><span>事件状态</span><div className="button-row"><label><input type="radio" name="event-status" defaultChecked />有效</label><label><input type="radio" name="event-status" />无效</label></div></label>
            <label><span>事件说明</span><textarea /></label>
          </div>
          <div className="button-row review-drawer-actions">
            <Link className="button-like" to="/omni-review/visual-events/list">取消</Link>
            <button className="omni-primary-btn" type="button">提交</button>
          </div>
        </aside>
      </div>
    </>
  );
}
