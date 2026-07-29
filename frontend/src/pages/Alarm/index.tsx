import { useState } from 'react';
import {
  Plus, Pencil, Trash2, Search, Clock, Video, Sparkles, ToggleLeft, ToggleRight, RefreshCw,
  Volume2, DoorOpen, Cpu, Image as ImageIcon, Mic, Crosshair, Save, X,
  Copy, AlertCircle,
} from 'lucide-react';

type ActionType = 'record' | 'wall' | 'video' | 'snapshot' | 'sound' | 'access' | 'algorithm' | 'alarmout' | 'devicesound' | 'preset';

const ACTION_TYPES: { type: ActionType; label: string; icon: React.ReactNode; desc: string }[] = [
  { type: 'record', label: '录像', icon: <Video size={16} />, desc: '从设备树中选择视频通道，设置预录时间和录像时间' },
  { type: 'wall', label: '上墙', icon: <Sparkles size={16} />, desc: '关联报警上墙功能，选择上墙任务和特效模板' },
  { type: 'video', label: '视频', icon: <PlayCircle size={16} />, desc: '选择联动视频模板，触发时叠加视频模板播放' },
  { type: 'snapshot', label: '抓拍', icon: <ImageIcon size={16} />, desc: '触发时抓拍事发时的图片' },
  { type: 'sound', label: '声音', icon: <Volume2 size={16} />, desc: '播放报警声音文件，配置音量和播放模式' },
  { type: 'access', label: '门禁', icon: <DoorOpen size={16} />, desc: '触发门禁操作' },
  { type: 'algorithm', label: '算法', icon: <Cpu size={16} />, desc: '启动算法任务，配置算法动作参数' },
  { type: 'alarmout', label: '报警输出', icon: <AlertCircle size={16} />, desc: '选择报警输出设备，设置消警时间' },
  { type: 'devicesound', label: '设备声音', icon: <Mic size={16} />, desc: '音频播放设备、播放的音频和播放次数' },
  { type: 'preset', label: '预置点', icon: <Crosshair size={16} />, desc: '选择视频通道的预置点，触发时转到预置点' },
];

function PlayCircle(props: { size?: number }) {
  return <svg width={props.size || 16} height={props.size || 16} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polygon points="10 8 16 12 10 16 10 8"/></svg>;
}

