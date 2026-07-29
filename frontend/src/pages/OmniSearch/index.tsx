import { useEffect, useMemo, useRef, useState, type CSSProperties } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  ArrowDownToLine,
  ArrowRight,
  BadgeCheck,
  Boxes,
  Camera,
  CopyPlus,
  Crosshair,
  Download,
  Image as ImageIcon,
  ListChecks,
  Map,
  Maximize2,
  MousePointer2,
  Play,
  Plus,
  Radar,
  Route,
  ScanSearch,
  Search,
  Send,
  SlidersHorizontal,
  Sparkles,
  Square,
  Upload,
  Video,
} from 'lucide-react';
import { api, assetUrl, type DetectedPerson, type PersonSearchBboxPoint, type PersonSearchResultResponse, type SimilarPersonResult } from '../../api';
import trajectoryCampusMap from '../../assets/trajectory-campus-map.png';

type SearchResultType = 'person' | 'vehicle';

type TextVideoCamera = {
  id: string;
  name: string;
  code: string;
  status: 'online' | 'offline';
  active?: boolean;
};

type TextVideoTreeArea = {
  id: string;
  name: string;
  count: number;
  cameras: TextVideoCamera[];
};

type TextVideoSegment = {
  id: string;
  title: string;
  duration: string;
  time: string;
  image: string;
  tags: string[];
  selected?: boolean;
};

type ImageResult = {
  id: string;
  type: SearchResultType;
  title: string;
  camera: string;
  time: string;
  similarity: number;
  attributes: string[];
};

type TrackPoint = {
  id: string;
  time: string;
  camera: string;
  position: string;
  event: string;
  similarity: number;
  node: 'start' | 'normal' | 'turn' | 'end';
};

type PrototypeCardResult = {
  image: string;
  location: string;
  time: string;
  features: string;
  name: string;
  detail: string;
};

const textVideoTree: TextVideoTreeArea[] = [
  {
    id: 'area-south',
    name: '园区南门',
    count: 6,
    cameras: [
      { id: 'tv-c1', name: '南门入口枪机', code: 'CAM-S-021', status: 'online', active: true },
      { id: 'tv-c2', name: '访客通道球机', code: 'CAM-S-024', status: 'online' },
    ],
  },
  {
    id: 'area-building',
    name: '办公楼群',
    count: 9,
    cameras: [
      { id: 'tv-c3', name: 'B栋12楼电梯出口', code: 'CAM-B-12-006', status: 'online' },
      { id: 'tv-c4', name: 'A1栋大厅半球', code: 'CAM-A1-L-003', status: 'online' },
    ],
  },
  {
    id: 'area-parking',
    name: '地下停车场',
    count: 7,
    cameras: [
      { id: 'tv-c5', name: '停车场东入口球机', code: 'CAM-P-E-014', status: 'offline' },
      { id: 'tv-c6', name: '车辆出入口卡口', code: 'CAM-P-G-009', status: 'online' },
    ],
  },
];

const textVideoSegments: TextVideoSegment[] = [
  {
    id: 'seg-01',
    title: '监控片段 01',
    duration: '01:36',
    time: '2026/07/08 10:21:20',
    image: 'https://images.unsplash.com/photo-1494522855154-9297ac14b55f?auto=format&fit=crop&w=520&q=80',
    tags: ['行人', '南门', '进入'],
    selected: true,
  },
  {
    id: 'seg-02',
    title: '监控片段 02',
    duration: '02:08',
    time: '2026/07/08 10:26:44',
    image: 'https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=520&q=80',
    tags: ['车辆', '园区道路'],
  },
  {
    id: 'seg-03',
    title: '监控片段 03',
    duration: '00:58',
    time: '2026/07/08 10:31:12',
    image: 'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=520&q=80',
    tags: ['异常停留', '楼宇'],
  },
  {
    id: 'seg-04',
    title: '监控片段 04',
    duration: '01:45',
    time: '2026/07/08 10:39:08',
    image: 'https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?auto=format&fit=crop&w=520&q=80',
    tags: ['行人', '连廊'],
  },
  {
    id: 'seg-05',
    title: '监控片段 05',
    duration: '02:21',
    time: '2026/07/08 10:46:35',
    image: 'https://images.unsplash.com/photo-1470229538611-16ba8c7ffbd7?auto=format&fit=crop&w=520&q=80',
    tags: ['车辆', '卡口'],
  },
  {
    id: 'seg-06',
    title: '监控片段 06',
    duration: '01:12',
    time: '2026/07/08 10:52:19',
    image: 'https://images.unsplash.com/photo-1518005020951-eccb494ad742?auto=format&fit=crop&w=520&q=80',
    tags: ['人员聚集', '广场'],
  },
];

const imageResults: ImageResult[] = [
  {
    id: 'r1',
    type: 'person',
    title: '深色上衣人员',
    camera: 'A区南门枪机',
    time: '2026/07/07 09:24:18',
    similarity: 94,
    attributes: ['男性', '黑色上衣', '白色鞋', '背包', '步行'],
  },
  {
    id: 'r2',
    type: 'vehicle',
    title: '白色小型轿车',
    camera: '停车场东入口球机',
    time: '2026/07/07 08:51:42',
    similarity: 91,
    attributes: ['轿车', '白色', '京A·82K6', '蓝牌', '本田'],
  },
  {
    id: 'r3',
    type: 'person',
    title: '浅色外套人员',
    camera: 'B栋12楼电梯出口',
    time: '2026/07/06 18:12:09',
    similarity: 88,
    attributes: ['女性', '浅灰外套', '长发', '手提包', '驻留'],
  },
  {
    id: 'r4',
    type: 'vehicle',
    title: '黑色SUV',
    camera: '园区北门卡口',
    time: '2026/07/06 17:38:27',
    similarity: 86,
    attributes: ['SUV', '黑色', '沪C·19P2', '蓝牌', '大众'],
  },
];

const trackPoints: TrackPoint[] = [
  { id: 't1', time: '09:24:18', camera: 'A区南门枪机', position: '南门入口', event: '首次出现', similarity: 94, node: 'start' },
  { id: 't2', time: '09:31:06', camera: 'A1栋大厅半球', position: 'A1栋大厅', event: '进入楼宇', similarity: 91, node: 'normal' },
  { id: 't3', time: '09:42:33', camera: '连廊西侧球机', position: 'A/B区连廊', event: '方向转折', similarity: 89, node: 'turn' },
  { id: 't4', time: '09:58:45', camera: 'B栋12楼电梯出口', position: 'B栋12楼', event: '最后出现', similarity: 87, node: 'end' },
];

