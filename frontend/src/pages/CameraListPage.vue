<template>
  <section class="content review-wide video-management-page">
    <div class="review-titlebar"><div><h1>视频管理</h1><p>统一管理 IPC、NVR 等编码设备，支持主流厂商与协议接入</p></div></div>
    <div class="video-device-layout">
      <aside class="panel video-region-panel">
        <div class="video-region-head"><span>组织区域</span><button type="button" title="新增区域" aria-label="新增区域" @click="showToast('新增区域窗口已模拟打开')">＋</button></div>
        <input class="input video-region-search" placeholder="请输入组织名称" aria-label="搜索组织区域" />
        <ul class="video-region-tree">
          <li v-for="region in regions" :key="region.name"><button class="video-region-node" :class="{ child: region.child, active: activeArea === region.name }" @click="activeArea = region.name"><span>{{ region.child ? '└ ' : '▾ ' }}{{ region.name }}</span><em>{{ region.count }}</em></button></li>
        </ul>
      </aside>
      <div class="video-device-main">
        <div class="review-board video-device-board">
          <div class="video-device-filter">
            <label>设备名称<input class="input" v-model.trim="nameQuery" placeholder="请输入设备名称/编号/IP" /></label>
            <label>接入协议<select class="select" v-model="protocolFilter"><option>全部协议</option><option>海康 SDK</option><option>大华 SDK</option><option>GB28181</option><option>ONVIF</option><option>Ehome / ISUP 5.0</option><option>RTSP 拉流</option><option>RTMP 推流</option><option>GA/T 1400</option></select></label>
            <label>在线状态<select class="select" v-model="statusFilter"><option>全部状态</option><option>在线</option><option>离线</option><option>未成功连接</option><option>停用</option></select></label>
            <label>厂商<select class="select" v-model="vendorFilter"><option>全部厂商</option><option>海康威视</option><option>大华</option><option>宇视</option><option>华为</option><option>其他</option></select></label>
            <button class="btn primary" @click="loadCameras">查询</button>
            <button class="btn" @click="nameQuery = ''; protocolFilter = '全部协议'; statusFilter = '全部状态'; vendorFilter = '全部厂商'; activeQuickTab = 'all'">重置</button>
          </div>
          <div class="video-device-toolbar">
            <div class="video-device-toolbar-actions"><button class="btn primary" @click="setRoute('mediaDeviceWizard')">＋ 新增</button><button class="btn" @click="openModal('mediaCloud')">云平台同步</button><button class="btn" @click="openModal('mediaImport')">⇧ 批量导入</button><button class="btn" @click="openModal('mediaSmartDiscover')">✦ 智能发现</button><button class="btn" @click="openModal('mediaExport')">⇩ 导出</button><button class="btn" @click="openModal('mediaMove')">⇄ 批量设备移动</button><button class="btn" @click="openModal('mediaCapability')">⚙ 能力配置</button><button class="btn danger" @click="openModal('mediaDelete')">删除</button></div>
            <label class="video-device-include"><input type="checkbox" v-model="includeChildren" />包含下级区域设备</label>
          </div>
          <div class="video-device-tabs"><button v-for="tab in quickTabs" :key="tab.key" class="video-device-tab" :class="{ active: activeQuickTab === tab.key }" @click="activeQuickTab = tab.key">{{ tab.label }} {{ tab.count }}</button></div>
          <div class="video-device-table-wrap">
            <table class="prototype-table video-device-table">
              <colgroup><col style="width:42px;" /><col style="width:180px;" /><col style="width:125px;" /><col style="width:130px;" /><col style="width:165px;" /><col style="width:190px;" /><col style="width:180px;" /><col style="width:145px;" /><col style="width:86px;" /><col style="width:105px;" /><col style="width:130px;" /></colgroup>
              <thead><tr><th><input type="checkbox" aria-label="全选设备" /></th><th class="left">设备名称</th><th>所在区域</th><th>接入协议</th><th>IP地址及端口</th><th>设备编号</th><th>设备序列号</th><th class="left">描述</th><th>密码强度</th><th>状态</th><th>操作</th></tr></thead>
              <tbody>
                <tr v-for="row in visibleCameras" :key="row.code">
                  <td><input type="checkbox" :aria-label="'选择设备' + row.name" /></td><td class="left video-device-name">{{ row.name }}</td><td>{{ row.area }}</td><td>{{ row.protocol }}</td><td>{{ row.address }}</td><td>{{ row.code }}</td><td>{{ row.serial }}</td><td class="left ellipsis">{{ row.desc }}</td><td><span class="password-strength" :class="row.strengthClass">{{ row.strength }}</span></td><td><span class="status-pill" :class="statusClass(row.status)">{{ row.status }}</span></td><td><div class="video-device-row-actions"><button class="link-blue" @click="setRoute('mediaDeviceDetail')">查看</button><button class="link-blue" @click="setRoute('mediaDeviceEdit')">编辑</button><button class="link-red" @click="openModal('mediaDelete', row)">删除</button></div></td>
                </tr>
                <tr v-if="!visibleCameras.length"><td colspan="11">{{ loading ? '设备列表加载中…' : '暂无符合条件的设备' }}</td></tr>
              </tbody>
            </table>
          </div>
          <div class="table-footer video-device-footer"><span>显示 1-{{ visibleCameras.length }} 共 69 条记录</span><div class="pagination"><button class="page-btn">上一页</button><button class="page-btn active">1</button><button class="page-btn">2</button><button class="page-btn">3</button><button class="page-btn">下一页</button><select class="select" style="width:92px;"><option>10条/页</option><option>20条/页</option><option>50条/页</option></select></div></div>
        </div>
      </div>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { api } from "../api";