export function AlarmPlans() {
  const [showForm, setShowForm] = useState(false);
  const [enabledActions, setEnabledActions] = useState<Record<ActionType, boolean>>({
    record: true, wall: true, video: true, snapshot: true, sound: false,
    access: false, algorithm: false, alarmout: false, devicesound: false, preset: false,
  });

  const plans = [
    { id: '1', name: '正门入侵预案', enabled: true, alarmType: '区域入侵', cameras: 3, updatedAt: '2026-06-20' },
    { id: '2', name: '停车场告警预案', enabled: true, alarmType: '车辆检测', cameras: 2, updatedAt: '2026-06-19' },
    { id: '3', name: '办公楼火警预案', enabled: false, alarmType: '火灾报警', cameras: 5, updatedAt: '2026-06-18' },
  ];

  return (
    <>
      <header className="topbar">
        <div><h1>告警联动</h1><p>报警预案配置与管理</p></div>
        <button onClick={() => setShowForm(true)}><Plus size={16} />新建预案</button>
      </header>

      <div className="alarm-sub-tabs">
        <a href="/alarm" className="active">报警预案</a>
        <a href="/alarm/templates">预案模板</a>
        <a href="/alarm/types">报警类型</a>
        <a href="/alarm/subscriptions">事件订阅</a>
        <a href="/alarm/business">业务类型</a>
      </div>

      <div className="toolbar-row">
        <div className="search-bar">
          <Search size={16} />
          <input placeholder="搜索预案名称..." />
        </div>
        <button>批量删除</button>
      </div>

      <div className="panel">
        <table>
          <thead><tr><th>预案名称</th><th>报警类型</th><th>关联摄像头</th><th>状态</th><th>更新时间</th><th>操作</th></tr></thead>
          <tbody>
            {plans.map(plan => (
              <tr key={plan.id}>
                <td>{plan.name}</td>
                <td>{plan.alarmType}</td>
                <td>{plan.cameras} 个</td>
                <td>
                  <button className="toggle-icon" onClick={() => {}}>
                    {plan.enabled ? <ToggleRight size={20} className="toggle-icon-on" /> : <ToggleLeft size={20} className="toggle-icon-off" />}
                  </button>
                </td>
                <td>{plan.updatedAt}</td>
                <td className="actions">
                  <button title="编辑"><Pencil size={14} /></button>
                  <button title="复制"><Copy size={14} /></button>
                  <button title="删除"><Trash2 size={14} /></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal modal-x-wide" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title">新建报警预案</div>
              <button className="icon-btn" onClick={() => setShowForm(false)}><X size={18} /></button>
            </div>
            <div className="alarm-form">
              <div className="form-section">
                <div className="form-section-title">报警信息</div>
                <label><span>预案名称</span><input placeholder="预案名称" /></label>
                <label><span>生效时段</span>
                  <select><option>全时段</option><option>工作日 08:00-18:00</option><option>自定义</option></select>
                </label>
                <label><span>报警类型</span>
                  <select>
                    <option>区域入侵</option>
                    <option>越界检测</option>
                    <option>人群聚集</option>
                    <option>车辆违停</option>
                  </select>
                </label>
                <label><span>报警源</span>
                  <select><option>全部摄像头</option><option>选择摄像头...</option></select>
                </label>
              </div>
              <div className="form-section">
                <div className="form-section-title">联动动作</div>
                <div className="action-types">
                  {ACTION_TYPES.map(at => (
                    <label key={at.type} className={`action-type-card ${enabledActions[at.type] ? 'active' : ''}`}>
                      <input
                        type="checkbox"
                        checked={enabledActions[at.type]}
                        onChange={e => setEnabledActions(prev => ({ ...prev, [at.type]: e.target.checked }))}
                      />
                      <span className="action-icon">{at.icon}</span>
                      <div>
                        <strong>{at.label}</strong>
                        <span>{at.desc}</span>
                      </div>
                    </label>
                  ))}
                </div>
                {enabledActions.record && (
                  <div className="action-detail">
                    <strong>录像参数</strong>
                    <label><span>视频通道</span><input placeholder="选择通道" /></label>
                    <label><span>预录时间</span><input type="number" defaultValue="10" />秒</label>
                    <label><span>录像时间</span><input type="number" defaultValue="30" />秒</label>
                    <label className="checkbox-label"><input type="checkbox" defaultChecked />使用辅码流</label>
                  </div>
                )}
                {enabledActions.wall && (
                  <div className="action-detail">
                    <strong>上墙任务</strong>
                    <label><span>选择上墙任务</span><select><option>大门入侵上墙</option><option>停车场告警上墙</option></select></label>
                    <label><span>上墙特效模板</span><select><option>默认模板</option><option>紧急模板</option></select></label>
                  </div>
                )}
                {enabledActions.video && (
                  <div className="action-detail">
                    <strong>视频联动</strong>
                    <label><span>视频通道</span><input placeholder="选择通道" /></label>
                    <label><span>联动视频模板</span><select><option>默认模板</option></select></label>
                    <label><span>停留时间</span><input type="number" defaultValue="30" />秒</label>
                  </div>
                )}
                {enabledActions.sound && (
                  <div className="action-detail">
                    <strong>声音联动</strong>
                    <label><span>声音文件</span><input placeholder="选择声音文件" /></label>
                    <label><span>音量</span><input type="range" min="0" max="100" defaultValue="80" /></label>
                    <label><span>播放模式</span><select><option>单次</option><option>循环</option></select></label>
                  </div>
                )}
                {enabledActions.preset && (
                  <div className="action-detail">
                    <strong>预置点联动</strong>
                    <label><span>视频通道</span><input placeholder="选择通道" /></label>
                    <label><span>预置点</span><select><option>P1</option><option>P2</option><option>P3</option></select></label>
                  </div>
                )}
                <button className="action-copy-btn"><Copy size={14} />复制此报警类型的联动动作到其他类型</button>
              </div>
              <div className="form-section">
                <div className="form-section-title">查看权限</div>
                <label><span>可见范围</span>
                  <select><option>全部用户</option><option>按部门</option><option>按角色</option></select>
                </label>
              </div>
            </div>
            <div className="button-row modal-actions">
              <button><Save size={14} />保存</button>
              <button onClick={() => setShowForm(false)}>取消</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export function AlarmTemplates() {
  const [activeTab, setActiveTab] = useState<'time' | 'video' | 'effect'>('time');
  const [showForm, setShowForm] = useState(false);

  const tables: Record<string, { title: string; items: { name: string; description: string }[] }> = {
    time: {
      title: '生效时段模板',
      items: [
        { name: '全时段', description: '00:00-23:59 每天' },
        { name: '工作日', description: '周一至周五 08:00-18:00' },
        { name: '双休日', description: '周六至周日 全天' },
        { name: '夜间时段', description: '22:00-06:00 每天' },
      ],
    },
    video: {
      title: '联动视频模板',
      items: [
        { name: '默认模板', description: '提示内容：告警区域' },
        { name: '红色警告模板', description: '红色 24px 文字，右上角' },
        { name: '滚动字幕', description: '黄色滚动字幕 16px' },
      ],
    },
    effect: {
      title: '上墙特效模板',
      items: [
        { name: '默认模板', description: '边框闪烁' },
        { name: '紧急模板', description: '红色边框 + 闪烁文字' },
        { name: '低调模板', description: '无闪烁，半透明边框' },
      ],
    },
  };

  const current = tables[activeTab];

  return (
    <>
      <header className="topbar"><div><h1>告警联动</h1><p>模板配置与管理</p></div></header>

      <div className="alarm-sub-tabs">
        <a href="/alarm">报警预案</a>
        <a href="/alarm/templates" className="active">预案模板</a>
        <a href="/alarm/types">报警类型</a>
        <a href="/alarm/subscriptions">事件订阅</a>
        <a href="/alarm/business">业务类型</a>
      </div>

      <div className="template-tabs">
        <button className={activeTab === 'time' ? 'active' : ''} onClick={() => setActiveTab('time')}>
          <Clock size={15} />生效时段
        </button>
        <button className={activeTab === 'video' ? 'active' : ''} onClick={() => setActiveTab('video')}>
          <Video size={15} />联动视频
        </button>
        <button className={activeTab === 'effect' ? 'active' : ''} onClick={() => setActiveTab('effect')}>
          <Sparkles size={15} />上墙特效
        </button>
      </div>

      <div className="toolbar-row">
        <div className="panel-title">{current.title}</div>
        <button onClick={() => setShowForm(true)}><Plus size={16} />新建</button>
      </div>

      <div className="panel">
        <table>
          <thead><tr><th>模板名称</th><th>描述</th><th>使用状态</th><th>操作</th></tr></thead>
          <tbody>
            {current.items.map((item, i) => (
              <tr key={i}>
                <td>{item.name}</td>
                <td>{item.description}</td>
                <td><span className={`status ${i === 0 ? 'running' : 'stopped'}`}>{i === 0 ? '默认' : '未使用'}</span></td>
                <td className="actions">
                  <button title="编辑"><Pencil size={14} /></button>
                  <button title="删除"><Trash2 size={14} /></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-title">新建{activeTab === 'time' ? '生效时段' : activeTab === 'video' ? '联动视频' : '上墙特效'}模板</div>
            <div className="device-form">
              <label><span>模板名称</span><input placeholder="模板名称" /></label>
              {activeTab === 'time' && (
                <>
                  <label><span>模板类型</span>
                    <select><option>单时间段</option><option>循环时间段</option></select>
                  </label>
                  <label><span>开始时间</span><input type="time" defaultValue="08:00" /></label>
                  <label><span>结束时间</span><input type="time" defaultValue="18:00" /></label>
                  <div>
                    <span className="form-section-title">重复日期</span>
                    <div className="weekday-picker">
                      {['一', '二', '三', '四', '五', '六', '日'].map(d => (
                        <label key={d} className="checkbox-label">
                          <input type="checkbox" defaultChecked={['一', '二', '三', '四', '五'].includes(d)} />周{d}
                        </label>
                      ))}
                    </div>
                  </div>
                </>
              )}
              {activeTab === 'video' && (
                <>
                  <label><span>提示内容</span><textarea placeholder="提示内容" /></label>
                  <label><span>字体大小</span><select><option>12</option><option>14</option><option>16</option><option>18</option><option>24</option></select></label>
                  <label><span>字体颜色</span><input type="color" defaultValue="#ff0000" /></label>
                  <label><span>提示位置</span>
                    <select><option>左上</option><option>右上</option><option>左下</option><option>右下</option><option>居中</option></select>
                  </label>
                </>
              )}
              {activeTab === 'effect' && (
                <>
                  <label className="checkbox-label"><input type="checkbox" /> 文字特效（滚动）</label>
                  <label className="checkbox-label"><input type="checkbox" /> 闪烁特效</label>
                  <label className="checkbox-label"><input type="checkbox" /> 边框特效</label>
                </>
              )}
            </div>
            <div className="button-row modal-actions">
              <button>保存</button>
              <button onClick={() => setShowForm(false)}>取消</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export function AlarmTypes() {
  const types = [
    { id: '1', name: '区域入侵', level: '中级', sourceType: '摄像头', interval: 30, enabled: true },
    { id: '2', name: '越界检测', level: '高级', sourceType: '摄像头', interval: 30, enabled: true },
    { id: '3', name: '人群聚集', level: '中级', sourceType: '摄像头', interval: 60, enabled: true },
    { id: '4', name: '车辆违停', level: '低级', sourceType: '摄像头', interval: 120, enabled: false },
    { id: '5', name: '火灾报警', level: '紧急', sourceType: '烟感设备', interval: 10, enabled: true },
    { id: '6', name: '门禁异常', level: '中级', sourceType: '门禁设备', interval: 30, enabled: true },
  ];

  return (
    <>
      <header className="topbar"><div><h1>告警联动</h1><p>报警类型配置</p></div></header>

      <div className="alarm-sub-tabs">
        <a href="/alarm">报警预案</a>
        <a href="/alarm/templates">预案模板</a>
        <a href="/alarm/types" className="active">报警类型</a>
        <a href="/alarm/subscriptions">事件订阅</a>
        <a href="/alarm/business">业务类型</a>
      </div>

      <div className="toolbar-row">
        <div className="search-bar"><Search size={16} /><input placeholder="搜索类型名称或等级..." /></div>
        <div className="button-row">
          <button>批量开启</button>
          <button>批量关闭</button>
          <button><Plus size={16} />新建类型</button>
        </div>
      </div>

      <div className="panel">
        <table>
          <thead><tr><th>类型编码</th><th>类型名称</th><th>报警等级</th><th>报警源类型</th><th>报警时间间隔(s)</th><th>状态</th><th>操作</th></tr></thead>
          <tbody>
            {types.map(t => (
              <tr key={t.id}>
                <td>ALT-{t.id.padStart(3, '0')}</td>
                <td>{t.name}</td>
                <td><span className={`alarm-level level-${t.level === '紧急' ? 'critical' : t.level === '高级' ? 'high' : t.level === '中级' ? 'medium' : 'low'}`}>{t.level}</span></td>
                <td>{t.sourceType}</td>
                <td>{t.interval}</td>
                <td>
                  <button className="toggle-icon">
                    {t.enabled ? <ToggleRight size={20} className="toggle-icon-on" /> : <ToggleLeft size={20} className="toggle-icon-off" />}
                  </button>
                </td>
                <td className="actions">
                  <button title="编辑"><Pencil size={14} /></button>
                  <button title="删除"><Trash2 size={14} /></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

export function EventSubscriptions() {
  const subs = [
    { id: '1', eventCode: 'FACE_MATCH', alarmType: '人脸匹配', status: '已订阅' },
    { id: '2', eventCode: 'INTRUSION', alarmType: '区域入侵', status: '已订阅' },
    { id: '3', eventCode: 'PARKING', alarmType: '车辆违停', status: '订阅失败' },
  ];

  return (
    <>
      <header className="topbar"><div><h1>告警联动</h1><p>事件订阅配置</p></div></header>

      <div className="alarm-sub-tabs">
        <a href="/alarm">报警预案</a>
        <a href="/alarm/templates">预案模板</a>
        <a href="/alarm/types">报警类型</a>
        <a href="/alarm/subscriptions" className="active">事件订阅</a>
        <a href="/alarm/business">业务类型</a>
      </div>

      <div className="toolbar-row">
        <div className="search-bar"><Search size={16} /><input placeholder="搜索事件编码或报警类型..." /></div>
        <button><Plus size={16} />新增订阅</button>
      </div>

      <div className="panel">
        <table>
          <thead><tr><th>事件编码</th><th>报警类型</th><th>注册状态</th><th>操作</th></tr></thead>
          <tbody>
            {subs.map(s => (
              <tr key={s.id}>
                <td>{s.eventCode}</td>
                <td>{s.alarmType}</td>
                <td><span className={`status ${s.status === '已订阅' ? 'running' : 'stopped'}`}>{s.status}</span></td>
                <td className="actions">
                  <button title="编辑"><Pencil size={14} /></button>
                  {s.status === '订阅失败' && <button title="重试"><RefreshCw size={14} /></button>}
                  <button title="删除"><Trash2 size={14} /></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

export function AlarmBusiness() {
  const [showForm, setShowForm] = useState(false);
  const businessTypes = [
    { id: '1', name: '安全防范', alarmTypes: ['区域入侵', '越界检测', '门禁异常'], builtIn: true },
    { id: '2', name: '交通管理', alarmTypes: ['车辆违停', '车流统计'], builtIn: true },
    { id: '3', name: '消防安全', alarmTypes: ['火灾报警', '烟雾检测'], builtIn: false },
    { id: '4', name: '人员管控', alarmTypes: ['人群聚集', '人脸匹配'], builtIn: false },
  ];

  return (
    <>
      <header className="topbar"><div><h1>告警联动</h1><p>业务类型管理</p></div></header>

      <div className="alarm-sub-tabs">
        <a href="/alarm">报警预案</a>
        <a href="/alarm/templates">预案模板</a>
        <a href="/alarm/types">报警类型</a>
        <a href="/alarm/subscriptions">事件订阅</a>
        <a href="/alarm/business" className="active">业务类型</a>
      </div>

      <p className="hint">业务类型是报警类型的二级分类，业务方根据此业务类型进行一组报警类型的数据查询。可对报警类型进行自由组合，组成所需的业务类型，系统自带的业务类型无法删除。</p>

      <div className="toolbar-row">
        <div className="search-bar"><Search size={16} /><input placeholder="搜索业务类型名称..." /></div>
        <button onClick={() => setShowForm(true)}><Plus size={16} />新建业务类型</button>
      </div>

      <div className="panel">
        <table>
          <thead><tr><th>业务类型名称</th><th>包含的报警类型</th><th>类型属性</th><th>操作</th></tr></thead>
          <tbody>
            {businessTypes.map(bt => (
              <tr key={bt.id}>
                <td>{bt.name}</td>
                <td>
                  {bt.alarmTypes.map(at => <span key={at} className="tag">{at}</span>)}
                </td>
                <td><span className={`status ${bt.builtIn ? 'running' : 'available'}`}>{bt.builtIn ? '系统内置' : '自定义'}</span></td>
                <td className="actions">
                  <button title="编辑"><Pencil size={14} /></button>
                  {!bt.builtIn && <button title="删除"><Trash2 size={14} /></button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-title">新建业务类型</div>
            <div className="device-form">
              <label><span>业务类型名称</span><input placeholder="例如：安全防范" /></label>
              <label><span>描述</span><textarea placeholder="业务类型描述" /></label>
              <div>
                <span className="form-section-title">选择报警类型（可多选）</span>
                <div className="alarm-type-selector">
                  {['区域入侵', '越界检测', '人群聚集', '车辆违停', '火灾报警', '门禁异常', '人脸匹配'].map(t => (
                    <label key={t} className="checkbox-label">
                      <input type="checkbox" />{t}
                    </label>
                  ))}
                </div>
              </div>
            </div>
            <div className="button-row modal-actions">
              <button>保存</button>
              <button onClick={() => setShowForm(false)}>取消</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
