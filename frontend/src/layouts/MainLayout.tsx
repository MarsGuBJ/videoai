import { NavLink, Outlet, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Camera,
  Tv,
  Bell,
  Cpu,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Square,
  ScanSearch,
  FileVideo,
  Images,
  Image,
  Route,
  ClipboardCheck,
  ClipboardList,
  Tags,
  Settings,
  MonitorCog,
  MonitorPlay,
  History,
  ShieldAlert,
  BrainCircuit,
  Gauge,
  Boxes,
  Radar,
  ChartColumnIncreasing,
  ListChecks,
  SlidersHorizontal,
  ShieldCheck,
  UsersRound,
  Logs,
  BotMessageSquare,
} from 'lucide-react';
import { useEffect, useState } from 'react';

type NavItem = {
  path: string;
  label: string;
  icon?: React.ReactNode;
  children?: NavItem[];
};

const navItems: NavItem[] = [
  { path: '/', label: '总览', icon: <LayoutDashboard size={17} /> },
  { path: '/sxin-assistant', label: 'SXin助手', icon: <BotMessageSquare size={17} /> },
  {
    path: '/omni-search', label: '万物搜', icon: <ScanSearch size={17} />,
    children: [
      {
        path: '/omni-search/text-video', label: '文搜视频', icon: <FileVideo size={17} />,
      },
      { path: '/omni-search/text-image', label: '文搜图', icon: <Image size={17} /> },
      { path: '/omni-search/image-image', label: '图搜图', icon: <Images size={17} /> },
      { path: '/omni-search/tracking', label: '轨迹还原', icon: <Route size={17} /> },
    ],
  },
  {
    path: '/omni-review', label: '万物核', icon: <ClipboardCheck size={17} />,
    children: [
      { path: '/omni-review/tasks', label: '任务管理', icon: <ClipboardList size={17} /> },
      { path: '/omni-review/types', label: '复核类型管理', icon: <Tags size={17} /> },
    ],
  },
  {
    path: '/algo-deploy', label: '算法布控', icon: <Cpu size={17} />,
    children: [
      { path: '/algo-deploy/algorithms', label: '算法管理', icon: <Boxes size={17} /> },
      { path: '/algo-deploy/tasks', label: '布控任务', icon: <Radar size={17} /> },
    ],
  },
  {
    path: '/visual-events', label: '视觉事件', icon: <Bell size={17} />,
    children: [
      { path: '/visual-events/statistics', label: '事件统计', icon: <ChartColumnIncreasing size={17} /> },
      { path: '/visual-events/list', label: '事件列表', icon: <ListChecks size={17} /> },
    ],
  },
  {
    path: '/basic-config', label: '基础配置', icon: <Settings size={17} />,
    children: [
      {
        path: '/basic-config/video', label: '视频管理', icon: <MonitorCog size={17} />,
        children: [
          { path: '/devices', label: '设备管理', icon: <Camera size={17} /> },
          { path: '/live', label: '实时预览', icon: <MonitorPlay size={17} /> },
          { path: '/playback', label: '录像回放', icon: <History size={17} /> },
          { path: '/tvwall', label: '电视墙', icon: <Tv size={17} /> },
          { path: '/alarm', label: '告警联动', icon: <ShieldAlert size={17} /> },
        ],
      },
      {
        path: '/basic-config/large-model', label: '大模型配置', icon: <BrainCircuit size={17} />,
      },
      { path: '/basic-config/events', label: '事件配置', icon: <SlidersHorizontal size={17} /> },
      { path: '/basic-config/large-model/resources', label: '资源监控', icon: <Gauge size={17} /> },
      { path: '/system-modules/permissions', label: '权限中心', icon: <ShieldCheck size={17} /> },
      { path: '/system-modules/users', label: '用户中心', icon: <UsersRound size={17} /> },
      { path: '/system-modules/logs', label: '日志管理', icon: <Logs size={17} /> },
    ],
  },
];

function NavItemComponent({ item, depth = 0 }: { item: NavItem; depth?: number }) {
  const location = useLocation();
  const hasChildren = item.children && item.children.length > 0;
  const isActive = isItemActive(item, location.pathname);
  const [expanded, setExpanded] = useState(isActive);

  useEffect(() => {
    if (isActive) {
      setExpanded(true);
    }
  }, [isActive]);

  return (
    <div className="nav-group">
      <NavLink
        to={item.path}
        end={!hasChildren}
        className={() => `nav-link nav-depth-${Math.min(depth, 4)} ${isActive ? 'active' : ''}`}
        onClick={() => hasChildren && setExpanded(e => !e)}
      >
        <span className="nav-icon">{item.icon || <Square size={15} />}</span>
        <span className="nav-label">{item.label}</span>
        {hasChildren && (
          <span className="nav-chevron">
            {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </span>
        )}
      </NavLink>
      {hasChildren && expanded && (
        <div className="nav-children">
          {item.children!.map(child => (
            <NavItemComponent key={child.path} item={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

function isItemActive(item: NavItem, pathname: string): boolean {
  if (item.path === '/') {
    return pathname === '/';
  }
  if (pathname === item.path || pathname.startsWith(`${item.path}/`)) {
    return true;
  }
  return item.children?.some(child => isItemActive(child, pathname)) ?? false;
}

export function MainLayout() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  return (
    <main className="app">
      <header className="app-header">
        <div className="header-brand">
          <div className="header-brand-mark"><img src="/sdlogo.png" alt="" aria-hidden="true" /></div>
          <div className="header-brand-copy">
            <h1>视觉大模型平台</h1>
            <p>Vision AI Platform</p>
          </div>
        </div>
        <div className="header-actions">
          <span className="header-status"><i aria-hidden="true" />系统在线</span>
          <button className="header-icon-btn" type="button" aria-label="消息提醒"><Bell size={18} /></button>
          <button className="header-icon-btn" type="button" aria-label="系统设置"><Settings size={18} /></button>
          <div className="header-user">
            <span>管理员</span>
            <b>AD</b>
          </div>
        </div>
      </header>
      <div className={`main-container ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
        <aside className="sidebar" aria-hidden={sidebarCollapsed}>
          <nav className="nav">
            {navItems.map(item => (
              <NavItemComponent key={item.path} item={item} />
            ))}
          </nav>
          <div className="sidebar-summary" aria-label="系统概览">
            <div className="sidebar-stat-card">
              <div className="sidebar-stat-header">
                <span className="sidebar-status-dot online" aria-hidden="true" />
                <span>在线设备</span>
              </div>
              <strong>22</strong>
            </div>
            <div className="sidebar-stat-card">
              <div className="sidebar-stat-header">
                <span className="sidebar-status-dot danger" aria-hidden="true" />
                <span>今日告警</span>
              </div>
              <strong className="danger">24</strong>
            </div>
          </div>
        </aside>
        <button
          className="sidebar-toggle-float"
          type="button"
          aria-label={sidebarCollapsed ? '展开左侧菜单' : '收起左侧菜单'}
          title={sidebarCollapsed ? '展开左侧菜单' : '收起左侧菜单'}
          onClick={() => setSidebarCollapsed(collapsed => !collapsed)}
        >
          {sidebarCollapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
        </button>
        <section className="workspace">
          <Outlet />
        </section>
      </div>
    </main>
  );
}
