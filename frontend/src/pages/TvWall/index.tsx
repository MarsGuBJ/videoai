import { useState } from 'react';
import {
  Settings, Monitor, Play, Plus, Trash2, Keyboard, Bell, LayoutTemplate, Layers,
} from 'lucide-react';

type WallCell = { id: string; cameraName?: string; decoder?: string };

type Tab = 'config' | 'control' | 'template' | 'alarm' | 'keyboard' | 'splicer';

function tvwallGridClass(cols: number, rows: number) {
  return `tvwall-cols-${cols} tvwall-rows-${rows}`;
}

export function TvWall() {
  const [activeTab, setActiveTab] = useState<Tab>('config');
  const [splicerCols, setSplicerCols] = useState(3);
  const [splicerRows, setSplicerRows] = useState(2);
  const [wallCols, setWallCols] = useState(3);
  const [wallRows, setWallRows] = useState(2);
  const [editMode, setEditMode] = useState(false);
  const [decoderMode, setDecoderMode] = useState(false);

  const wallCells: WallCell[] = Array.from({ length: wallCols * wallRows }, (_, i) => ({
    id: `cell-${i}`,
    cameraName: i === 0 ? '大门入口' : i === 1 ? '停车场' : undefined,
  }));

  const splicerCells: WallCell[] = Array.from({ length: splicerCols * splicerRows }, (_, i) => ({
    id: `sp-${i}`,
    cameraName: i === 0 ? '大门入口' : undefined,
    decoder: ['HDMI-1', 'HDMI-2', 'HDMI-3', 'HDMI-4', 'HDMI-5', 'HDMI-6'][i],
  }));

  return (
    <>
      <header className="topbar">
        <div><h1>电视墙</h1><p>电视墙配置与上墙控制</p></div>
        <div className="button-row">
          {activeTab === 'config' && (
            <>
              <button onClick={() => setEditMode(!editMode)}>
                <Settings size={16} />{editMode ? '完成配置' : '配置电视墙'}
              </button>
              <button onClick={() => setDecoderMode(true)}>
                <Monitor size={16} />解码通道绑定
              </button>
            </>
          )}
        </div>
      </header>

      <div className="tvwall-tabs">
        <button className={activeTab === 'config' ? 'active' : ''} onClick={() => setActiveTab('config')}>
          <Monitor size={14} />电视墙配置
        </button>
        <button className={activeTab === 'splicer' ? 'active' : ''} onClick={() => setActiveTab('splicer')}>
          <Layers size={14} />拼控墙配置
        </button>
        <button className={activeTab === 'template' ? 'active' : ''} onClick={() => setActiveTab('template')}>
          <LayoutTemplate size={14} />上墙模板
        </button>
        <button className={activeTab === 'control' ? 'active' : ''} onClick={() => setActiveTab('control')}>
          <Play size={14} />上墙控制
        </button>
        <button className={activeTab === 'alarm' ? 'active' : ''} onClick={() => setActiveTab('alarm')}>
          <Bell size={14} />报警上墙
        </button>
        <button className={activeTab === 'keyboard' ? 'active' : ''} onClick={() => setActiveTab('keyboard')}>
          <Keyboard size={14} />网络键盘
        </button>
      </div>

      {activeTab === 'config' && (
        <div className="tvwall-config">
          {editMode && (
            <div className="tvwall-size-control">
              <label>列：<select value={wallCols} onChange={e => setWallCols(Number(e.target.value))}>
                {[1, 2, 3, 4, 5, 6].map(n => <option key={n} value={n}>{n}</option>)}
              </select></label>
              <label>行：<select value={wallRows} onChange={e => setWallRows(Number(e.target.value))}>
                {[1, 2, 3, 4].map(n => <option key={n} value={n}>{n}</option>)}
              </select></label>
              <span className="tvwall-size-info">{wallCols}×{wallRows} = {wallCols * wallRows} 窗口</span>
            </div>
          )}

          <div className={`tvwall-grid ${tvwallGridClass(wallCols, wallRows)}`}>
            {wallCells.map(cell => (
              <div key={cell.id} className={`tvwall-cell ${editMode ? 'editing' : ''} ${cell.cameraName ? 'bound' : ''}`}>
                {editMode ? (
                  <>
                    <div className="tvwall-cell-empty">
                      <Plus size={20} />
                      <span>{cell.cameraName || '绑定信号源'}</span>
                    </div>
                    <button className="tvwall-cell-remove"><Trash2 size={14} /></button>
                  </>
                ) : (
                  <>
                    {cell.cameraName ? (
                      <>
                        <div className="tvwall-cell-video"><Play size={24} /></div>
                        <div className="tvwall-cell-label">{cell.cameraName}</div>
                      </>
                    ) : (
                      <div className="tvwall-cell-empty">空闲</div>
                    )}
                  </>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'splicer' && (
        <div className="tvwall-config">
          <div className="tvwall-size-control">
            <label>输出列：<select value={splicerCols} onChange={e => setSplicerCols(Number(e.target.value))}>
              {[1, 2, 3, 4].map(n => <option key={n} value={n}>{n}</option>)}
            </select></label>
            <label>输出行：<select value={splicerRows} onChange={e => setSplicerRows(Number(e.target.value))}>
              {[1, 2, 3].map(n => <option key={n} value={n}>{n}</option>)}
            </select></label>
            <span className="tvwall-size-info">{splicerCols}×{splicerRows} 拼控输出</span>
          </div>
          <div className={`tvwall-grid ${tvwallGridClass(splicerCols, splicerRows)}`}>
            {splicerCells.map(cell => (
              <div key={cell.id} className={`tvwall-cell ${cell.cameraName ? 'bound' : ''}`}>
                <div className="tvwall-cell-decoder">{cell.decoder}</div>
                {cell.cameraName ? (
                  <>
                    <div className="tvwall-cell-video"><Play size={24} /></div>
                    <div className="tvwall-cell-label">{cell.cameraName}</div>
                  </>
                ) : (
                  <div className="tvwall-cell-empty">未绑定</div>
                )}
              </div>
            ))}
          </div>
          <div className="splicer-config">
            <h3>拼控设备</h3>
            <table>
              <thead><tr><th>设备名称</th><th>设备IP</th><th>输出通道数</th><th>状态</th><th>操作</th></tr></thead>
              <tbody>
                <tr>
                  <td>主拼控器</td>
                  <td>192.168.1.100</td>
                  <td>6</td>
                  <td><span className="status running">在线</span></td>
                  <td className="actions">
                    <button><Settings size={14} /></button>
                    <button><Trash2 size={14} /></button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'template' && (
        <div className="panel">
          <div className="toolbar-row">
            <div className="panel-title">上墙模板</div>
            <button><Plus size={16} />新建模板</button>
          </div>
          <table>
            <thead><tr><th>模板名称</th><th>窗口布局</th><th>关联信号源</th><th>操作</th></tr></thead>
            <tbody>
              <tr><td>大门巡逻模板</td><td>2×2</td><td>大门入口, 门卫室</td><td className="actions"><button><Settings size={14} /></button><button><Trash2 size={14} /></button></td></tr>
              <tr><td>停车场监视模板</td><td>3×1</td><td>停车场 A, B, C</td><td className="actions"><button><Settings size={14} /></button><button><Trash2 size={14} /></button></td></tr>
              <tr><td>办公楼大屏模板</td><td>4×3</td><td>12 个监控点</td><td className="actions"><button><Settings size={14} /></button><button><Trash2 size={14} /></button></td></tr>
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 'control' && (
        <div className="tvwall-control">
          <div className="tvwall-control-cameras">
            <div className="panel-title">信号源列表</div>
            {['大门入口', '停车场', '办公楼大厅', '走廊', '停车场 B', '门卫室'].map(name => (
              <div key={name} className="stream-control">
                <div><strong>{name}</strong><span>RUNNING</span></div>
                <button title="上墙"><Monitor size={16} /></button>
              </div>
            ))}
          </div>
          <div className="tvwall-control-walls">
            <div className="panel-title">上墙窗口</div>
            <div className={`tvwall-mini-grid tvwall-mini-cols-${wallCols}`}>
              {wallCells.map((cell, i) => (
                <div key={cell.id} className={`tvwall-mini-cell ${cell.cameraName ? 'active' : ''}`}>
                  {i + 1}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'alarm' && (
        <div className="panel">
          <div className="toolbar-row">
            <div className="panel-title">报警上墙业务</div>
            <button><Plus size={16} />新建报警上墙</button>
          </div>
          <table>
            <thead><tr><th>任务名称</th><th>开窗设置</th><th>绑定信号源</th><th>报警停留时间</th><th>触发条件</th><th>操作</th></tr></thead>
            <tbody>
              <tr>
                <td>正门入侵上墙</td>
                <td>2×2 窗口</td>
                <td>大门入口, 门卫室</td>
                <td>60s</td>
                <td>区域入侵</td>
                <td className="actions"><button><Settings size={14} /></button><button><Trash2 size={14} /></button></td>
              </tr>
              <tr>
                <td>停车场告警上墙</td>
                <td>3×1 窗口</td>
                <td>停车场 A/B/C</td>
                <td>120s</td>
                <td>车辆违停</td>
                <td className="actions"><button><Settings size={14} /></button><button><Trash2 size={14} /></button></td>
              </tr>
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 'keyboard' && (
        <div className="panel">
          <div className="toolbar-row">
            <div className="panel-title">网络键盘管理</div>
            <button><Plus size={16} />添加键盘</button>
          </div>
          <p className="hint">支持华智指定网络键盘的接入和控制，配置电视墙编号、视频源编号、视频源轮巡组编号。</p>
          <table>
            <thead><tr><th>键盘名称</th><th>设备IP</th><th>电视墙编号</th><th>视频源编号</th><th>轮巡组编号</th><th>状态</th><th>操作</th></tr></thead>
            <tbody>
              <tr>
                <td>主控键盘 #1</td>
                <td>192.168.1.50</td>
                <td>TW-001</td>
                <td>VS-001~VS-100</td>
                <td>PT-001</td>
                <td><span className="status running">在线</span></td>
                <td className="actions"><button><Settings size={14} /></button><button><Trash2 size={14} /></button></td>
              </tr>
              <tr>
                <td>分控键盘 #2</td>
                <td>192.168.1.51</td>
                <td>TW-001</td>
                <td>VS-101~VS-200</td>
                <td>PT-002</td>
                <td><span className="status stopped">离线</span></td>
                <td className="actions"><button><Settings size={14} /></button><button><Trash2 size={14} /></button></td>
              </tr>
            </tbody>
          </table>
        </div>
      )}

      {decoderMode && (
        <div className="modal-overlay" onClick={() => setDecoderMode(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-title">解码通道绑定</div>
            <table>
              <thead><tr><th>输出通道</th><th>绑定窗口</th><th>信号源</th><th>解码状态</th></tr></thead>
              <tbody>
                <tr><td>HDMI-1</td><td>窗口 1</td><td>大门入口</td><td><span className="status running">解码中</span></td></tr>
                <tr><td>HDMI-2</td><td>窗口 2</td><td>-</td><td><span className="status stopped">空闲</span></td></tr>
                <tr><td>HDMI-3</td><td>窗口 3</td><td>-</td><td><span className="status stopped">空闲</span></td></tr>
              </tbody>
            </table>
            <div className="button-row modal-actions">
              <button onClick={() => setDecoderMode(false)}>关闭</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