const videoFrames = [
  { id: 'f1', time: '09:24:18', title: '人员从南门进入', object: '人员', event: '进入园区' },
  { id: 'f2', time: '09:31:06', title: '目标进入A1栋大厅', object: '人员', event: '跨区域移动' },
  { id: 'f3', time: '09:42:33', title: '目标经过连廊', object: '人员', event: '方向变化' },
];

const prototypeTextImageResults = [
  { id: 'p1', image: 'https://s.coze.cn/image/UTybzJ3M2zg/', location: '南门入口-C01', time: '14:32:15', features: '男性，黑色上衣，短发', name: '张明', detail: '男 · 32岁' },
  { id: 'p2', image: 'https://s.coze.cn/image/1EQsEiH6idg/', location: '园区广场-C02', time: '14:28:42', features: '男性，深色上衣', name: '李伟', detail: '男 · 28岁' },
  { id: 'p3', image: 'https://s.coze.cn/image/VM9rSVL-1yQ/', location: '地下车库-C03', time: '14:15:33', features: '男性，灰色上衣', name: '王强', detail: '男 · 35岁' },
  { id: 'p4', image: 'https://s.coze.cn/image/N7ptFNbFcjE/', location: '办公楼层-C04', time: '13:58:21', features: '男性，蓝色外套', name: '赵军', detail: '男 · 41岁' },
  { id: 'p5', image: 'https://s.coze.cn/image/FJiQPeFpYlc/', location: '餐厅-C05', time: '13:45:18', features: '女性，长发', name: '刘芳', detail: '女 · 26岁' },
  { id: 'p6', image: 'https://s.coze.cn/image/y6XMInNaZC8/', location: '会议室区-C06', time: '13:32:07', features: '男性，眼镜', name: '陈杰', detail: '男 · 30岁' },
  { id: 'p7', image: 'https://s.coze.cn/image/3zCe7cPeVJg/', location: '停车场-D01', time: '12:18:45', features: '女性，白色上衣', name: '杨丽', detail: '女 · 33岁' },
  { id: 'p8', image: 'https://s.coze.cn/image/cAzmdke_T8I/', location: '东门入口-D02', time: '11:55:22', features: '男性，外套', name: '周勇', detail: '男 · 45岁' },
  { id: 'p9', image: 'https://s.coze.cn/image/UTybzJ3M2zg/', location: '南门入口-C01', time: '11:20:33', features: '男性，灰色运动裤，戴耳机', name: '吴刚', detail: '男 · 38岁' },
  { id: 'p10', image: 'https://s.coze.cn/image/1EQsEiH6idg/', location: '园区广场-C02', time: '10:48:15', features: '女性，米色背包，太阳镜', name: '孙婷', detail: '女 · 24岁' },
  { id: 'p11', image: 'https://s.coze.cn/image/VM9rSVL-1yQ/', location: '地下车库-C03', time: '10:15:42', features: '男性，黑色运动套装', name: '郑涛', detail: '男 · 29岁' },
  { id: 'p12', image: 'https://s.coze.cn/image/N7ptFNbFcjE/', location: '办公楼层-C04', time: '09:50:18', features: '女性，红色围巾，手提袋', name: '黄敏', detail: '女 · 36岁' },
];

const prototypeVideoEvents = [
  { id: 've1', image: 'https://s.coze.cn/image/VM9rSVL-1yQ/', time: '16:10:23', type: '车辆进入', status: '正常', title: '白色奔驰GLC300进入B2层停车场', info: ['车牌: 京A·12345'] },
  { id: 've2', image: 'https://s.coze.cn/image/3zCe7cPeVJg/', time: '16:12:37', type: '剐蹭事故', status: '异常', title: '黑色大众与白色奔驰发生剐蹭', info: ['肇事车辆: 黑色大众 粤B·A8***', '受损车辆: 白色奔驰 京A·12345', '肇事人: 男性，30-45岁，深色外套'], highlight: true },
  { id: 've3', image: 'https://s.coze.cn/image/-wPO7bjzom0/', time: '16:15:42', type: '车辆离开', status: '正常', title: '黑色大众驶离现场', info: ['车牌: 粤B·A8***'] },
];

const prototypeTrajectoryPoints = [
  { id: 'tp1', label: '1', title: '园区东门', time: '14:23:15', desc: '进入园区', tag: '起点', type: 'start', left: 16, top: 24 },
  { id: 'tp2', label: '2', title: '办公楼A座大厅', time: '14:25:32', desc: '停留 2分钟', tag: '停留', type: 'normal', left: 32, top: 34 },
  { id: 'tp3', label: '3', title: '电梯间', time: '14:35:18', desc: '经过', tag: '经过', type: 'normal', left: 38, top: 45 },
  { id: 'tp4', label: '4', title: '会议室B-301', time: '14:42:05', desc: '停留 33分钟 · 会议', tag: '停留', type: 'warning', left: 58, top: 40 },
  { id: 'tp5', label: '5', title: '餐厅', time: '15:15:40', desc: '停留 32分钟 · 用餐', tag: '停留', type: 'normal', left: 50, top: 68 },
  { id: 'tp6', label: '6', title: '停车场B区', time: '15:48:22', desc: '经过', tag: '经过', type: 'normal', left: 28, top: 82 },
  { id: 'tp7', label: '7', title: '园区西门', time: '16:05:11', desc: '离开园区', tag: '终点', type: 'end', left: 12, top: 74 },
];

function StatusBadge({ status }: { status: TextVideoCamera['status'] }) {
  return <span className={`omni-status ${status}`}>{status === 'online' ? '在线' : '离线'}</span>;
}