import type { Camera } from "../types";

function guessProtocol(sourceUrl: string): string {
  const url = (sourceUrl || "").toLowerCase();
  if (url.startsWith("rtsp://")) return "RTSP 拉流";
  if (url.startsWith("rtmp://")) return "RTMP 推流";
  if (url.startsWith("http://") || url.startsWith("https://")) return "ONVIF";
  return "其他";
}

function extractAddress(sourceUrl: string): string {
  try {
    const url = new URL(sourceUrl);
    return url.port ? `${url.hostname}:${url.port}` : url.hostname;
  } catch {
    return sourceUrl || "-";
  }
}

function statusLabel(status: string): string {
  const value = (status || "").toUpperCase();
  if (value === "RUNNING") return "在线";
  if (value === "STOPPED") return "离线";
  if (value === "DISABLED") return "停用";
  return "未成功连接";
}

export default defineComponent({
  name: "CameraListPage",
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  inject: {
    openModal: { from: "openModal", default: (key: string, payload?: any) => {} },
    setRoute: { from: "setRoute", default: (route: string, options?: any) => {} },
    showToast: { from: "showToast", default: (m: string) => {} },
  },
  data() {
    return {
      activeArea: "园区总部",
      activeQuickTab: "all",
      includeChildren: true,
      nameQuery: "",
      protocolFilter: "全部协议",
      statusFilter: "全部状态",
      vendorFilter: "全部厂商",
      loading: false,
      regions: [
        { name: "园区总部", count: 69, child: false },
        { name: "A区", count: 24, child: false },
        { name: "A1栋", count: 8, child: true },
        { name: "A2栋", count: 9, child: true },
        { name: "A3栋", count: 7, child: true },
        { name: "B区", count: 31, child: false },
        { name: "B1栋", count: 11, child: true },
        { name: "B2栋", count: 12, child: true },
        { name: "B3栋", count: 8, child: true },
        { name: "停车场", count: 14, child: false }
      ],
      quickTabs: [
        { key: "all", label: "全部设备", count: 69 },
        { key: "online", label: "在线", count: 42 },
        { key: "offline", label: "离线", count: 18 },
        { key: "never", label: "从未连接成功", count: 6 },
        { key: "weak", label: "弱密码", count: 3 },
        { key: "disabled", label: "停用", count: 4 }
      ],
      cameras: [] as any[]
    };
  },
  computed: {
    visibleCameras(): any[] {
      return this.cameras.filter((row: any) => {
        const matchesQuery = !this.nameQuery || [row.name, row.code, row.address].some((value: string) => value.toLowerCase().includes(this.nameQuery.toLowerCase()));
        const matchesProtocol = this.protocolFilter === "全部协议" || row.protocol === this.protocolFilter;
        const matchesStatus = this.statusFilter === "全部状态" || row.status === this.statusFilter;
        const matchesVendor = this.vendorFilter === "全部厂商" || row.vendor === this.vendorFilter;
        const matchesQuick = this.activeQuickTab === "all"
          || (this.activeQuickTab === "online" && row.status === "在线")
          || (this.activeQuickTab === "offline" && row.status === "离线")
          || (this.activeQuickTab === "never" && row.status === "未成功连接")
          || (this.activeQuickTab === "weak" && row.strength === "弱")
          || (this.activeQuickTab === "disabled" && row.status === "停用");
        return matchesQuery && matchesProtocol && matchesStatus && matchesVendor && matchesQuick;
      });
    }
  },
  methods: {
    mapCamera(camera: Camera, index: number) {
      return {
        id: camera.id,
        name: camera.name,
        area: camera.area || "未分配",
        protocol: guessProtocol(camera.sourceUrl),
        address: extractAddress(camera.sourceUrl),
        code: String(index + 1).padStart(4, "0"),
        serial: camera.id.slice(0, 12).toUpperCase(),
        desc: camera.description || "-",
        strength: "中",
        strengthClass: "medium",
        status: statusLabel(camera.status),
        vendor: "其他"
      };
    },
    async loadCameras() {
      this.loading = true;
      try {
        const list = await api.cameras();
        this.cameras = (list || []).map((camera: Camera, index: number) => this.mapCamera(camera, index));
      } catch (error: any) {
        this.showToast(`设备列表加载失败：${error?.message || error}`);
      } finally {
        this.loading = false;
      }
    }
  },
  mounted() {
    this.loadCameras();
  }
});
</script>
