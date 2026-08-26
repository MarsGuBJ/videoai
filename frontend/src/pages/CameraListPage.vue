<template>
  <section class="content review-wide video-management-page">
    <div class="review-titlebar"><div><h1>视频管理</h1><p>统一管理 IPC、NVR 等编码设备，支持主流厂商与协议接入</p></div></div>
    <div class="video-device-layout">
      <aside class="panel video-region-panel">
        <div class="video-region-head"><span>组织区域</span></div>
        <input class="input video-region-search" placeholder="请输入组织名称" aria-label="搜索组织区域" v-model.trim="regionQuery" />
        <ul class="video-region-tree">
          <li><button class="video-region-node" :class="{ active: activeArea === '' }" @click="activeArea = ''"><span>▾ 全部</span><em>{{ cameras.length }}</em></button></li>
          <li v-for="region in regions" :key="region.fullPath"><button class="video-region-node" :class="{ child: region.child, active: activeArea === region.fullPath }" @click="activeArea = region.fullPath"><span>{{ region.child ? '└ ' : '▾ ' }}{{ region.name }}</span><em>{{ region.count }}</em></button></li>
        </ul>
      </aside>
      <div class="video-device-main">
        <div class="review-board video-device-board">
          <div class="video-device-filter">
            <label>设备名称<input class="input" v-model.trim="nameQuery" placeholder="请输入设备名称/编号/IP" /></label>
            <label>接入协议<select class="select" v-model="protocolFilter"><option>全部协议</option><option>海康 SDK</option><option>大华 SDK</option><option>GB28181</option><option>ONVIF</option><option>Ehome / ISUP 5.0</option><option>RTSP 拉流</option><option>RTMP 推流</option><option>HTTP 拉流</option><option>GA/T 1400</option></select></label>
            <label>在线状态<select class="select" v-model="statusFilter"><option>全部状态</option><option>在线</option><option>离线</option><option>未成功连接</option><option>停用</option></select></label>
            <label>厂商<select class="select" v-model="vendorFilter"><option>全部厂商</option><option>海康威视</option><option>大华</option><option>宇视</option><option>华为</option><option>其他</option></select></label>
            <button class="btn primary" @click="loadCameras">查询</button>
            <button class="btn" @click="resetFilters">重置</button>
          </div>
          <div class="video-device-toolbar">
            <div class="video-device-toolbar-actions"><button class="btn primary" @click="setRoute('mediaDeviceWizard')">＋ 新增</button><button class="btn" @click="openModal('mediaCloud')">云平台同步</button><button class="btn" @click="openModal('mediaImport')">⇧ 批量导入</button><button class="btn" @click="openModal('mediaSmartDiscover')">✦ 智能发现</button><button class="btn" @click="exportDevices">⇩ 导出</button><button class="btn" @click="moveSelected">⇄ 批量设备移动</button><button class="btn" @click="openModal('mediaCapability')">⚙ 能力配置</button><button class="btn danger" @click="deleteSelected">删除</button></div>
            <label class="video-device-include"><input type="checkbox" v-model="includeChildren" />包含下级区域设备</label>
          </div>
          <div class="video-device-tabs"><button v-for="tab in quickTabs" :key="tab.key" class="video-device-tab" :class="{ active: activeQuickTab === tab.key }" @click="activeQuickTab = tab.key">{{ tab.label }} {{ tab.count }}</button></div>
          <div class="video-device-table-wrap">
            <table class="prototype-table video-device-table">
              <colgroup><col style="width:42px;" /><col style="width:180px;" /><col style="width:125px;" /><col style="width:130px;" /><col style="width:165px;" /><col style="width:190px;" /><col style="width:180px;" /><col style="width:145px;" /><col style="width:86px;" /><col style="width:105px;" /><col style="width:130px;" /></colgroup>
              <thead><tr><th><input type="checkbox" aria-label="全选设备" :checked="allPageSelected" @change="toggleSelectAll" /></th><th class="left">设备名称</th><th>所在区域</th><th>接入协议</th><th>IP地址及端口</th><th>设备编号</th><th>设备序列号</th><th class="left">描述</th><th>密码强度</th><th>状态</th><th>操作</th></tr></thead>
              <tbody>
                <tr v-for="row in pagedCameras" :key="row.id">
                  <td><input type="checkbox" v-model="selectedIds" :value="row.id" :aria-label="'选择设备' + row.name" /></td><td class="left video-device-name">{{ row.name }}</td><td>{{ row.area }}</td><td>{{ row.protocol }}</td><td>{{ row.address }}</td><td>{{ row.code }}</td><td>{{ row.serial }}</td><td class="left ellipsis">{{ row.desc }}</td><td><span class="password-strength" :class="row.strengthClass">{{ row.strength }}</span></td><td><span class="status-pill" :class="statusClass(row.status)">{{ row.status }}</span></td><td><div class="video-device-row-actions"><button class="link-blue" @click="openCameraDetail(row.raw)">查看</button><button class="link-blue" @click="openCameraEdit(row.raw)">编辑</button><button class="link-blue" @click="toggleStartStop(row)">{{ row.rawStatus === 'RUNNING' ? '下线' : '上线' }}</button><button class="link-red" @click="openModal('mediaDelete', { rows: [row] })">删除</button></div></td>
                </tr>
                <tr v-if="!pagedCameras.length"><td colspan="11">{{ loading ? '设备列表加载中…' : '暂无符合条件的设备' }}</td></tr>
              </tbody>
            </table>
          </div>
          <div class="table-footer video-device-footer"><span>显示 {{ rangeStart }}-{{ rangeEnd }} 共 {{ filteredCameras.length }} 条记录</span><div class="pagination"><button class="page-btn" :disabled="page <= 1" @click="page = page - 1">上一页</button><template v-for="(p, index) in pageNumbers" :key="index"><span v-if="p === '…'" class="page-btn" style="border:0;cursor:default;">…</span><button v-else class="page-btn" :class="{ active: page === p }" @click="page = Number(p)">{{ p }}</button></template><button class="page-btn" :disabled="page >= totalPages" @click="page = page + 1">下一页</button><select class="select" style="width:92px;" v-model.number="pageSize"><option :value="10">10条/页</option><option :value="20">20条/页</option><option :value="50">50条/页</option></select></div></div>
        </div>
      </div>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { api } from "../api";