function PageHeader({
  title, desc, action,
}: {
  title: string;
  desc: string;
  action?: React.ReactNode;
}) {
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

function OmniPrompt({
  placeholder,
  defaultValue,
  showUpload,
}: {
  placeholder: string;
  defaultValue?: string;
  showUpload?: boolean;
}) {
  const [value, setValue] = useState(defaultValue ?? '');
  const [fileName, setFileName] = useState('');

  return (
    <section className="omni-command">
      <div className="omni-command-head">
        <span><Sparkles size={16} />自然语言检索</span>
        <div className="omni-chip-row">
          <button type="button">今天上午</button>
          <button type="button">A区附近</button>
          <button type="button">目标人员</button>
        </div>
      </div>
      <div className="omni-input-shell">
        <textarea
          value={value}
          onChange={event => setValue(event.target.value)}
          placeholder={placeholder}
        />
        <div className="omni-input-actions">
          {showUpload && (
            <label className={`omni-upload-action ${fileName ? 'has-file' : ''}`}>
              <Upload size={16} />
              <span>{fileName || '拖拽或选择视频'}</span>
              <input
                type="file"
                accept="video/*"
                onChange={event => setFileName(event.target.files?.[0]?.name ?? '')}
              />
            </label>
          )}
          <button className="omni-primary-btn" type="button"><Send size={15} />检索</button>
        </div>
      </div>
    </section>
  );
}

function OmniMetricStrip() {
  return (
    <div className="omni-metrics">
      <div><strong>69</strong><span>可检索点位</span></div>
      <div><strong>24h</strong><span>单段视频问询上限</span></div>
      <div><strong>85%</strong><span>默认相似度阈值</span></div>
      <div><strong>4</strong><span>轨迹关键节点</span></div>
    </div>
  );
}

export function OmniSearchHome() {
  return (
    <>
      <PageHeader
        title="万物搜"
        desc="通过文本、图片和视频问询完成摄像机点位、人员、车辆与轨迹检索"
        action={<Link className="button-like omni-primary-btn" to="/omni-search/text-video"><Search size={16} />开始检索</Link>}
      />
      <OmniPrompt
        placeholder="输入自然语言，例如：查找今天上午从A区南门进入、穿黑色上衣并背包的人员"
        defaultValue="今天上午 A区南门附近 穿黑色上衣 背包人员"
      />
      <OmniMetricStrip />
      <section className="omni-home-grid">
        <Link className="omni-capability" to="/omni-search/text-video">
          <Video size={22} />
          <div>
            <strong>文搜视频</strong>
            <span>模糊或精确搜索摄像机点位，查看实时/回放视频并发起视频问询。</span>
          </div>
          <ArrowRight size={16} />
        </Link>
        <Link className="omni-capability" to="/omni-search/text-image">
          <ScanSearch size={22} />
          <div>
            <strong>文搜图</strong>
            <span>用自然语言检索人员、车辆，展示属性、bbox 与精准时间戳。</span>
          </div>
          <ArrowRight size={16} />
        </Link>
        <Link className="omni-capability" to="/omni-search/image-image">
          <ImageIcon size={22} />
          <div>
            <strong>图搜图</strong>
            <span>选择平台图片或本地上传图片，组合时间、地点与相似度筛选。</span>
          </div>
          <ArrowRight size={16} />
        </Link>
        <Link className="omni-capability" to="/omni-search/tracking">
          <Route size={22} />
          <div>
            <strong>轨迹还原</strong>
            <span>根据已选目标按时间轴还原运动路径，查看关键节点和轨迹详情。</span>
          </div>
          <ArrowRight size={16} />
        </Link>
      </section>
      <section className="panel omni-recent-panel">
        <div className="section-head">
          <strong>最近检索</strong>
          <button type="button"><ArrowDownToLine size={15} />导出记录</button>
        </div>
        <table>
          <thead>
            <tr><th>检索内容</th><th>类型</th><th>命中结果</th><th>最近时间</th><th>操作</th></tr>
          </thead>
          <tbody>
            <tr><td>今天上午 A区南门 黑色上衣人员</td><td>文搜图</td><td>18 张图片</td><td>2026/07/07 10:18</td><td><Link to="/omni-search/text-image">查看</Link></td></tr>
            <tr><td>B栋12楼电梯出口摄像头 09:00-10:00</td><td>文搜视频</td><td>1 路回放</td><td>2026/07/07 09:55</td><td><Link to="/omni-search/text-video">查看</Link></td></tr>
            <tr><td>目标ID P-2048 轨迹还原</td><td>轨迹还原</td><td>4 个轨迹点</td><td>2026/07/07 09:48</td><td><Link to="/omni-search/tracking">查看</Link></td></tr>
          </tbody>
        </table>
      </section>
    </>
  );
}

function TextVideoDeviceTree() {
  return (
    <aside className="proto-video-device-tree">
      <div className="proto-device-tree-header">
        <Camera size={15} />
        设备列表
      </div>
      <label className="proto-device-tree-search">
        <Search size={13} />
        <input placeholder="搜索设备..." />
      </label>
      <div className="proto-device-tree-list">
        {textVideoTree.map(area => (
          <section className="proto-device-group" key={area.id}>
            <div className="proto-device-group-header">
              <ArrowRight size={12} />
              <span>{area.name}</span>
              <small>{area.count} 路</small>
            </div>
            <div className="proto-device-group-items">
              {area.cameras.map(camera => (
                <button
                  className={`proto-device-item ${camera.active ? 'active' : ''} ${camera.status === 'offline' ? 'offline' : ''}`}
                  key={camera.id}
                  type="button"
                >
                  <Camera size={14} />
                  <span>
                    <strong>{camera.name}</strong>
                    <small>{camera.code}</small>
                  </span>
                  <StatusBadge status={camera.status} />
                </button>
              ))}
            </div>
          </section>
        ))}
      </div>
    </aside>
  );
}

function TextVideoCenter() {
  const [query, setQuery] = useState('');
  const preview = textVideoSegments[0];

  return (
    <main className="proto-video-chat-area">
      <section className="proto-center-video-section">
        <div className="proto-center-video-header">
          <div className="proto-center-video-title">
            <Video size={15} />
            <span>南门入口枪机</span>
            <em><i />录像</em>
          </div>
          <div className="proto-video-actions">
            <button type="button" title="重置"><ArrowDownToLine size={14} /></button>
            <button type="button" title="全屏"><Maximize2 size={14} /></button>
            <button type="button" title="小窗"><Square size={13} /></button>
          </div>
        </div>
        <div className="proto-center-video-player">
          <img src={preview.image} alt="南门入口监控画面" />
          <button className="proto-video-play" type="button" aria-label="播放视频">
            <Play size={26} fill="currentColor" />
          </button>
        </div>
        <div className="proto-center-video-controls">
          <button type="button" aria-label="播放"><Play size={13} fill="currentColor" /></button>
          <button type="button" aria-label="快退">«</button>
          <button type="button" aria-label="快进">»</button>
          <div className="proto-video-progress"><span /></div>
          <time>00:35:00 / 02:30:00</time>
        </div>
      </section>
      <section className="proto-chat-messages">
        <article className="proto-chat-message bot">
          <div className="proto-message-avatar"><Boxes size={15} /></div>
          <div className="proto-message-content">
            <p>从左侧设备树选择摄像机后，系统将自动展示视频画面和分析结果。</p>
            <span>选中视频后，可在下方输入框输入问题进行 AI 视频理解分析</span>
          </div>
        </article>
        <article className="proto-chat-message user">
          <div className="proto-message-content">
            <p>请分析 B2 层停车场 16:10 到 16:16 的车辆异常事件。</p>
          </div>
        </article>
        <article className="proto-chat-message bot">
          <div className="proto-message-avatar"><Boxes size={15} /></div>
          <div className="proto-message-content">
            <p>检测到 3 个关键事件，其中 16:12:37 黑色大众与白色奔驰发生剐蹭，已在右侧生成事件卡片。</p>
          </div>
        </article>
      </section>
      <section className="proto-input-area">
        <div className="proto-input-wrapper">
          <input
            value={query}
            onChange={event => setQuery(event.target.value)}
            placeholder="选择设备后，输入问题进行视频分析..."
          />
          <button type="button" aria-label="发送问题"><Send size={18} /></button>
        </div>
      </section>
    </main>
  );
}

function TextVideoAnalysisPanel() {
  return (
    <aside className="proto-analysis-panel">
      <div className="proto-analysis-header">
        <h3><ListChecks size={15} />分析结果</h3>
        <span>{prototypeVideoEvents.length} 个事件</span>
      </div>
      <div className="proto-event-report">
        {prototypeVideoEvents.map(event => (
          <article className={`proto-event-card ${event.highlight ? 'highlight' : ''}`} key={event.id}>
            <div className="proto-event-card-content">
              <div className="proto-event-keyframe">
                <img src={event.image} alt={event.title} loading="lazy" />
                <time>{event.time}</time>
              </div>
              <div className="proto-event-details">
                <div className="proto-event-header">
                  <span>{event.time}</span>
                  <span>类型: {event.type}</span>
                  <b className={event.highlight ? 'warning' : 'normal'}>{event.status}</b>
                </div>
                <strong>{event.title}</strong>
                {event.info.map(item => <small key={item}>{item}</small>)}
              </div>
            </div>
            <p>双击放大 | 拖拽到输入框进行操作</p>
          </article>
        ))}
        <section className="proto-event-summary">
          <h3><ListChecks size={16} />事件摘要</h3>
          <div>
            <strong>事件概况</strong>
            <p>2026-04-20 16:12:37，B2层C区通道，黑色大众在倒车时与停放的白色奔驰发生剐蹭。</p>
          </div>
          <div>
            <strong>涉及车辆</strong>
            <p>肇事车辆: 黑色大众 粤B·A8***；受损车辆: 白色奔驰 京A·12345</p>
          </div>
          <div className="proto-summary-actions">
            <button type="button">布控车辆</button>
            <Link to="/omni-search/text-video/analysis/trajectory">轨迹还原</Link>
            <button type="button">导出报告</button>
          </div>
        </section>
      </div>
    </aside>
  );
}

export function TextVideoSearch() {
  return (
    <div className="omni-prototype-page proto-video-search-layout">
      <TextVideoDeviceTree />
      <TextVideoCenter />
      <TextVideoAnalysisPanel />
    </div>
  );
}

function KeyFrameCard({ frame }: { frame: typeof videoFrames[number] }) {
  return (
    <article className="omni-frame-card">
      <div className="omni-frame-visual">
        <div className="omni-target-box person" />
        <button type="button" title="双击放大"><Maximize2 size={15} /></button>
      </div>
      <div className="omni-frame-body">
        <strong>{frame.title}</strong>
        <span>{frame.time}</span>
        <dl>
          <div><dt>对象</dt><dd>{frame.object}</dd></div>
          <div><dt>事件</dt><dd>{frame.event}</dd></div>
        </dl>
      </div>
    </article>
  );
}

function AnalysisActionPanel({ action }: { action: string }) {
  if (action.includes('image-search')) {
    return (
      <section className="panel omni-action-panel">
        <div className="panel-title">以图搜图</div>
        <p>已选关键帧中的目标人员，自动带入图搜图检索图像与默认相似度范围。</p>
        <div className="omni-action-row">
          <Link className="button-like omni-primary-btn" to="/omni-search/image-image"><ImageIcon size={15} />进入图搜图</Link>
          <button type="button"><SlidersHorizontal size={15} />调整筛选</button>
        </div>
      </section>
    );
  }
  if (action.includes('append-input')) {
    return (
      <section className="panel omni-action-panel">
        <div className="panel-title">追加到输入框</div>
        <p>关键帧对象、事件和时间点已整理为下一轮问询上下文。</p>
        <div className="omni-append-box">09:31:06 A1栋大厅 目标人员进入楼宇，请继续判断其是否进入B栋。</div>
      </section>
    );
  }
  if (action.includes('image-deploy')) {
    return <ImageDeployPage compact />;
  }
  if (action.includes('trajectory')) {
    return <TrajectoryPanel compact />;
  }
  return (
    <section className="panel omni-action-panel">
      <div className="panel-title">分析结果操作</div>
      <p>可继续对关键帧中的目标执行以图搜图、追加问询、图像布控或轨迹还原。</p>
      <div className="omni-action-row">
        <Link className="button-like" to="/omni-search/text-video/analysis/image-search"><ImageIcon size={15} />以图搜图</Link>
        <Link className="button-like" to="/omni-search/text-video/analysis/append-input"><CopyPlus size={15} />追加输入</Link>
        <Link className="button-like" to="/omni-search/text-video/analysis/image-deploy"><Radar size={15} />图像布控</Link>
        <Link className="button-like" to="/omni-search/text-video/analysis/trajectory"><Route size={15} />轨迹还原</Link>
      </div>
    </section>
  );
}

export function VideoAnalysisPage() {
  const location = useLocation();

  return (
    <>
      <PageHeader
        title="点击分析结果"
        desc="自动定位事件关键帧，并将事件文本解析为对象、事件详情和可继续检索的结构化信息"
        action={<Link className="button-like" to="/omni-search/text-video"><ArrowRight size={16} />返回文搜视频</Link>}
      />
      <div className="omni-analysis-layout">
        <section className="panel">
          <div className="section-head">
            <strong>关键帧定位</strong>
            <span className="omni-muted">双击关键帧可放大查看</span>
          </div>
          <div className="omni-frame-grid">
            {videoFrames.map(frame => <KeyFrameCard key={frame.id} frame={frame} />)}
          </div>
        </section>
        <section className="panel">
          <div className="panel-title">结构化解析</div>
          <div className="omni-structured-list">
            <div><span>目标对象</span><strong>人员 P-2048</strong></div>
            <div><span>事件详情</span><strong>从A区南门进入，途经A1栋大厅和连廊，最终出现在B栋12楼</strong></div>
            <div><span>时间范围</span><strong>2026/07/07 09:24:18 - 09:58:45</strong></div>
            <div><span>建议动作</span><strong>以图搜图、图像布控、轨迹还原</strong></div>
          </div>
        </section>
      </div>
      <AnalysisActionPanel action={location.pathname} />
    </>
  );
}

function ResultVisual({ result, selected }: { result: ImageResult; selected?: boolean }) {
  return (
    <div className={`omni-result-visual ${result.type} ${selected ? 'selected' : ''}`}>
      <div className={`omni-target-box ${result.type}`} />
      <span className="omni-frame-time">{result.time.split(' ')[1]}</span>
      <button type="button" title="手动框选目标"><MousePointer2 size={14} /></button>
    </div>
  );
}

function PrototypeResultCard({
  result,
  similarity,
  level,
  jumpToImageSearch,
}: {
  result: PrototypeCardResult;
  similarity?: number;
  level?: string;
  jumpToImageSearch?: boolean;
}) {
  return (
    <article className="proto-search-result-card">
      {similarity !== undefined && <div className={`proto-card-similarity ${level ?? 'medium'}`}>相似度 {similarity}%</div>}
      <div className="proto-card-image">
        <img src={result.image} alt={`${result.location} 检索结果`} loading="lazy" />
        {jumpToImageSearch && (
          <Link className="proto-card-jump-icon" to="/omni-search/image-image" title="以图搜图">
            <Search size={14} />
          </Link>
        )}
      </div>
      <div className="proto-card-info">
        <strong>{result.location}</strong>
        <time>{result.time}</time>
        <span>{result.features}</span>
      </div>
      <div className="proto-card-person">
        <span>人</span>
        <div>
          <strong>{result.name}</strong>
          <small>{result.detail}</small>
        </div>
      </div>
    </article>
  );
}

export function TextImageSearch() {
  const [type, setType] = useState<SearchResultType>('person');

  return (
    <div className="omni-prototype-page">
      <section className="proto-search-card">
        <div className="proto-tabs">
          <button type="button" className={type === 'person' ? 'active' : ''} onClick={() => setType('person')}>
            <BadgeCheck size={15} />
            人员检索
          </button>
          <button type="button" className={type === 'vehicle' ? 'active' : ''} onClick={() => setType('vehicle')}>
            <Camera size={15} />
            车辆检索
          </button>
        </div>

        {type === 'person' ? (
          <div className="proto-filter-grid six">
            {([
              ['性别', ['不限', '男性', '女性']],
              ['年龄段', ['不限', '青年(19-35)', '中年(36-55)']],
              ['上衣颜色', ['不限', '红色', '蓝色', '黑色']],
              ['下装颜色', ['不限', '深色', '浅色']],
            ] as Array<[string, string[]]>).map(([label, options]) => (
              <label key={label}>
                <span>{label}</span>
                <select>{options.map(option => <option key={option}>{option}</option>)}</select>
              </label>
            ))}
            <label><span>开始时间</span><input type="datetime-local" defaultValue="2024-01-15T00:00" /></label>
            <label><span>结束时间</span><input type="datetime-local" defaultValue="2024-01-15T23:59" /></label>
          </div>
        ) : (
          <div className="proto-filter-grid four">
            {([
              ['车牌颜色', ['不限', '蓝色', '黄色', '绿色']],
              ['车辆类型', ['不限', '轿车', 'SUV', '货车']],
              ['车身颜色', ['不限', '白色', '黑色', '灰色']],
            ] as Array<[string, string[]]>).map(([label, options]) => (
              <label key={label}>
                <span>{label}</span>
                <select>{options.map(option => <option key={option}>{option}</option>)}</select>
              </label>
            ))}
            <label><span>开始时间</span><input type="datetime-local" defaultValue="2024-01-15T00:00" /></label>
          </div>
        )}

        <div className="proto-text-search-row">
          <input placeholder="描述你要查找的目标特征..." />
          <button type="button">搜索</button>
        </div>
      </section>

      <section className="proto-search-results-full">
        <div className="proto-search-result-cards">
          {prototypeTextImageResults.map(result => (
            <PrototypeResultCard key={result.id} result={result} jumpToImageSearch />
          ))}
        </div>
      </section>
    </div>
  );
}

export function ImageImageSearch() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState('');
  const [imageUrlInput, setImageUrlInput] = useState('');
  const [queryImageUrl, setQueryImageUrl] = useState('');
  const [detectedPersons, setDetectedPersons] = useState<DetectedPerson[]>([]);
  const [imageShape, setImageShape] = useState<number[]>([]);
  const [naturalShape, setNaturalShape] = useState<number[]>([]);
  const [selectedPersonIndex, setSelectedPersonIndex] = useState(0);
  const [similarity, setSimilarity] = useState(70);
  const [searchMethod, setSearchMethod] = useState<'reid' | 'vlm'>('reid');
  const [topK, setTopK] = useState(10);
  const [startTime, setStartTime] = useState('2024-12-12T00:00');
  const [endTime, setEndTime] = useState('2026-12-12T23:59');
  const [taskId, setTaskId] = useState('');
  const [phase, setPhase] = useState<'idle' | 'detecting' | 'detected' | 'submitting' | 'polling' | 'success' | 'error'>('idle');
  const [statusText, setStatusText] = useState('等待上传图片');
  const [errorText, setErrorText] = useState('');
  const [results, setResults] = useState<SimilarPersonResult[]>([]);
  const [taskResult, setTaskResult] = useState<PersonSearchResultResponse | null>(null);
  const pollRunRef = useRef(0);
  const selectedPerson = detectedPersons[selectedPersonIndex];
  const activeImageShape = imageShape.length >= 2 ? imageShape : naturalShape;
  const busy = phase === 'detecting' || phase === 'submitting' || phase === 'polling';

  useEffect(() => () => {
    pollRunRef.current += 1;
  }, []);

  useEffect(() => () => {
    if (previewUrl.startsWith('blob:')) {
      URL.revokeObjectURL(previewUrl);
    }
  }, [previewUrl]);

  function resetSearchState() {
    pollRunRef.current += 1;
    setPhase('idle');
    setDetectedPersons([]);
    setImageShape([]);
    setSelectedPersonIndex(0);
    setTaskId('');
    setResults([]);
    setTaskResult(null);
    setErrorText('');
  }

  function handleFileChange(file?: File) {
    resetSearchState();
    setSelectedFile(file ?? null);
    setQueryImageUrl('');
    if (file) {
      setPreviewUrl(URL.createObjectURL(file));
      setStatusText('图片已选择，等待检测');
      return;
    }
    setPreviewUrl('');
    setStatusText('等待上传图片');
  }

  async function handleDetect() {
    resetSearchState();
    setPhase('detecting');
    setStatusText('正在检测图片中的人员');
    try {
      let imageUrl = imageUrlInput.trim();
      if (selectedFile) {
        const uploaded = await api.uploadPersonSearchImage(selectedFile);
        imageUrl = uploaded.imageUrl;
        setPreviewUrl(assetUrl(uploaded.imagePath));
      }
      if (!imageUrl) {
        throw new Error('请先上传图片或输入图片 URL');
      }
      if (!selectedFile) {
        setPreviewUrl(imageUrl);
      }
      setQueryImageUrl(imageUrl);
      const response = await api.detectPersons(imageUrl);
      const detected = response.data?.detected_persons ?? [];
      if (response.data?.status !== 'success' || detected.length === 0) {
        throw new Error(response.data?.message || '未检测到人，请重新上传');
      }
      setDetectedPersons(detected);
      setImageShape(response.data.image_shape ?? []);
      setSelectedPersonIndex(0);
      setPhase('detected');
      setStatusText(response.data.message || `检测到 ${detected.length} 个人`);
    } catch (error) {
      setPhase('error');
      setErrorText(error instanceof Error ? error.message : '人员检测失败');
      setStatusText('检测失败');
    }
  }

  async function handleSearch() {
    if (!queryImageUrl) {
      setPhase('error');
      setErrorText('请先完成人员检测');
      return;
    }
    pollRunRef.current += 1;
    const runId = pollRunRef.current;
    setPhase('submitting');
    setErrorText('');
    setResults([]);
    setTaskResult(null);
    setStatusText('正在提交图搜人任务');
    try {
      const response = await api.searchPersonByBbox({
        imageUrl: queryImageUrl,
        bbox: selectedPerson?.bbox,
        searchMethod,
        startTime: toPersonApiDateTime(startTime),
        endTime: toPersonApiDateTime(endTime),
        similarityThreshold: similarity / 100,
        topK,
      });
      const nextTaskId = response.data?.task_id ?? response.data?.data?.task_id;
      if (!nextTaskId) {
        throw new Error(response.data?.message || '搜索任务提交失败');
      }
      setTaskId(nextTaskId);
      await pollPersonSearchResult(nextTaskId, runId);
    } catch (error) {
      if (runId === pollRunRef.current) {
        setPhase('error');
        setErrorText(error instanceof Error ? error.message : '图搜人任务失败');
        setStatusText('搜索失败');
      }
    }
  }

  async function pollPersonSearchResult(nextTaskId: string, runId: number) {
    setPhase('polling');
    for (let attempt = 0; attempt < 60; attempt += 1) {
      if (runId !== pollRunRef.current) {
        return;
      }
      const response = await api.personSearchResult(nextTaskId);
      if (runId !== pollRunRef.current) {
        return;
      }
      setTaskResult(response);
      const taskStatus = response.data?.status;
      const taskMessage = response.data?.message || '任务处理中';
      setStatusText(taskMessage);
      if (taskStatus === 'success') {
        const resultPayload = personSearchResultPayload(response);
        const similarPersons = resultPayload?.similar_persons ?? [];
        setResults(similarPersons);
        setPhase('success');
        setStatusText(resultPayload?.message || taskMessage || `找到 ${similarPersons.length} 个相似人员`);
        return;
      }
      if (taskStatus === 'error') {
        throw new Error(taskMessage);
      }
      await delay(1500);
    }
    throw new Error('搜索任务超时，请稍后重试');
  }

  return (
    <div className="omni-prototype-page">
      <div className="proto-i2i-top-bar">
        <h1>以图搜图</h1>
        <Link className="proto-trajectory-btn" to="/omni-search/tracking">
          <Route size={16} />
          还原目标轨迹
        </Link>
      </div>

      <section className="proto-search-card">
        <div className="proto-i2i-workspace">
          <div className="proto-i2i-query-panel">
            <label className={`proto-i2i-upload-zone ${selectedFile || previewUrl ? 'has-file' : ''}`}>
              <Upload size={28} />
              <span>{selectedFile?.name || '上传图片'}</span>
              <input
                type="file"
                accept="image/*"
                onChange={event => handleFileChange(event.target.files?.[0])}
              />
            </label>
            <label className="proto-simple-field">
              <span>图片 URL</span>
              <input
                value={imageUrlInput}
                onChange={event => {
                  resetSearchState();
                  setSelectedFile(null);
                  setImageUrlInput(event.target.value);
                  setPreviewUrl(event.target.value.trim());
                  setStatusText(event.target.value.trim() ? '图片 URL 已输入，等待检测' : '等待上传图片');
                }}
                placeholder="http://example.com/query.jpg"
              />
            </label>
            <div className={`proto-i2i-status ${phase}`}>
              <strong>{statusText}</strong>
              {taskId && <span>任务 ID：{taskId}</span>}
              {errorText && <span>{errorText}</span>}
            </div>
          </div>

          <div className="proto-i2i-preview-panel">
            <div className="proto-i2i-preview-frame">
              {previewUrl ? (
                <img
                  src={previewUrl}
                  alt="查询图片"
                  onLoad={event => setNaturalShape([event.currentTarget.naturalHeight, event.currentTarget.naturalWidth])}
                />
              ) : (
                <div className="proto-i2i-empty-preview"><ImageIcon size={28} /><span>未选择图片</span></div>
              )}
              {detectedPersons.map((person, index) => (
                <button
                  key={`${person.person_id ?? 'person'}-${index}`}
                  type="button"
                  className={`proto-i2i-bbox ${index === selectedPersonIndex ? 'active' : ''}`}
                  style={bboxToStyle(person.bbox, activeImageShape)}
                  onClick={() => setSelectedPersonIndex(index)}
                  title={`目标 ${index + 1}`}
                >
                  <span>{index + 1}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="proto-i2i-detect-list">
            <div className="proto-section-label">检测目标</div>
            {detectedPersons.length > 0 ? detectedPersons.map((person, index) => (
              <button
                key={`${person.person_id ?? 'detected'}-${index}`}
                type="button"
                className={index === selectedPersonIndex ? 'active' : ''}
                onClick={() => setSelectedPersonIndex(index)}
              >
                <span>目标 {index + 1}</span>
                <strong>{formatConfidence(person.confidence)}</strong>
              </button>
            )) : (
              <div className="proto-i2i-empty-list">暂无检测框</div>
            )}
          </div>
        </div>
      </section>

      <section className="proto-search-card">
        <div className="proto-filter-grid five proto-i2i-live-filters">
          <label><span>开始时间</span><input type="datetime-local" value={startTime} onChange={event => setStartTime(event.target.value)} /></label>
          <label><span>结束时间</span><input type="datetime-local" value={endTime} onChange={event => setEndTime(event.target.value)} /></label>
          <label>
            <span>搜索方法</span>
            <select value={searchMethod} onChange={event => setSearchMethod(event.target.value as 'reid' | 'vlm')}>
              <option value="reid">ReID</option>
              <option value="vlm">VLM</option>
            </select>
          </label>
          <label>
            <span>相似度: <b>{similarity}%</b></span>
            <input type="range" min="0" max="100" value={similarity} onChange={event => setSimilarity(Number(event.target.value))} />
          </label>
          <label>
            <span>Top K</span>
            <input
              type="number"
              min="1"
              max="100"
              value={topK}
              onChange={event => setTopK(Math.max(1, Number(event.target.value) || 1))}
            />
          </label>
        </div>
        <div className="proto-i2i-action-row">
          <button type="button" onClick={handleDetect} disabled={busy || (!selectedFile && !imageUrlInput.trim())}>
            <ScanSearch size={15} />
            检测人员
          </button>
          <button type="button" className="proto-primary-btn" onClick={handleSearch} disabled={busy || detectedPersons.length === 0}>
            <Search size={15} />
            搜索
          </button>
        </div>
      </section>

      <section className="proto-search-results-full">
        <div className="proto-i2i-results-head">
          <strong>搜索结果</strong>
          <span>{personSearchResultPayload(taskResult)?.message || (results.length ? `${results.length} 条匹配` : '暂无结果')}</span>
        </div>
        {results.length > 0 ? (
          <div className="proto-i2i-result-cards">
            {results.map((result, index) => (
              <article key={result.es_doc_id || `${result.camera_id}-${index}`} className="proto-i2i-result-card">
                <div className="proto-i2i-result-image">
                  {result.image_url ? <img src={assetUrl(result.image_url)} alt={`搜索结果 ${index + 1}`} loading="lazy" /> : <ImageIcon size={24} />}
                  <span>{formatSimilarity(result.similarity_score)}</span>
                </div>
                <div className="proto-i2i-result-info">
                  <strong>{result.camera_id || '未知摄像头'}</strong>
                  <time>{formatCreateTime(result.create_time)}</time>
                  <span>{result.es_doc_id || '无文档 ID'}</span>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div className="proto-i2i-empty-results">{phase === 'success' ? '未找到相似人员' : '完成搜索后展示结果'}</div>
        )}
      </section>
    </div>
  );
}

function delay(ms: number) {
  return new Promise(resolve => {
    window.setTimeout(resolve, ms);
  });
}

function toPersonApiDateTime(value: string) {
  if (!value) {
    return undefined;
  }
  const [date, rawTime = '00:00'] = value.split('T');
  const time = rawTime.length === 5 ? `${rawTime}:00` : rawTime;
  return `${date} ${time}`;
}

function personSearchResultPayload(response: PersonSearchResultResponse | null) {
  const payload = response?.data?.data;
  return payload?.result ?? payload ?? null;
}

function bboxToStyle(bbox: PersonSearchBboxPoint[], imageShape: number[]): CSSProperties {
  const [height, width] = imageShape;
  if (!height || !width || bbox.length === 0) {
    return {};
  }
  const xs = bbox.map(point => point.x);
  const ys = bbox.map(point => point.y);
  const left = Math.max(0, Math.min(...xs) / width * 100);
  const top = Math.max(0, Math.min(...ys) / height * 100);
  const right = Math.min(100, Math.max(...xs) / width * 100);
  const bottom = Math.min(100, Math.max(...ys) / height * 100);
  return {
    left: `${left}%`,
    top: `${top}%`,
    width: `${Math.max(1, right - left)}%`,
    height: `${Math.max(1, bottom - top)}%`,
  };
}

function formatConfidence(confidence?: number) {
  if (confidence === undefined || Number.isNaN(confidence)) {
    return '置信度 --';
  }
  return `置信度 ${Math.round(confidence * 100)}%`;
}

function formatSimilarity(score?: number) {
  if (score === undefined || Number.isNaN(score)) {
    return '--';
  }
  const normalized = score <= 1 ? score * 100 : score;
  return `${Math.round(normalized)}%`;
}

function formatCreateTime(value?: number | string) {
  if (value === undefined || value === null || value === '') {
    return '未知时间';
  }
  const numeric = Number(value);
  if (Number.isFinite(numeric)) {
    const millis = numeric > 10_000_000_000 ? numeric : numeric * 1000;
    return new Date(millis).toLocaleString();
  }
  return String(value);
}

export function ImageDeployPage({ compact = false }: { compact?: boolean }) {
  return (
    <section className={compact ? 'panel omni-action-panel' : ''}>
      {!compact && (
        <PageHeader
          title="图像布控"
          desc="基于关键帧目标创建静态布控任务，前端仅展示任务配置 UI"
          action={<button type="button"><Plus size={16} />新建布控</button>}
        />
      )}
      <div className="panel-title">图像布控配置</div>
      <div className="omni-deploy-grid">
        <ResultVisual result={imageResults[0]} selected />
        <div className="omni-deploy-form">
          <label className="form-label"><span>任务名称</span><input defaultValue="A区黑色上衣人员布控" /></label>
          <label className="form-label"><span>布控范围</span><select defaultValue="园区全域"><option>园区全域</option><option>A区</option><option>B栋</option></select></label>
          <label className="form-label"><span>相似度阈值</span><input type="range" min="50" max="100" defaultValue="88" /></label>
          <label className="form-label"><span>生效时间</span><input defaultValue="2026/07/07 10:00 - 2026/07/08 10:00" /></label>
          <div className="button-row">
            <button type="button" className="omni-primary-btn"><Radar size={15} />保存布控</button>
            <button type="button"><CopyPlus size={15} />复制参数</button>
          </div>
        </div>
      </div>
    </section>
  );
}

function TrajectoryPanel({ compact = false }: { compact?: boolean }) {
  const distance = useMemo(() => '1.84 km', []);

  return (
    <section className={compact ? 'panel omni-action-panel' : 'omni-track-page'}>
      <div className="omni-track-summary">
        <div className="omni-target-avatar"><Crosshair size={24} /></div>
        <div>
          <strong>目标 P-2048</strong>
          <span>黑色上衣、白色鞋、背包 · 检索范围 2026/07/07 09:20-10:05</span>
        </div>
        <div className="omni-track-stats">
          <div><b>{distance}</b><span>总长度</span></div>
          <div><b>34m27s</b><span>总耗时</span></div>
          <div><b>3.2km/h</b><span>平均速度</span></div>
        </div>
      </div>
      <div className="omni-track-layout">
        <div className="omni-map-panel">
          <img className="omni-map-image" src={trajectoryCampusMap} alt="园区道路轨迹示例地图" />
          <div className="omni-map-toolbar">
            <button type="button"><Map size={14} />三方地图</button>
            <button type="button"><Boxes size={14} />数字孪生</button>
          </div>
        </div>
        <div className="omni-timeline">
          {trackPoints.map((point, index) => (
            <article key={point.id} className={`omni-timeline-item ${point.node}`}>
              <span className="omni-timeline-index">{index + 1}</span>
              <div>
                <strong>{point.time} · {point.event}</strong>
                <p>{point.camera} / {point.position}</p>
                <span>相似度 {point.similarity}%</span>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

export function TrajectoryPage() {
  const [activePoint, setActivePoint] = useState(0);

  return (
    <div className="omni-prototype-page proto-trajectory-layout">
      <aside className="proto-trajectory-side">
        <section className="proto-search-card">
          <label className="proto-section-label">目标信息</label>
          <div className="proto-target-info">
            <div />
            <span>
              <strong>目标人员 #001</strong>
              <small>男性 · 黑色上衣</small>
            </span>
          </div>
          <button type="button" className="proto-secondary-btn">更换目标</button>
        </section>

        <section className="proto-search-card">
          <label className="proto-section-label">时间范围</label>
          <label className="proto-simple-field"><span>开始时间</span><input type="datetime-local" /></label>
          <label className="proto-simple-field"><span>结束时间</span><input type="datetime-local" /></label>
        </section>

        <button className="proto-primary-btn" type="button">
          <Download size={16} />
          导出轨迹数据
        </button>
      </aside>

      <section className="proto-trajectory-map-panel">
        <div className="proto-canvas-grid" />
        <svg className="proto-trajectory-svg" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
          <path d="M16,24 L32,34 L38,45 L58,40 L50,68 L28,82 L12,74" />
        </svg>
        {[
          ['园区广场', 20, 30, 120, 80],
          ['1号楼', 45, 25, 100, 70],
          ['地下车库', 70, 60, 110, 80],
          ['东门', 5, 45, 80, 60],
          ['A座大厅', 30, 15, 80, 60],
          ['电梯间', 55, 35, 80, 50],
          ['餐厅', 30, 65, 100, 60],
          ['西门', 5, 75, 80, 60],
        ].map(([label, left, top, width, height]) => (
          <div
            className="proto-map-building"
            key={label}
            style={{ left: `${left}%`, top: `${top}%`, width: `${width}px`, height: `${height}px` }}
          >
            {label}
          </div>
        ))}
        {prototypeTrajectoryPoints.map((point, index) => (
          <button
            className={`proto-trajectory-point ${point.type} ${activePoint === index ? 'active' : ''}`}
            key={point.id}
            type="button"
            style={{ left: `${point.left}%`, top: `${point.top}%` }}
            onClick={() => setActivePoint(index)}
          >
            {point.label}
          </button>
        ))}
        <div className="proto-map-legend">
          <span><i className="start" />起点</span>
          <span><i />途经点</span>
          <span><i className="end" />终点</span>
          <span><b />轨迹线</span>
        </div>
      </section>

      <aside className="proto-trajectory-timeline">
        <div className="proto-timeline-head">
          <h3>轨迹时间轴</h3>
          <span>{prototypeTrajectoryPoints.length}个轨迹点</span>
        </div>
        <div className="proto-timeline-list">
          {prototypeTrajectoryPoints.map((point, index) => (
            <button
              className={`proto-timeline-item ${point.type} ${activePoint === index ? 'active' : ''}`}
              key={point.id}
              type="button"
              onClick={() => setActivePoint(index)}
            >
              <i>{point.label}</i>
              <span>
                <strong>{point.title}</strong>
                <time>{point.time}</time>
                <small>{point.desc}</small>
                <em>{point.tag}</em>
              </span>
            </button>
          ))}
        </div>
      </aside>
    </div>
  );
}
