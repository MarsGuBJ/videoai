<template>
        <section class="content review-wide media-wall-page">
          <div class="review-titlebar"><div><h1>电视墙</h1><p>配置电视墙、拼控墙、报警上墙预案与网络键盘控制，支持上墙预览和通道绑定</p></div><button class="btn primary" @click="showToast('电视墙配置已模拟保存')">保存配置</button></div>
          <div class="media-wall-layout">
            <aside class="panel media-wall-sidebar">
              <div class="media-side-menu"><button v-for="tab in wallTabs" :key="tab.key" :class="{ active: activeWallTab === tab.key }" @click="activeWallTab = tab.key">{{ tab.label }}</button></div>
              <input class="input" placeholder="搜索电视墙/预案/键盘" aria-label="搜索电视墙配置" />
              <div class="media-ptz-section"><div class="media-panel-head"><b>电视墙列表</b><button class="link-blue" @click="openModal('tvWall')">＋</button></div><ul class="media-plan-list"><li class="active"><b>指挥中心主墙</b><span>4x4 · 16窗口 · 8路解码</span></li><li><b>园区安防副墙</b><span>3x3 · 9窗口 · 4路解码</span></li><li><b>应急联动墙</b><span>2x2 · 报警优先</span></li></ul></div>
              <div class="media-ptz-section"><div class="media-panel-head"><b>报警预案</b><span class="status-pill pass">启用 6</span></div><ul class="media-plan-list"><li><b>周界入侵上墙</b><span>窗口 1 · 停留 30 秒</span></li><li><b>门禁强开联动</b><span>窗口 4 · 停留 20 秒</span></li></ul></div>
            </aside>
            <main class="media-wall-main">
              <div class="media-summary-row"><div class="media-summary-item"><b>3</b><span>电视墙</span></div><div class="media-summary-item"><b>2</b><span>拼控设备</span></div><div class="media-summary-item"><b>8</b><span>报警预案</span></div><div class="media-summary-item"><b>4</b><span>网络键盘</span></div></div>
              <section v-if="activeWallTab === 'wallConfig'" class="panel media-wall-panel"><div class="media-wall-toolbar"><div class="media-control-buttons"><button class="btn primary" @click="openModal('tvWall')">＋ 添加电视墙</button><button class="btn" @click="openModal('wallPreview')">预览配置</button><button class="btn">批量绑定</button></div><input class="input" style="width:190px;" placeholder="请输入电视墙名称" /></div><div class="media-wall-config-grid"><div><div class="media-panel-head"><b>指挥中心主墙</b><span>布局 4x4 · 3840x2160</span></div><div class="media-wall-canvas"><div v-for="item in wallWindows" :key="item.number" class="media-wall-window" :class="{ active: item.number === 1 }">{{ item.number }}<br />{{ item.source }}</div></div></div><div class="media-wall-table-wrap"><div class="media-panel-head"><b>解码通道绑定</b><button class="link-blue">自动匹配</button></div><table class="prototype-table media-wall-table"><thead><tr><th>窗口</th><th>解码设备</th><th>解码通道</th><th>信号源</th><th>状态</th></tr></thead><tbody><tr><td>1</td><td>DEC-01</td><td>HDMI-1</td><td>北门卡口 IPC-07</td><td><span class="status-pill pass">已绑定</span></td></tr><tr><td>2</td><td>DEC-01</td><td>HDMI-2</td><td>A1栋入口 IPC-01</td><td><span class="status-pill pass">已绑定</span></td></tr><tr><td>3</td><td>DEC-02</td><td>HDMI-1</td><td>停车场 NVR-01</td><td><span class="status-pill waiting">待绑定</span></td></tr></tbody></table></div></div></section>
              <section v-else-if="activeWallTab === 'spliceConfig'" class="panel media-wall-panel"><div class="media-wall-toolbar"><div class="media-control-buttons"><button class="btn primary" @click="openModal('spliceWall')">＋ 添加拼控墙</button><button class="btn">输出通道绑定</button></div><select class="select" style="width:190px;"><option>LCD拼控控制器-01</option><option>LED拼接处理器-02</option></select></div><div class="media-wall-config-grid"><div><div class="media-panel-head"><b>LCD拼控墙</b><span>3行 x 4列 · 支持跨屏开窗</span></div><div class="media-splice-canvas"><div class="media-wall-window active">大屏窗口 A<br />输出 1-6</div><div class="media-wall-window">窗口 B<br />输出 7</div><div class="media-wall-window">窗口 C<br />输出 8</div><div class="media-wall-window">告警窗口 D<br />输出 9-10</div></div></div><div class="media-wall-table-wrap"><div class="media-panel-head"><b>输出通道绑定</b><button class="link-blue">刷新状态</button></div><table class="prototype-table media-wall-table"><thead><tr><th>输出口</th><th>物理屏</th><th>分辨率</th><th>拼接位置</th><th>状态</th></tr></thead><tbody><tr><td>OUT-01</td><td>屏幕 1</td><td>1920x1080</td><td>1行1列</td><td><span class="status-pill pass">正常</span></td></tr><tr><td>OUT-02</td><td>屏幕 2</td><td>1920x1080</td><td>1行2列</td><td><span class="status-pill pass">正常</span></td></tr><tr><td>OUT-09</td><td>屏幕 9</td><td>1920x1080</td><td>3行1列</td><td><span class="status-pill waiting">待校准</span></td></tr></tbody></table></div></div></section>
              <section v-else-if="activeWallTab === 'alarmWall'" class="panel media-wall-panel"><div class="media-wall-toolbar"><div class="media-control-buttons"><button class="btn primary" @click="openModal('alarmPlan')">＋ 新增预案</button><button class="btn" @click="openModal('alarmPlan')">编辑</button><button class="btn danger">批量删除</button></div><span class="hint-text">报警触发后按开窗设置自动上墙，并按停留时间轮转</span></div><div class="media-wall-table-wrap"><table class="prototype-table media-wall-table" style="min-width:820px;"><thead><tr><th>预案名称</th><th>报警类型</th><th>开窗位置</th><th>绑定信号源</th><th>停留时间</th><th>状态</th><th>操作</th></tr></thead><tbody><tr><td>周界入侵上墙</td><td>周界入侵</td><td>主墙 窗口1</td><td>周界球机 IPC-03</td><td>30秒</td><td><span class="status-pill pass">开启</span></td><td><button class="link-blue" @click="openModal('alarmPlan')">编辑</button></td></tr><tr><td>门禁强开联动</td><td>门禁异常</td><td>主墙 窗口4</td><td>A1入口 IPC-01</td><td>20秒</td><td><span class="status-pill pass">开启</span></td><td><button class="link-blue" @click="openModal('alarmPlan')">编辑</button></td></tr><tr><td>停车场夜间报警</td><td>区域入侵</td><td>副墙 窗口2</td><td>停车场 NVR-01</td><td>45秒</td><td><span class="status-pill reject">关闭</span></td><td><button class="link-blue" @click="openModal('alarmPlan')">编辑</button></td></tr></tbody></table></div></section>
              <section v-else-if="activeWallTab === 'keyboardConfig'" class="panel media-wall-panel"><div class="media-wall-toolbar"><div><h3 class="form-section-title">网络键盘接入</h3></div><button class="btn primary" @click="openModal('keyboardAccess')">指定接入</button></div><div class="media-wall-table-wrap"><table class="prototype-table media-wall-table"><thead><tr><th>键盘名称</th><th>IP地址</th><th>控制电视墙</th><th>状态</th><th>操作</th></tr></thead><tbody><tr><td>KB-指挥中心-01</td><td>192.168.88.21</td><td>指挥中心主墙</td><td><span class="status-pill pass">在线</span></td><td><button class="link-blue" @click="openModal('keyboardAccess')">控制</button></td></tr><tr><td>KB-值班室-02</td><td>192.168.88.22</td><td>园区安防副墙</td><td><span class="status-pill reject">离线</span></td><td><button class="link-blue" @click="openModal('keyboardAccess')">配置</button></td></tr></tbody></table></div><div class="video-device-filter" style="margin-top:14px;"><label>电视墙编号<input class="input" value="TVW-001" /></label><label>视频源编号规则<input class="input" value="SRC-{区域}-{序号}" /></label><label>轮巡组编号规则<input class="input" value="TOUR-{业务}-{序号}" /></label><label>控制权限<select class="select"><option>指定键盘可控</option><option>值班组可控</option><option>全部键盘可控</option></select></label></div></section>
              <section v-else class="panel media-wall-panel"><div class="media-wall-toolbar"><div class="media-layout-buttons"><span>信号源</span><button class="active">监控点</button><button>视图</button><button>巡航</button></div><div class="media-control-buttons"><button class="btn primary" @click="showToast('选中信号已模拟上墙')">上墙</button><button class="btn" @click="openModal('wallPreview')">保存预览配置</button><button class="btn">清空窗口</button></div></div><div class="media-wall-preview-stage"><div class="media-wall-window active">主墙 1<br />真实黄区球机</div><div class="media-wall-window">主墙 2<br />A1栋入口</div><div class="media-wall-window">主墙 3</div><div class="media-wall-window">主墙 4</div></div></section>
            </main>
          </div>
        </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";

export default defineComponent({
  name: "MediaWallPage",
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  // Prototype declares inject: ["openModal", "showToast"]; vue-tsc does not
  // surface injected members on the instance type, so they are injected under
  // aliases and exposed as same-named methods (behavior identical).
  inject: {
    openModalFn: { from: "openModal", default: (..._args: any[]) => {} },
    showToastFn: { from: "showToast", default: (..._args: any[]) => {} }
  },
  methods: {
    openModal(...args: any[]) {
      (this as any).openModalFn(...args);
    },
    showToast(...args: any[]) {
      (this as any).showToastFn(...args);
    }
  },
  data() {
    return {
      activeWallTab: "wallConfig",
      wallTabs: [
        { key: "wallConfig", label: "电视墙配置" },
        { key: "spliceConfig", label: "拼控设备配置" },
        { key: "alarmWall", label: "报警上墙" },
        { key: "keyboardConfig", label: "网络键盘" },
        { key: "wallPreview", label: "上墙预览" }
      ],
      wallWindows: Array.from({ length: 16 }, (_, index) => ({ number: index + 1, source: ["北门卡口", "A1入口", "停车场", "周界球机"][index] || "" }))
    };
  }
});
</script>