import type { Camera } from "../types";
import { statusClass } from "../utils/prototype-helpers";
import { buildRegionTree, loadCustomRegions, passwordStrength } from "../utils/regions";
import type { RegionNode } from "../utils/regions";

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
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm", "selectedCamera"],
  inject: {
    openModal: { from: "openModal", default: (key: string, payload?: any) => {} },
    setRoute: { from: "setRoute", default: (route: string, options?: any) => {} },
    showToast: { from: "showToast", default: (m: string) => {} },
    openCameraDetailImpl: { from: "openCameraDetail", default: (row: any) => {} },
    openCameraEditImpl: { from: "openCameraEdit", default: (row: any) => {} },
    refreshCameras: { from: "refreshCameras", default: () => {} }
  },
  data() {
    return {
      activeArea: "",
      activeQuickTab: "all",
      includeChildren: true,
      nameQuery: "",
      protocolFilter: "全部协议",
      statusFilter: "全部状态",
      vendorFilter: "全部厂商",
      regionQuery: "",
      selectedIds: [] as string[],
      page: 1,
      pageSize: 10,
      loading: false,
      customRegions: [] as string[],
      cameras: [] as any[]
    };
  },
  computed: {
    regionNodes(): RegionNode[] {
      const areas = this.cameras.map((row: any) => row.area).filter((area: string) => area && area !== "未分配");
      return buildRegionTree(areas, this.customRegions);
    },
    regions(): RegionNode[] {
      if (!this.regionQuery) return this.regionNodes;
      const query = this.regionQuery.toLowerCase();
      return this.regionNodes.filter((node) => node.name.toLowerCase().includes(query));
    },
    regionPaths(): string[] {
      return this.regionNodes.map((node) => node.fullPath);
    },
    quickTabs(): any[] {
      const rows = this.cameras;
      return [
        { key: "all", label: "全部设备", count: rows.length },
        { key: "online", label: "在线", count: rows.filter((row: any) => row.status === "在线").length },
        { key: "offline", label: "离线", count: rows.filter((row: any) => row.status === "离线").length },
        { key: "never", label: "从未连接成功", count: rows.filter((row: any) => row.status === "未成功连接").length },
        { key: "weak", label: "弱密码", count: rows.filter((row: any) => row.strength === "弱").length },
        { key: "disabled", label: "停用", count: rows.filter((row: any) => row.status === "停用").length }
      ];
    },
    filteredCameras(): any[] {
      return this.cameras.filter((row: any) => {
        const matchesQuery = !this.nameQuery || [row.name, row.code, row.address].some((value: string) => String(value).toLowerCase().includes(this.nameQuery.toLowerCase()));
        const matchesProtocol = this.protocolFilter === "全部协议" || row.protocol === this.protocolFilter;
        const matchesStatus = this.statusFilter === "全部状态" || row.status === this.statusFilter;
        const matchesVendor = this.vendorFilter === "全部厂商" || row.vendor === this.vendorFilter;
        const matchesArea = !this.activeArea
          || (this.includeChildren
            ? row.area === this.activeArea || String(row.area).startsWith(this.activeArea + " / ")
            : row.area === this.activeArea);
        const matchesQuick = this.activeQuickTab === "all"
          || (this.activeQuickTab === "online" && row.status === "在线")
          || (this.activeQuickTab === "offline" && row.status === "离线")
          || (this.activeQuickTab === "never" && row.status === "未成功连接")
          || (this.activeQuickTab === "weak" && row.strength === "弱")
          || (this.activeQuickTab === "disabled" && row.status === "停用");
        return matchesQuery && matchesProtocol && matchesStatus && matchesVendor && matchesArea && matchesQuick;
      });
    },
    totalPages(): number {
      return Math.max(1, Math.ceil(this.filteredCameras.length / this.pageSize));
    },
    pagedCameras(): any[] {
      const page = Math.min(this.page, this.totalPages);
      return this.filteredCameras.slice((page - 1) * this.pageSize, page * this.pageSize);
    },
    pageNumbers(): any[] {
      const total = this.totalPages;
      const current = Math.min(this.page, total);
      if (total <= 7) return Array.from({ length: total }, (_value, index) => index + 1);
      const pages: any[] = [1];
      const start = Math.max(2, current - 1);
      const end = Math.min(total - 1, current + 1);
      if (start > 2) pages.push("…");
      for (let p = start; p <= end; p += 1) pages.push(p);
      if (end < total - 1) pages.push("…");
      pages.push(total);
      return pages;
    },
    rangeStart(): number {
      if (!this.filteredCameras.length) return 0;
      return (Math.min(this.page, this.totalPages) - 1) * this.pageSize + 1;
    },
    rangeEnd(): number {
      return Math.min(Math.min(this.page, this.totalPages) * this.pageSize, this.filteredCameras.length);
    },
    selectedRows(): any[] {
      return this.cameras.filter((row: any) => this.selectedIds.includes(row.id));
    },
    allPageSelected(): boolean {
      return this.pagedCameras.length > 0 && this.pagedCameras.every((row: any) => this.selectedIds.includes(row.id));
    },
    filterKey(): string {
      return [this.nameQuery, this.protocolFilter, this.statusFilter, this.vendorFilter, this.activeArea, this.includeChildren, this.activeQuickTab, this.pageSize].join("|");
    }
  },
  watch: {
    filterKey() {
      this.page = 1;
    },
    "state.camerasVersion"() {
      this.customRegions = loadCustomRegions();
      this.loadCameras();
    }
  },
  methods: {
    statusClass,
    // Aliased injections (openCameraDetailImpl/openCameraEditImpl) re-exposed as
    // same-named methods so the template calls type-check, matching the
    // wrapper pattern used by other pages.
    openCameraDetail(row: any) {
      (this as any).openCameraDetailImpl(row);
    },
    openCameraEdit(row: any) {
      (this as any).openCameraEditImpl(row);
    },
    mapCamera(camera: Camera) {
      const strength = passwordStrength(camera.password);
      return {
        id: camera.id,
        name: camera.name,
        area: camera.area || "未分配",
        protocol: camera.protocol || guessProtocol(camera.sourceUrl),
        address: camera.ip ? `${camera.ip}${camera.port ? `:${camera.port}` : ""}` : extractAddress(camera.sourceUrl),
        code: camera.deviceCode || "-",
        serial: camera.serialNumber || "-",
        desc: camera.description || "-",
        strength: strength.label,
        strengthClass: strength.cls,
        status: statusLabel(camera.status),
        rawStatus: camera.status,
        vendor: camera.vendor || "其他",        raw: camera
      };
    },
    async loadCameras() {
      this.loading = true;
      try {
        const list = await api.cameras();
        this.cameras = (list || []).map((camera: Camera) => this.mapCamera(camera));
      } catch (error: any) {
        this.showToast(`设备列表加载失败：${error?.message || error}`);
      } finally {
        this.loading = false;
      }
    },
    resetFilters() {
      this.nameQuery = "";
      this.protocolFilter = "全部协议";
      this.statusFilter = "全部状态";
      this.vendorFilter = "全部厂商";
      this.activeQuickTab = "all";
    },
    toggleSelectAll(event: any) {
      const pageIds = this.pagedCameras.map((row: any) => row.id);
      if (event.target.checked) {
        this.selectedIds = Array.from(new Set([...this.selectedIds, ...pageIds]));
      } else {
        this.selectedIds = this.selectedIds.filter((id: string) => !pageIds.includes(id));
      }
    },
    async toggleStartStop(row: any) {
      try {
        if (row.rawStatus === "RUNNING") {
          await api.stopCamera(row.id);
          this.showToast(`设备「${row.name}」已下线`);
        } else {
          await api.startCamera(row.id);
          this.showToast(`设备「${row.name}」已上线`);
        }
      } catch (error: any) {
        this.showToast(`操作失败：${error?.message || error}`);
      } finally {
        this.loadCameras();
      }
    },
    deleteSelected() {
      if (!this.selectedRows.length) {
        this.showToast("请先选择设备");
        return;
      }
      this.openModal("mediaDelete", { rows: this.selectedRows });
    },
    moveSelected() {
      if (!this.selectedRows.length) {
        this.showToast("请先选择设备");
        return;
      }
      this.openModal("mediaMove", { rows: this.selectedRows, areas: this.regionPaths });
    },
    exportDevices() {
      this.openModal("mediaExport", {
        filtered: this.filteredCameras.map((row: any) => row.raw),
        selected: this.selectedRows.map((row: any) => row.raw),
        all: this.cameras.map((row: any) => row.raw)
      });
    }
  },
  mounted() {
    this.customRegions = loadCustomRegions();
    this.loadCameras();
  }
});
</script>
