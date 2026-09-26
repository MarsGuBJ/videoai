<script lang="ts">
import * as XLSX from "xlsx";
import { api, sameOriginAssetUrl } from "../api";
import type { RecordingSegment } from "../api";
import type { AccessGb28181Entry, Algorithm, AlgorithmEngine, Camera, CloudPlatform, CloudSyncPrecheck, EventInfo, FaceProfile, LlmConfig, NvrImportPrecheck, ReviewType } from "../types";
import { statusClass } from "../utils/prototype-helpers";
import { deviceStatusLabel, onlineStatusOf, streamStatusLabel } from "../utils/device-status";
import { loadPlayerSettings, resetPlayerSettings, savePlayerSettings } from "../utils/player-settings";
import { computeSourceUrl, flattenRegionTree, loadRegionTree } from "../utils/regions";
import { resolveEventAlgorithm } from "../utils/algorithm-binding";
import type { AlgorithmResolution } from "../utils/algorithm-binding";
import type { FlatRegionNode } from "../utils/regions";
import type { RegionTreeNode } from "../api";
import VideoPlayer from "./VideoPlayer.vue";

// 云平台同步弹窗中的合成选项：选中「国标GB28181」后改走级联服务器同步流程
const GB28181_OPTION_ID = "__gb28181__";

// 即时回放：与录像回放页同一口径，时间均按本地时区（北京时间）ISO 秒格式
function pad2(value: number): string {
  return String(value).padStart(2, "0");
}

function toLocalIsoSeconds(ms: number): string {
  const date = new Date(ms);
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}T${pad2(date.getHours())}:${pad2(date.getMinutes())}:${pad2(date.getSeconds())}`;
}

function parseLocalMs(value?: string): number {
  const ms = value ? new Date(value).getTime() : NaN;
  return Number.isNaN(ms) ? 0 : ms;
}

function formatMmSs(totalSeconds: number): string {
  const value = Math.max(0, Math.floor(totalSeconds));
  return `${pad2(Math.floor(value / 60))}:${pad2(value % 60)}`;
}

// 无录像提示弹窗中的查询时段：按北京时间展示到分钟
function formatDateTimeLabel(value?: string): string {
  const ms = parseLocalMs(value);
  if (!ms) return value || "-";
  const date = new Date(ms);
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())} ${pad2(date.getHours())}:${pad2(date.getMinutes())}`;
}

// 即时回放固定检索窗口：最近 30 分钟（规避 NVR 最新录像段落盘/索引延迟导致窄窗口检索为空）
const QUICK_REPLAY_SEARCH_WINDOW_MS = 30 * 60 * 1000;

export default {
  name: "ModalHost",
  components: { VideoPlayer },
  props: ["modal", "store", "state", "reviewTaskSubmitting"],
  emits: ["close", "submit"],
  // Aliased injection + same-named method wrapper for `showToast` (used in the
  // template, which is type-checked); runtime behavior matches the prototype's
  // `inject: ["showToast", "setRoute"]`. `setRoute` is only used in script.
  inject: {
    toastImpl: { from: "showToast" },
    setRoute: { from: "setRoute" },
    refreshCamerasImpl: { from: "refreshCameras", default: () => {} }
  },
  data() {
    return {
      videoSettings: loadPlayerSettings(),
      quickReplaySeconds: loadPlayerSettings().instantReplaySec,
      algorithmName: "",
      algorithmCode: "",
      algorithmEngineType: "",
      algorithmVersion: "v1.0.0",
      algorithmVersionName: "",
      algorithmNotes: "",
      algorithmDesc: "",
      algorithmScene: "",
      algorithmOwner: "",
      algorithmPackageFile: null as File | null,
      algorithmPackageName: "",
      algorithmEngines: [] as AlgorithmEngine[],
      algorithmEventInfos: [] as EventInfo[],
      deployTaskName: "",
      deployAlgorithmCode: "",
      deployRecognitionPerMinute: 10,
      deployEffectiveStart: "",
      deployEffectiveEnd: "",
      deployCycleStart: "00:00",
      deployCycleEnd: "23:59",
      deploySimilarity: 50,
      deployFaceProfileId: "",
      deployTargetFile: null as File | null,
      deployTargetImageUrl: "",
      deployTargetLocalPreview: "",
      deployFaceFilter: "",
      deployFaceDropdownOpen: false,
      deployDesc: "",
      deployAlgorithms: [] as Algorithm[],
      deployEventInfos: [] as EventInfo[],
      deployCameras: [] as Camera[],
      faceProfiles: [] as FaceProfile[],
      versionFileName: "",
      deployCameraTreeOpen: false,
      deploySelectedCameras: [] as string[],
      deployAreaExpanded: {} as Record<string, boolean>,
      importFile: null as File | null,
      importFileName: "",
      importBusy: false,
      importResult: null as any,
      exportRange: "filtered",
      exportFields: "all",
      moveArea: "",
      capabilityPtz: false,
      capabilityStrategy: "overwrite",
      capabilitySaving: false,
      // 云台能力探测进度与结果（不支持的设备会被跳过并在弹窗里列出明细）
      capabilityProbing: false,
      capabilityProgress: { done: 0, total: 0 },
      capabilityReport: null as null | {
        applied: number;
        ptzOn: boolean;
        total: number;
        skipped: { name: string; reason: string }[];
      },
      // 区域管理弹窗：后端区域树（/api/regions）树形编辑器
      regionTree: [] as RegionTreeNode[],
      regionSelectedId: "",
      regionRootNew: "",
      regionRenameValue: "",
      regionChildNew: "",
      regionSiblingNew: "",
      regionExpanded: {} as Record<string, boolean>,
      regionDragId: "",
      regionDropTargetId: "",
      regionDropPosition: "" as "" | "before" | "after",
      regionSpatialBaseUrl: "",
      regionSpatialSaving: false,
      regionSpatialSyncing: false,
      reviewLlmId: "",
      reviewLlmConfigs: [] as LlmConfig[],
      reviewTypeId: "",
      reviewTypeOptions: [] as ReviewType[],
      reviewImageFile: null as File | null,
      reviewImageName: "",
      reviewImageUrl: "",
      // 云平台同步设备弹窗
      cloudPlatforms: [] as CloudPlatform[],
      cloudPlatformId: "",
      gb28181Entries: [] as AccessGb28181Entry[],
      gb28181EntryId: "",
      cloudItems: [] as any[],
      cloudSummary: null as CloudSyncPrecheck | null,
      cloudBusy: false,
      cloudConflictStrategy: "overwrite",
      cloudTargetArea: "",
      cloudAreaOptions: [] as string[],
      // 从NVR/CVR导入弹窗
      nvrHostRows: [""] as string[],
      nvrUsername: "",
      nvrPassword: "",
      nvrItems: [] as any[],
      nvrSummary: null as NvrImportPrecheck | null,
      nvrBusy: false,
      nvrTargetArea: "",
      nvrAreaOptions: [] as string[],
      // 录像下载弹窗（上下文来自回放页 openModal('recordDownload', { camera, startTime, endTime })）
      recordDownloadStart: "",
      recordDownloadEnd: "",
      recordDownloadBusy: false,
      recordDownloadUrl: "",
      recordDownloadError: "",
      // 即时回放弹窗（上下文来自实时预览页 openModal('quickReplay', { camera })）
      quickReplayUrl: undefined as string | undefined,
      quickReplayError: "",
      quickReplayLoading: false,
      quickReplayCurrent: 0,
      quickReplayDuration: 0,
      quickReplayStartedAt: 0,
      // 即时回放实际起流的时间段（毫秒）：「切至历史录像」带入录像回放页直接播放
      quickReplayStartMs: 0,
      quickReplayEndMs: 0,
      quickReplayTimer: null as number | null,
      quickReplaySeq: 0
    };
  },
  computed: {
    isAlgorithmEdit(): boolean {
      return this.modal.type === "algorithm" && !!(this.modal.item && this.modal.item.id);
    },
    isDeployTaskEdit(): boolean {
      return this.modal.type === "deployTask" && !!(this.modal.item && this.modal.item.id);
    },
    deployCameraAreas(): { name: string; cameras: Camera[] }[] {
      const groups: Record<string, Camera[]> = {};
      this.deployCameras.forEach((camera) => {
        const area = camera.area || "未分配";
        if (!groups[area]) groups[area] = [];
        groups[area].push(camera);
      });
      return Object.keys(groups).map((name) => ({ name, cameras: groups[name] }));
    },
    // 算法编号下拉：选项来自事件信息配置，value 用事件信息的编码；
    // 选中后按其 algorithmCode 在算法列表中匹配出实际布控算法，事件未绑定算法
    // 编码时回落到「算法编号本身即算法编码」的算法（见 utils/algorithm-binding）。
    deploySelectedEventInfo(): EventInfo | undefined {
      return this.deployEventInfos.find((item) => item.code === this.deployAlgorithmCode);
    },
    deployAlgorithmResolution(): AlgorithmResolution {
      return resolveEventAlgorithm(this.deployAlgorithms, this.deployEventInfos, this.deployAlgorithmCode);
    },
    deploySelectedAlgorithm(): Algorithm | undefined {
      return this.deployAlgorithmResolution.algorithm;
    },
    // 算法编号下方的提示：让用户看清这次到底绑定了哪个算法，没绑上也要说清楚
    deployAlgorithmHint(): string {
      const resolution = this.deployAlgorithmResolution;
      if (!this.deployAlgorithmCode) return "";
      if (resolution.algorithm) return `已绑定算法：${resolution.algorithm.name}（${resolution.algorithm.code}）`;
      if (resolution.boundCode) {
        return `事件绑定的算法编码「${resolution.boundCode}」在算法管理中不存在：任务会照常创建，但 worker 不会启动算法`;
      }
      return "该事件未绑定可布控算法，且没有同编码的算法：任务会照常创建，但 worker 不会启动算法，请到「事件配置 → 事件信息配置」补充算法编码";
    },
    deployCameraSummary(): string {
      const count = this.deploySelectedCameras.length;
      if (!count) return "请选择摄像机（可多选）";
      const names = this.deployCameras
        .filter((camera) => this.deploySelectedCameras.includes(camera.id))
        .map((camera) => camera.name);
      return `已选 ${count} 台：${names.join("、")}`;
    },
    deploySelectedAreas(): string[] {
      const areas = this.deployCameras
        .filter((camera) => this.deploySelectedCameras.includes(camera.id))
        .map((camera) => camera.area || "未分配");
      return Array.from(new Set(areas));
    },
    // 快速布防带入的目标图：仅新建且从搜索页带图跳转时展示
    deployTargetImage(): string {
      return (!this.isDeployTaskEdit && this.state && this.state.prefill) || "";
    },
    // 布控目标预览：本地上传的 objectURL 优先，其次已选/回填的目标图 URL
    deployTargetPreview(): string {
      return this.deployTargetLocalPreview || this.deployTargetImageUrl;
    },
    deploySelectedFaceProfile(): FaceProfile | undefined {
      return this.faceProfiles.find((face) => face.id === this.deployFaceProfileId);
    },
    filteredFaceProfiles(): FaceProfile[] {
      const keyword = this.deployFaceFilter.trim().toLowerCase();
      const selected = this.deploySelectedFaceProfile;
      // 输入内容就是已选人姓名时视为未筛选，展示全部
      const list =
        !keyword || (selected && selected.name.toLowerCase() === keyword)
          ? this.faceProfiles
          : this.faceProfiles.filter((face) => face.name.toLowerCase().includes(keyword));
      return list.slice(0, 50);
    },
    deployTargetCrop(): any {
      return (this.state && this.state.imageCrop) || null;
    },
    deployTargetCropStyle(): Record<string, string> {
      const crop = this.deployTargetCrop || { x: 0, y: 0, width: 0, height: 0 };
      return {
        left: `${crop.x}%`,
        top: `${crop.y}%`,
        width: `${crop.width}%`,
        height: `${crop.height}%`
      };
    },
    submitLabel() {
      const labels: any = {
        reviewTask: this.reviewTaskSubmitting ? "提交中…" : "确定",
        mediaExport: "导出",
        mediaMove: "确认移动",
        mediaCapability: "批量保存",
        mediaDelete: "确认删除",
        customLayout: "保存布局",
        recordDownload: "下载"
      };
      return labels[this.modal.type] || "保存";
    },
    cloudCheckedItems(): any[] {
      return this.cloudItems.filter((item) => item.checked);
    },
    isGb28181Mode(): boolean {
      return this.cloudPlatformId === GB28181_OPTION_ID;
    },
    cloudAllChecked(): boolean {
      return this.cloudItems.length > 0 && this.cloudCheckedItems.length === this.cloudItems.length;
    },
    nvrCheckedItems(): any[] {
      return this.nvrItems.filter((item) => item.checked);
    },
    nvrAllChecked(): boolean {
      return this.nvrItems.length > 0 && this.nvrCheckedItems.length === this.nvrItems.length;
    },
    recordDownloadCamera(): any {
      return (this.modal.item && this.modal.item.camera) || null;
    },
    // 无录像提示弹窗（上下文来自回放页 openModal('recordEmpty', { camera, startTime, endTime })）
    recordEmptyCamera(): any {
      return (this.modal.item && this.modal.item.camera) || null;
    },
    recordEmptyCameraName(): string {
      const camera = this.recordEmptyCamera;
      return (camera && camera.name) || "所选设备";
    },
    recordEmptyRangeText(): string {
      const item = this.modal.item || {};
      return `${formatDateTimeLabel(item.startTime)} ~ ${formatDateTimeLabel(item.endTime)}`;
    },
    quickReplayCamera(): any {
      return (this.modal.item && this.modal.item.camera) || null;
    },
    quickReplayProgressText(): string {
      return `正在回放 ${formatMmSs(this.quickReplayCurrent)} / ${formatMmSs(this.quickReplayDuration)}`;
    },
    // --- 区域管理弹窗（区域树编辑器） ---
    regionFlatList(): FlatRegionNode[] {
      return flattenRegionTree(this.regionTree);
    },
    // 左侧树可见行：折叠节点的子孙不渲染；depth 用于 18px 逐级缩进
    regionRows(): { node: RegionTreeNode; fullPath: string; depth: number; hasChildren: boolean }[] {
      const rows: { node: RegionTreeNode; fullPath: string; depth: number; hasChildren: boolean }[] = [];
      const walk = (nodes: RegionTreeNode[], prefix: string, depth: number, hidden: boolean) => {
        for (const node of nodes || []) {
          const fullPath = prefix ? `${prefix} / ${node.name}` : node.name;
          if (!hidden) {
            rows.push({ node, fullPath, depth, hasChildren: !!(node.children && node.children.length) });
          }
          walk(node.children || [], fullPath, depth + 1, hidden || this.regionExpanded[fullPath] === false);
        }
      };
      walk(this.regionTree, "", 0, false);
      return rows;
    },
    regionSelected(): FlatRegionNode | null {
      if (!this.regionSelectedId) return null;
      return this.regionFlatList.find((item) => item.node.id === this.regionSelectedId) || null;
    },
    // 有子区域或已挂载设备的节点不可删除（后端同样返回 409，前端提前禁用并提示）
    regionDeletable(): boolean {
      const selected = this.regionSelected;
      return !!selected && !(selected.node.children && selected.node.children.length) && !selected.node.deviceCount;
    }

  },
  watch: {
    // 打开弹窗时重新读取设置，保证与上次保存/恢复默认后的值一致
    "modal.type"(type: string) {
      if (type === "videoConfig") this.videoSettings = loadPlayerSettings();
      if (type === "quickReplay") this.quickReplaySeconds = loadPlayerSettings().instantReplaySec;
    },
    // 弹窗打开状态下切换回放时长：按新时长重新查询并起流
    quickReplaySeconds() {
      if (this.modal.open && this.modal.type === "quickReplay") this.initQuickReplay();
    },
    moveArea(value: string) {
      // 批量设备移动：把选定的目标区域写回 modal.item，App.submitModal 的
      // mediaMove 分支在提交时读取它。
      if (this.modal && this.modal.item) this.modal.item.area = value;
    },
    deployAlgorithmCode() {
      // 切换算法后重置布控目标，避免人脸库错挂到其他引擎
      this.deployFaceProfileId = "";
      this.deployFaceFilter = "";
    },
    "modal.open"(open: boolean) {
      if (!open) {
        // 关闭上传复核任务弹窗时重置表单并释放图片预览 URL
        if (this.modal.type === "reviewTask") this.resetReviewTaskForm();
        // 关闭即时回放：停止进度计时并卸载回放流（v-if 卸载 VideoPlayer 自动 teardown）
        if (this.modal.type === "quickReplay") this.teardownQuickReplay();
        return;
      }
      if (this.modal.type === "algorithm") {
        this.initAlgorithmForm();
      } else if (this.modal.type === "deployTask") {
        this.initDeployTaskForm();
      } else if (this.modal.type === "mediaImport") {
        this.importFile = null;
        this.importFileName = "";
        this.importBusy = false;
        this.importResult = null;
        const input: any = this.$refs.importFileInput;
        if (input) input.value = "";
      } else if (this.modal.type === "mediaExport") {
        this.exportRange = "filtered";
        this.exportFields = "all";
      } else if (this.modal.type === "mediaMove") {
        const areas = (this.modal.item && this.modal.item.areas) || [];
        this.moveArea = areas[0] || "";
        if (this.modal.item) this.modal.item.area = this.moveArea;
      } else if (this.modal.type === "mediaCloud") {
        this.initCloudSync();
      } else if (this.modal.type === "mediaNvrImport") {
        this.initNvrImport();
      } else if (this.modal.type === "mediaCapability") {
        this.initCapabilityForm();
      } else if (this.modal.type === "mediaRegion") {
        this.regionSelectedId = "";
        this.regionRootNew = "";
        this.regionRenameValue = "";
        this.regionChildNew = "";
        this.regionSiblingNew = "";
        this.regionExpanded = {};
        this.regionDragId = "";
        this.regionDropTargetId = "";
        this.regionDropPosition = "";
        this.regionSpatialBaseUrl = "";
        this.regionSpatialSaving = false;
        this.regionSpatialSyncing = false;
        this.loadSpatialConfig();
        this.loadRegionTreeData();
      } else if (this.modal.type === "recordDownload") {
        this.initRecordDownloadForm();
      } else if (this.modal.type === "quickReplay") {
        this.initQuickReplay();
      } else if (this.modal.type === "reviewTask") {
        this.resetReviewTaskForm();
        if (!this.reviewLlmConfigs.length) {
          api.llmConfigs()
            .then((configs) => { this.reviewLlmConfigs = configs; })
            .catch((error) => this.showToast(`大模型配置加载失败：${error instanceof Error ? error.message : error}`));
        }
        if (!this.reviewTypeOptions.length) {
          api.reviewTypes()
            .then((types) => { this.reviewTypeOptions = types; })
            .catch((error) => this.showToast(`复核类型加载失败：${error instanceof Error ? error.message : error}`));
        }
      }
    }
  },
  methods: {
    statusClass,
    saveVideoConfig() {
      savePlayerSettings(this.videoSettings);
      this.showToast("视频参数配置已保存");
      this.$emit("close");
    },
    resetVideoConfig() {
      this.videoSettings = resetPlayerSettings();
      this.showToast("已恢复默认视频参数");
    },
    // --- 云平台同步设备弹窗 ---
    initCloudSync() {
      this.cloudPlatformId = "";
      this.gb28181EntryId = "";
      this.cloudItems = [];
      this.cloudSummary = null;
      this.cloudBusy = false;
      this.cloudConflictStrategy = "overwrite";
      this.cloudTargetArea = "";
      api.cloudPlatforms()
        .then((rows) => {
          this.cloudPlatforms = [
            ...rows,
            { id: GB28181_OPTION_ID, name: "国标GB28181", type: "gb28181", key: "", secret: "", ip: "-", port: "-", createdAt: "", updatedAt: "" }
          ];
          if (rows.length === 1) this.cloudPlatformId = rows[0].id;
        })
        .catch((error) => this.showToast(`云平台列表加载失败：${error instanceof Error ? error.message : error}`));
      api.gb28181Entries()
        .then((rows) => {
          this.gb28181Entries = rows || [];
        })
        .catch(() => {});
      api.cameras()
        .then((list) => {
          const areas = (list || []).map((camera) => (camera.area || "").trim()).filter(Boolean);
          this.cloudAreaOptions = Array.from(new Set(areas));
        })
        .catch(() => {});
    },
    resetCloudSync() {
      this.gb28181EntryId = "";
      this.cloudItems = [];
      this.cloudSummary = null;
    },
    onGb28181EntryChange() {
      this.cloudItems = [];
      this.cloudSummary = null;
    },
    toggleCloudAll(event: any) {
      const checked = !!(event.target && event.target.checked);
      this.cloudItems.forEach((item) => { item.checked = checked; });
    },
    async runCloudPrecheck() {
      if (!this.cloudPlatformId || this.cloudBusy) return;
      if (this.isGb28181Mode && !this.gb28181EntryId) {
        this.showToast("请先选择级联服务器");
        return;
      }
      this.cloudBusy = true;
      try {
        const result = this.isGb28181Mode
          ? await api.gb28181EntryPrecheck(this.gb28181EntryId)
          : await api.cloudPlatformPrecheck(this.cloudPlatformId);
        this.cloudSummary = result;
        this.cloudItems = result.items.map((item) => ({ ...item, checked: true }));
        if (!result.items.length) this.showToast(this.isGb28181Mode ? "级联服务器暂无可同步设备" : "云平台暂无可同步设备");
      } catch (error) {
        this.onGb28181EntryChange();
        this.showToast(error instanceof Error ? error.message : "云平台预检查失败");
      } finally {
        this.cloudBusy = false;
      }
    },
    async runCloudSync() {
      const items = this.cloudCheckedItems.map((item) => {
        const { checked, ...rest } = item;
        return rest;
      });
      if (!items.length || this.cloudBusy) return;
      if (this.isGb28181Mode && !this.gb28181EntryId) {
        this.showToast("请先选择级联服务器");
        return;
      }
      this.cloudBusy = true;
      try {
        const payload = {
          items,
          targetArea: this.cloudTargetArea,
          overwrite: this.cloudConflictStrategy === "overwrite"
        };
        const result = this.isGb28181Mode
          ? await api.gb28181EntrySync(this.gb28181EntryId, payload)
          : await api.cloudPlatformSync(this.cloudPlatformId, payload);
        this.showToast(`同步完成：新增 ${result.created} 台，更新 ${result.updated} 台，跳过 ${result.skipped} 台`);
        this.$emit("close");
        (this as any).refreshCamerasImpl();
      } catch (error) {
        this.showToast(error instanceof Error ? error.message : "云平台同步失败");
      } finally {
        this.cloudBusy = false;
      }
    },
    showToast(message: string) {
      (this as any).toastImpl(message);
    },
    // --- 从NVR/CVR导入弹窗 ---
    initNvrImport() {
      this.nvrHostRows = [""];
      this.nvrUsername = "";
      this.nvrPassword = "";
      this.nvrItems = [];
      this.nvrSummary = null;
      this.nvrBusy = false;
      this.nvrTargetArea = "";
      api.cameras()
        .then((list) => {
          const areas = (list || []).map((camera) => (camera.area || "").trim()).filter(Boolean);
          this.nvrAreaOptions = Array.from(new Set(areas));
        })
        .catch(() => {});
    },
    addNvrHostRow() {
      this.nvrHostRows.push("");
    },
    removeNvrHostRow(index: number) {
      if (this.nvrHostRows.length <= 1) {
        this.nvrHostRows = [""];
        return;
      }
      this.nvrHostRows.splice(index, 1);
    },
    toggleNvrAll(event: any) {
      const checked = !!(event.target && event.target.checked);
      this.nvrItems.forEach((item) => { item.checked = checked; });
    },
    async runNvrPrecheck() {
      if (this.nvrBusy) return;
      const hosts = this.nvrHostRows.map((row) => row.trim()).filter(Boolean);
      if (!hosts.length) {
        this.showToast("请先添加NVR/CVR地址");
        return;
      }
      if (!this.nvrUsername.trim() || !this.nvrPassword) {
        this.showToast("请输入登录账号和密码");
        return;
      }
      this.nvrBusy = true;
      try {
        const result = await api.nvrImportPrecheck({ hosts, username: this.nvrUsername.trim(), password: this.nvrPassword });
        this.nvrSummary = result;
        this.nvrItems = result.items.map((item) => ({ ...item, checked: true }));
        if (!result.items.length && !result.failures.length) this.showToast("NVR/CVR 上未读取到摄像头通道");
      } catch (error) {
        this.nvrItems = [];
        this.nvrSummary = null;
        this.showToast(error instanceof Error ? error.message : "NVR/CVR 预检查失败");
      } finally {
        this.nvrBusy = false;
      }
    },
    async runNvrSync() {
      const items = this.nvrCheckedItems.map((item) => {
        const { checked, ...rest } = item;
        return rest;
      });
      if (!items.length || this.nvrBusy) return;
      this.nvrBusy = true;
      try {
        const result = await api.nvrImportSync({
          items,
          targetArea: this.nvrTargetArea,
          username: this.nvrUsername.trim(),
          password: this.nvrPassword
        });
        this.showToast(`导入完成：新增 ${result.created} 台，跳过 ${result.skipped} 台（已存在的设备不会更新）`);
        this.$emit("close");
        (this as any).refreshCamerasImpl();
      } catch (error) {
        this.showToast(error instanceof Error ? error.message : "NVR/CVR 导入失败");
      } finally {
        this.nvrBusy = false;
      }
    },
    // 能力配置弹窗：回填勾选设备当前的云台开关（全部勾选设备都开启时才勾上），用户可再编辑
    initCapabilityForm() {
      const rows = ((this.modal.item && this.modal.item.rows) || []).map((row: any) => row.raw || row);
      const every = (key: string, fallback: boolean) =>
        rows.length ? rows.every((raw: any) => raw[key] === true) : fallback;
      this.capabilityPtz = every("ptzEnabled", false);
      this.capabilityStrategy = "overwrite";
      this.capabilitySaving = false;
      this.capabilityProbing = false;
      this.capabilityProgress = { done: 0, total: 0 };
      this.capabilityReport = null;
    },
    // 批量开启云台控制前的能力探测：与设备新增/编辑页同口径（POST /api/cameras/probe-source），
    // 只有探测到明确支持云台的设备才下发；离线/不可达/探测失败的都算「无法确认」，一律跳过。
    async probePtzSupport(targets: any[]) {
      const results: { raw: any; supported: boolean; reason: string }[] = [];
      const queue = [...targets];
      const total = queue.length;
      this.capabilityProgress = { done: 0, total };
      const worker = async () => {
        for (;;) {
          const raw = queue.shift();
          if (!raw) return;
          let supported = false;
          let reason = "未能确认云台能力";
          if (onlineStatusOf(raw) !== "ONLINE") {
            reason = "设备离线，未确认云台能力";
          } else if (!raw.sourceUrl) {
            reason = "缺少拉流地址，无法探测云台能力";
          } else {
            try {
              const probe = await api.probeCameraSource(raw.sourceUrl);
              if (probe.reachable && probe.ptzSupported === true) {
                supported = true;
                reason = "";
              } else if (!probe.reachable) {
                reason = "设备不可达，未确认云台能力";
              } else if (probe.ptzSupported === false) {
                reason = "设备不支持云台控制";
              }
            } catch (error) {
              reason = "云台能力探测失败";
            }
          }
          results.push({ raw, supported, reason });
          this.capabilityProgress = { done: this.capabilityProgress.done + 1, total };
        }
      };
      // 限并发 4：设备视频网探测单次最长 4s，避免大批量时把弹窗卡太久
      await Promise.all(Array.from({ length: Math.min(4, total) }, () => worker()));
      return results;
    },
    async submitCapability() {
      const rows = ((this.modal.item && this.modal.item.rows) || []).map((row: any) => row.raw || row);
      if (!rows.length) {
        this.showToast("请先选择设备");
        return;
      }
      if (this.capabilitySaving) return;
      this.capabilitySaving = true;
      this.capabilityReport = null;
      // 弹窗只保留云台控制一项：只下发 ptzEnabled，设备其余能力配置保持不变
      const desired: Record<string, boolean> = {
        ptzEnabled: this.capabilityPtz
      };
      let targets = rows;
      if (this.capabilityStrategy === "onlineOnly") {
        // "仅应用到在线设备"按设备可达性（onlineStatus）筛选，与页面在线口径一致
        targets = rows.filter((raw: any) => onlineStatusOf(raw) === "ONLINE");
        if (!targets.length) {
          this.capabilitySaving = false;
          this.showToast("所选设备中没有在线设备");
          return;
        }
      }
      // 追加策略下未勾选的项不下发（云台未勾选时等于不改动）
      const payloadKeys = Object.keys(desired).filter(
        (key) => this.capabilityStrategy !== "append" || desired[key]
      );
      if (!payloadKeys.length) {
        this.capabilitySaving = false;
        this.showToast(`无需变更：所选 ${targets.length} 台设备保持原能力配置`);
        return;
      }
      // 开启云台控制前先探测能力：不支持的设备不下发，保存后列出明细
      const skipped: { name: string; reason: string }[] = [];
      let writable = targets;
      if (this.capabilityPtz) {
        this.capabilityProbing = true;
        try {
          const probed = await this.probePtzSupport(targets);
          writable = [];
          probed.forEach((item) => {
            if (item.supported) writable.push(item.raw);
            else skipped.push({ name: item.raw.name || item.raw.id, reason: item.reason });
          });
        } finally {
          this.capabilityProbing = false;
        }
      }
      let succeeded = 0;
      const failures = new Set<string>();
      for (const raw of writable) {
        const payload: Record<string, boolean> = {};
        payloadKeys.forEach((key) => {
          payload[key] = desired[key];
        });
        try {
          await api.updateCamera(raw.id, payload);
          succeeded += 1;
        } catch (error) {
          failures.add(raw.name || raw.id);
        }
      }
      this.capabilitySaving = false;
      if (succeeded > 0) this.refreshCameras();
      const failed = Array.from(failures);
      if (!skipped.length && !failed.length) {
        this.showToast(`能力配置已应用到 ${succeeded} 台设备`);
        this.$emit("close");
        return;
      }
      // 有设备被跳过或保存失败：留在弹窗里给出明细，避免「部分成功」被一条 toast 带过
      failed.forEach((name) => skipped.push({ name, reason: "能力配置保存失败" }));
      this.capabilityReport = {
        applied: succeeded,
        ptzOn: this.capabilityPtz,
        total: targets.length,
        skipped
      };
    },
    toggleDeployArea(name: string) {
      this.deployAreaExpanded[name] = !this.deployAreaExpanded[name];
    },
    // --- 区域管理弹窗（区域树编辑器） ---
    // 区域数据来自后端区域树（/api/regions）；重命名由后端同步更新占用该区域的设备，
    // 每次变更后刷新树并调用 refreshCameras 通知各页面（state.camerasVersion）
    async loadRegionTreeData() {
      try {
        this.regionTree = await loadRegionTree();
        const selected = this.regionSelected;
        if (this.regionSelectedId && !selected) {
          this.regionSelectedId = "";
          this.regionRenameValue = "";
        } else if (selected) {
          this.regionRenameValue = selected.node.name;
        }
      } catch (error) {
        this.showToast(`区域树加载失败：${error instanceof Error ? error.message : error}`);
      }
    },
    async reloadRegions(message?: string) {
      await this.loadRegionTreeData();
      this.refreshCameras();
      if (message) this.showToast(message);
    },
    isRegionExpanded(fullPath: string): boolean {
      return this.regionExpanded[fullPath] !== false;
    },
    toggleRegionExpand(fullPath: string) {
      this.regionExpanded[fullPath] = !this.isRegionExpanded(fullPath);
    },
    selectRegion(row: { node: RegionTreeNode }) {
      this.regionSelectedId = row.node.id;
      this.regionRenameValue = row.node.name;
    },
    validateRegionName(value: string): string {
      const name = (value || "").trim();
      if (!name) {
        this.showToast("请输入区域名称");
        return "";
      }
      if (name.includes("/")) {
        this.showToast("区域名称不能包含 /，请逐层添加");
        return "";
      }
      return name;
    },
    async addRootRegion() {
      const name = this.validateRegionName(this.regionRootNew);
      if (!name) return;
      try {
        await api.createRegion({ name, parentId: null });
      } catch (error) {
        this.showToast(`区域新增失败：${error instanceof Error ? error.message : error}`);
        return;
      }
      this.regionRootNew = "";
      await this.reloadRegions(`区域「${name}」已新增`);
    },
    async saveRegionRename() {
      const selected = this.regionSelected;
      if (!selected) return;
      const name = this.validateRegionName(this.regionRenameValue);
      if (!name) return;
      if (name === selected.node.name) return;
      try {
        await api.renameRegion(selected.node.id, name);
      } catch (error) {
        this.showToast(`区域修改失败：${error instanceof Error ? error.message : error}`);
        return;
      }
      await this.reloadRegions(`区域已修改为「${name}」`);
    },
    async addChildRegion() {
      const selected = this.regionSelected;
      if (!selected) return;
      const name = this.validateRegionName(this.regionChildNew);
      if (!name) return;
      try {
        await api.createRegion({ name, parentId: selected.node.id });
      } catch (error) {
        this.showToast(`区域新增失败：${error instanceof Error ? error.message : error}`);
        return;
      }
      this.regionChildNew = "";
      this.regionExpanded[selected.fullPath] = true;
      await this.reloadRegions(`区域「${name}」已新增`);
    },
    async addSiblingRegion() {
      const selected = this.regionSelected;
      if (!selected) return;
      const name = this.validateRegionName(this.regionSiblingNew);
      if (!name) return;
      try {
        await api.createRegion({ name, parentId: selected.node.parentId });
      } catch (error) {
        this.showToast(`区域新增失败：${error instanceof Error ? error.message : error}`);
        return;
      }
      this.regionSiblingNew = "";
      await this.reloadRegions(`区域「${name}」已新增`);
    },
    async deleteSelectedRegion() {
      const selected = this.regionSelected;
      if (!selected || !this.regionDeletable) return;
      if (!window.confirm("确认删除该区域？")) return;
      try {
        await api.deleteRegion(selected.node.id);
      } catch (error) {
        this.showToast(`区域删除失败：${error instanceof Error ? error.message : error}`);
        return;
      }
      this.regionSelectedId = "";
      this.regionRenameValue = "";
      await this.reloadRegions("区域已删除");
    },
    // 空间服务地址（同步区域树的基址）：读取失败不阻塞区域管理，仅保留空输入框
    async loadSpatialConfig() {
      try {
        const config = await api.spatialConfig();
        this.regionSpatialBaseUrl = config.baseUrl || "";
      } catch {
        this.regionSpatialBaseUrl = "";
      }
    },
    async saveSpatialConfig() {
      if (this.regionSpatialSaving) return;
      const baseUrl = (this.regionSpatialBaseUrl || "").trim();
      if (!baseUrl) {
        this.showToast("请输入空间服务地址");
        return;
      }
      this.regionSpatialSaving = true;
      try {
        const config = await api.saveSpatialConfig(baseUrl);
        this.regionSpatialBaseUrl = config.baseUrl;
        this.showToast("空间服务地址已保存");
      } catch (error) {
        this.showToast(`空间服务地址保存失败：${error instanceof Error ? error.message : error}`);
      } finally {
        this.regionSpatialSaving = false;
      }
    },
    // 从界面配置的空间服务同步区域树：后端只新增缺失的园区/区域/楼栋/楼层，
    // 已有区域结构不动；接口不可访问时后端只记日志、返回 success=false，这里仅提示不当作错误
    async syncSpatialRegions() {
      if (this.regionSpatialSyncing) return;
      this.regionSpatialSyncing = true;
      try {
        const result = await api.syncSpatialRegions();
        await this.loadRegionTreeData();
        this.refreshCameras();
        if (result.success) {
          this.showToast(`空间区域同步完成：新增 ${result.created} 个，已存在跳过 ${result.skipped} 个`);
        } else {
          this.showToast(result.message || "空间区域同步未完成");
        }
      } catch (error) {
        this.showToast(`空间区域同步失败：${error instanceof Error ? error.message : error}`);
      } finally {
        this.regionSpatialSyncing = false;
      }
    },
    // 同级拖拽排序：仅允许同一 parentId 的节点间拖拽，落点上半部分插到目标前、下半部分插到目标后
    onRegionDragStart(event: DragEvent, row: { node: RegionTreeNode }) {
      this.regionDragId = row.node.id;
      if (event.dataTransfer) {
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData("text/plain", row.node.id);
      }
    },
    onRegionDragOver(event: DragEvent, row: { node: RegionTreeNode }) {
      const dragged = this.regionFlatList.find((item) => item.node.id === this.regionDragId);
      if (!dragged || dragged.node.id === row.node.id || dragged.node.parentId !== row.node.parentId) return;
      // 仅同级节点允许放置，此时才阻止默认行为以启用 drop
      event.preventDefault();
      if (event.dataTransfer) event.dataTransfer.dropEffect = "move";
      const rect = (event.currentTarget as HTMLElement).getBoundingClientRect();
      this.regionDropTargetId = row.node.id;
      this.regionDropPosition = event.clientY < rect.top + rect.height / 2 ? "before" : "after";
    },
    onRegionDragLeave(row: { node: RegionTreeNode }) {
      if (this.regionDropTargetId === row.node.id) {
        this.regionDropTargetId = "";
        this.regionDropPosition = "";
      }
    },
    async onRegionDrop(event: DragEvent, row: { node: RegionTreeNode }) {
      event.preventDefault();
      const dragId = this.regionDragId;
      const position = this.regionDropPosition;
      this.onRegionDragEnd();
      const dragged = this.regionFlatList.find((item) => item.node.id === dragId);
      if (!dragged || dragged.node.id === row.node.id || dragged.node.parentId !== row.node.parentId || !position) return;
      const parentId = row.node.parentId;
      const siblings = parentId
        ? (this.regionFlatList.find((item) => item.node.id === parentId)?.node.children || [])
        : this.regionTree;
      const orderedIds = siblings.map((node) => node.id).filter((id) => id !== dragId);
      const targetIndex = orderedIds.indexOf(row.node.id);
      if (targetIndex < 0) return;
      orderedIds.splice(position === "before" ? targetIndex : targetIndex + 1, 0, dragId);
      try {
        await api.reorderRegions(parentId, orderedIds);
      } catch (error) {
        this.showToast(`区域排序失败：${error instanceof Error ? error.message : error}`);
        return;
      }
      await this.reloadRegions();
    },
    onRegionDragEnd() {
      this.regionDragId = "";
      this.regionDropTargetId = "";
      this.regionDropPosition = "";
    },
    // --- 录像下载弹窗 ---
    initRecordDownloadForm() {
      const item = this.modal.item || {};
      this.recordDownloadStart = item.startTime || "";
      this.recordDownloadEnd = item.endTime || "";
      this.recordDownloadBusy = false;
      this.recordDownloadUrl = "";
      this.recordDownloadError = "";
    },
    async submitRecordDownload() {
      const camera = this.recordDownloadCamera;
      if (!camera || this.recordDownloadBusy) return;
      if (!this.recordDownloadStart || !this.recordDownloadEnd) {
        this.showToast("请选择录像的开始与结束时间");
        return;
      }
      if (new Date(this.recordDownloadStart).getTime() >= new Date(this.recordDownloadEnd).getTime()) {
        this.showToast("开始时间必须早于结束时间");
        return;
      }
      // 导出耗时随时段增长（数十秒~数分钟），期间按钮置灰显示「导出中…」
      this.recordDownloadBusy = true;
      this.recordDownloadUrl = "";
      this.recordDownloadError = "";
      try {
        const result = await api.downloadRecording({ cameraId: camera.id, startTime: this.recordDownloadStart, endTime: this.recordDownloadEnd });
        this.recordDownloadUrl = result.url;
        this.showToast("录像导出完成，可点击链接下载 MP4");
      } catch (error) {
        this.recordDownloadError = error instanceof Error ? error.message : String(error);
        this.showToast(`录像导出失败：${this.recordDownloadError}`);
      } finally {
        this.recordDownloadBusy = false;
      }
    },
    toggleDeployCamera(id: string) {
      this.deploySelectedCameras = this.deploySelectedCameras.includes(id)
        ? this.deploySelectedCameras.filter(item => item !== id)
        : this.deploySelectedCameras.concat(id);
    },
    // 部署树里的设备状态：展示设备可达性（在线/离线/未探测）
    cameraStatusText(camera?: Camera) {
      return deviceStatusLabel(camera);
    },
    initAlgorithmForm() {
      const item = this.modal.item;
      const editing = !!(item && item.id);
      this.algorithmName = (item && item.name) || "";
      this.algorithmCode = (item && item.code) || "";
      this.algorithmEngineType = (item && item.engineType) || "";
      // 编辑时这几项是只读的当前版本信息，新增时是初始版本输入
      this.algorithmVersion = editing ? ((item && item.currentVersion) || "") : "v1.0.0";
      this.algorithmVersionName = "";
      this.algorithmNotes = "";
      if (editing) this.loadAlgorithmVersionInfo(item.id);
      this.algorithmDesc = (item && item.description) || "";
      this.algorithmScene = (item && item.scene) || "";
      this.algorithmOwner = (item && item.owner) || "";
      this.algorithmPackageFile = null;
      this.algorithmPackageName = "";
      const input: any = this.$refs.algorithmPackageInput;
      if (input) input.value = "";
      if (!this.algorithmEngines.length) {
        api.algorithmEngines()
          .then((engines) => { this.algorithmEngines = engines; })
          .catch((error) => this.showToast(`算法引擎加载失败：${error instanceof Error ? error.message : error}`));
      }
      // 算法编号下拉：选项来自事件配置页（事件信息）的编码，与原型一致
      if (!this.algorithmEventInfos.length) {
        api.eventInfos()
          .then((rows) => { this.algorithmEventInfos = rows; })
          .catch((error) => this.showToast(`事件编码加载失败：${error instanceof Error ? error.message : error}`));
      }
    },
    initDeployTaskForm() {
      const item = this.modal.item;
      const crop = this.deployTargetCrop;
      const defaultName = this.deployTargetImage ? `快速布防-${(crop && crop.sourceName) || "目标"}` : "";
      this.deployTaskName = (item && item.name) || defaultName;
      this.deployAlgorithmCode = (item && item.algorithmCode) || "";
      this.deploySelectedCameras = item && Array.isArray(item.cameraIds) ? [...item.cameraIds] : [];
      this.deployRecognitionPerMinute = (item && item.recognitionPerMinute) || 10;
      this.deployEffectiveStart = (item && item.effectiveStart) || "";
      this.deployEffectiveEnd = (item && item.effectiveEnd) || "";
      this.deployCycleStart = (item && item.cycleStart) || "00:00";
      this.deployCycleEnd = (item && item.cycleEnd) || "23:59";
      this.deploySimilarity = item && item.similarity != null ? item.similarity : 50;
      this.deployFaceProfileId = (item && item.faceProfileId) || "";
      this.deployDesc = (item && item.desc) || "";
      // 布控目标图：快速布防带入，或编辑回填（仅当目标图不是来自人脸库时）
      this.deployTargetFile = null;
      if (this.deployTargetLocalPreview) URL.revokeObjectURL(this.deployTargetLocalPreview);
      this.deployTargetLocalPreview = "";
      const itemPhotoUrl = item && item.faceProfilePhotoUrl && !item.faceProfileId ? sameOriginAssetUrl(item.faceProfilePhotoUrl) : "";
      this.deployTargetImageUrl = itemPhotoUrl || this.deployTargetImage || "";
      this.deployFaceFilter = "";
      this.deployFaceDropdownOpen = false;
      const targetInput: any = this.$refs.deployTargetFileInput;
      if (targetInput) targetInput.value = "";
      this.deployCameraTreeOpen = false;
      this.deployAreaExpanded = {};
      Promise.all([api.cameras(), api.algorithms(), api.faces(), api.eventInfos()])
        .then(([cameras, algorithms, faces, eventInfos]) => {
          this.deployCameras = cameras;
          this.deployAlgorithms = algorithms;
          this.faceProfiles = faces;
          this.deployEventInfos = eventInfos;
          const areas = this.deployCameraAreas.map((area: any) => area.name);
          if (areas.length) this.deployAreaExpanded = { [areas[0]]: true };
          const selectedFace = this.deploySelectedFaceProfile;
          if (selectedFace) this.deployFaceFilter = selectedFace.name;
        })
        .catch((error) => this.showToast(`布控基础数据加载失败：${error instanceof Error ? error.message : error}`));
    },
    triggerDeployTargetFile() {
      const input: any = this.$refs.deployTargetFileInput;
      if (input) input.click();
    },
    handleDeployTargetFile(event: Event) {
      const input = event.target as HTMLInputElement;
      const file = input.files && input.files[0];
      if (!file) return;
      if (this.deployTargetLocalPreview) URL.revokeObjectURL(this.deployTargetLocalPreview);
      this.deployTargetFile = file;
      this.deployTargetLocalPreview = URL.createObjectURL(file);
      // 本地上传优先于人脸库选取
    },
    clearDeployTargetImage() {
      if (this.deployTargetLocalPreview) URL.revokeObjectURL(this.deployTargetLocalPreview);
      this.deployTargetFile = null;
      this.deployTargetLocalPreview = "";
      this.deployTargetImageUrl = "";
      const input: any = this.$refs.deployTargetFileInput;
      if (input) input.value = "";
    },
    selectDeployFace(face: FaceProfile) {
      this.deployFaceProfileId = face.id;
      this.deployFaceFilter = face.name;
      this.deployFaceDropdownOpen = false;
    },
    clearDeployFace() {
      this.deployFaceProfileId = "";
      this.deployFaceFilter = "";
    },
    closeDeployFaceDropdownSoon() {
      window.setTimeout(() => {
        this.deployFaceDropdownOpen = false;
      }, 150);
    },
    async handleSubmit() {
      if (this.modal.type === "algorithm") {
        this.$emit("submit", "algorithm", {
          id: this.isAlgorithmEdit ? this.modal.item.id : null,
          name: this.algorithmName.trim(),
          code: this.algorithmCode.trim(),
          engineType: this.algorithmEngineType,
          version: this.algorithmVersion.trim(),
          versionName: this.algorithmVersionName.trim(),
          notes: this.algorithmNotes.trim(),
          description: this.algorithmDesc.trim(),
          scene: this.algorithmScene.trim(),
          owner: this.algorithmOwner.trim(),
          file: this.algorithmPackageFile
        });
        return;
      }
      if (this.modal.type === "deployTask") {
        const algorithm = this.deploySelectedAlgorithm;
        // 布控目标：上传的布控图像优先，其次人脸库选取的图片，两者都没值则拦截
        let photoUrl = this.deployTargetImageUrl || "";
        if (this.deployTargetFile) {
          try {
            const uploaded = await api.uploadPersonSearchImage(this.deployTargetFile);
            photoUrl = uploaded.imageUrl;
          } catch (error) {
            this.showToast(`布控图像上传失败：${error instanceof Error ? error.message : error}`);
            return;
          }
        }
        const faceProfile = this.deploySelectedFaceProfile;
        if (!photoUrl && faceProfile) photoUrl = faceProfile.photoUrl || "";
        if (!photoUrl) {
          this.showToast("请上传布控图像或从人脸库选取");
          return;
        }
        if (!this.deployEffectiveStart || !this.deployEffectiveEnd) {
          this.showToast("请选择生效时间");
          return;
        }
        this.$emit("submit", "deployTask", {
          id: this.isDeployTaskEdit ? this.modal.item.id : null,
          name: this.deployTaskName.trim(),
          algorithmId: algorithm ? algorithm.id : null,
          algorithmName: algorithm ? algorithm.name : null,
          algorithmCode: this.deployAlgorithmCode || null,
          engineType: algorithm ? algorithm.engineType : null,
          cameraIds: [...this.deploySelectedCameras],
          faceProfileId: this.deployTargetPreview ? null : faceProfile ? faceProfile.id : null,
          faceProfilePhotoUrl: photoUrl || null,
          recognitionPerMinute: this.deployRecognitionPerMinute,
          similarity: Math.min(100, Math.max(0, Math.floor(Number(this.deploySimilarity) || 0))),
          effectiveStart: this.deployEffectiveStart || null,
          effectiveEnd: this.deployEffectiveEnd || null,
          cycleStart: this.deployCycleStart || null,
          cycleEnd: this.deployCycleEnd || null,
          desc: this.deployDesc.trim(),
          area: this.deploySelectedAreas.join("、"),
          areaCount: this.deploySelectedCameras.length
        });
        return;
      }
      if (this.modal.type === "reviewTask") {
        if (this.reviewTaskSubmitting) return;
        if (!this.reviewTypeId) { this.showToast("请选择事件编码"); return; }
        if (!this.reviewLlmId) { this.showToast("请选择大模型"); return; }
        if (!this.reviewImageFile) { this.showToast("请上传图片"); return; }
        this.$emit("submit", "reviewTask", {
          reviewTypeId: this.reviewTypeId,
          llmConfigId: this.reviewLlmId,
          image: this.reviewImageFile
        });
        return;
      }
      if (this.modal.type === "mediaCapability") {
        await this.submitCapability();
        return;
      }
      this.$emit("submit", this.modal.type);
    },
    resetReviewTaskForm() {
      this.reviewTypeId = "";
      this.reviewLlmId = "";
      this.reviewImageFile = null;
      this.reviewImageName = "";
      if (this.reviewImageUrl) {
        URL.revokeObjectURL(this.reviewImageUrl);
        this.reviewImageUrl = "";
      }
      const input: any = this.$refs.reviewImageInput;
      if (input) input.value = "";
    },
    triggerReviewImage() {
      const input: any = this.$refs.reviewImageInput;
      if (input) input.click();
    },
    handleReviewImage(event: any) {
      const file = event.target.files && event.target.files[0];
      if (!file) return;
      // 与后端 save_review_image 校验一致：仅图片、不超过 20MB；前置拦截避免超大请求被 nginx 413 直接拒绝
      if (!file.type || !file.type.startsWith("image/")) {
        this.showToast("仅支持图片文件");
        event.target.value = "";
        return;
      }
      if (file.size > 20 * 1024 * 1024) {
        this.showToast("图片大小不能超过 20MB");
        event.target.value = "";
        return;
      }
      if (this.reviewImageUrl) URL.revokeObjectURL(this.reviewImageUrl);
      this.reviewImageFile = file;
      this.reviewImageName = file.name;
      this.reviewImageUrl = URL.createObjectURL(file);
    },
    triggerVersionFile() {
      const input: any = this.$refs.versionFileInput;
      if (input) input.click();
    },
    handleVersionFile(event: any) {
      const file = event.target.files && event.target.files[0];
      this.versionFileName = file ? file.name : "";
    },
    // 编辑算法时展示当前版本的只读信息（版本名称、说明、算法包文件清单）
    async loadAlgorithmVersionInfo(algorithmId: string) {
      try {
        const versions = await api.algorithmVersions(algorithmId);
        const active = (versions || []).find(version => version.active) || (versions || [])[0];
        if (!active) return;
        if (!this.algorithmVersion) this.algorithmVersion = active.version || "";
        this.algorithmVersionName = active.versionName || "";
        this.algorithmNotes = active.notes || "";
        const files = Object.keys(active.fileManifest || {});
        this.algorithmPackageName = files.length
          ? `${files.length} 个文件：${files.slice(0, 3).join("、")}${files.length > 3 ? " 等" : ""}`
          : (active.status === "MISSING_FILES" ? "算法包文件缺失" : "");
      } catch {
        // 版本信息拉取失败时保持空值，不影响其它字段编辑
      }
    },
    triggerAlgorithmPackage() {
      const input: any = this.$refs.algorithmPackageInput;
      if (input) input.click();
    },
    handleAlgorithmPackage(event: any) {
      const file = event.target.files && event.target.files[0];
      if (file && !/\.zip$/i.test(file.name)) {
        this.showToast("算法包仅支持 zip 文件");
        event.target.value = "";
        return;
      }
      this.algorithmPackageFile = file || null;
      this.algorithmPackageName = file ? file.name : "";
    },
    refreshCameras() {
      (this as any).refreshCamerasImpl();
    },
    triggerImportFile() {
      const input: any = this.$refs.importFileInput;
      if (input) input.click();
    },
    handleImportFile(event: any) {
      const file = event.target.files && event.target.files[0];
      if (!file) return;
      this.importFile = file;
      this.importFileName = file.name;
      this.importResult = null;
    },
    handleImportDrop(event: any) {
      const file = event.dataTransfer && event.dataTransfer.files && event.dataTransfer.files[0];
      if (!file) return;
      this.importFile = file;
      this.importFileName = file.name;
      this.importResult = null;
    },
    downloadImportTemplate() {
      const rows = [
        {
          设备名称: "示例摄像机",
          接入协议: "RTSP 拉流",
          IP: "192.168.1.64",
          端口: "554",
          所在区域: "园区总部 / A区",
          账号: "admin",
          密码: "12345678",
          设备编号: "100000000000000001",
          设备序列号: "SN-0001",
          拉流地址: ""
        }
      ];
      const sheet = XLSX.utils.json_to_sheet(rows);
      const book = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(book, sheet, "设备导入模板");
      XLSX.writeFile(book, "设备导入模板.xlsx");
      this.showToast("导入模板已开始下载");
    },
    async runImport() {
      if (this.importBusy) return;
      if (!this.importFile) {
        this.showToast("请先选择导入文件");
        return;
      }
      this.importBusy = true;
      try {
        const buffer = await this.importFile.arrayBuffer();
        const workbook = XLSX.read(buffer, { type: "array" });
        const sheet = workbook.Sheets[workbook.SheetNames[0]];
        const rows = XLSX.utils.sheet_to_json(sheet, { defval: "" }) as any[];
        const failures: any[] = [];
        let succeeded = 0;
        for (let index = 0; index < rows.length; index += 1) {
          const raw = rows[index];
          const rowNo = index + 2;
          const cell = (key: string) => String(raw[key] ?? "").trim();
          const name = cell("设备名称");
          if (!name) {
            failures.push({ row: rowNo, reason: "设备名称必填" });
            continue;
          }
          // 列名兼容：导入模板用「协议/区域/序列号」，导出文件与界面列名用「接入协议/所在区域/设备序列号」
          const protocol = cell("协议") || cell("接入协议");
          const ip = cell("IP");
          let sourceUrl = cell("拉流地址");
          if (!sourceUrl) {
            const built = computeSourceUrl(protocol || "RTSP 拉流", ip, cell("端口"), cell("账号"), cell("密码"));
            if ((protocol === "" || protocol === "RTSP 拉流") && ip && built) {
              sourceUrl = built;
            } else {
              failures.push({ row: rowNo, reason: "缺少拉流地址且无法按协议拼装" });
              continue;
            }
          }
          try {
            await api.createCamera({
              name,
              sourceUrl,
              protocol: protocol || undefined,
              ip: ip || undefined,
              port: cell("端口") || undefined,
              username: cell("账号") || undefined,
              password: cell("密码") || undefined,
              area: cell("区域") || cell("所在区域") || undefined,
              deviceCode: cell("设备编号") || undefined,
              serialNumber: cell("序列号") || cell("设备序列号") || undefined
            });
            succeeded += 1;
          } catch (error: any) {
            failures.push({ row: rowNo, reason: `创建失败：${error?.message || error}` });
          }
        }
        this.importResult = { ok: succeeded, fail: failures };
        if (succeeded > 0) this.refreshCameras();
        if (!rows.length) this.showToast("文件中没有可导入的数据行");
      } catch (error: any) {
        this.showToast(`文件解析失败：${error?.message || error}`);
      } finally {
        this.importBusy = false;
      }
    },
    runExport() {
      const item = this.modal.item || {};
      const datasets: any = {
        filtered: item.filtered || [],
        selected: item.selected || [],
        all: item.all || []
      };
      const cameras = (datasets[this.exportRange] || []) as Camera[];
      if (!cameras.length) {
        this.showToast("没有可导出的设备");
        return;
      }
      // 导出列：设备状态按"设备可达性"，拉流状态单独一列（与设备管理页口径一致）
      const statusText = (camera?: Camera) => deviceStatusLabel(camera);
      const streamText = (status?: string) => streamStatusLabel({ status });
      const columnSets: any = {
        all: [
          ["设备名称", (c: Camera) => c.name],
          ["所在区域", (c: Camera) => c.area || "未分配"],
          ["接入协议", (c: Camera) => c.protocol || ""],
          ["IP", (c: Camera) => c.ip || ""],
          ["端口", (c: Camera) => c.port || ""],
          ["设备编号", (c: Camera) => c.deviceCode || ""],
          ["设备序列号", (c: Camera) => c.serialNumber || ""],
          ["厂商", (c: Camera) => c.vendor || ""],
          ["设备状态", (c: Camera) => statusText(c)],
          ["拉流状态", (c: Camera) => streamText(c.status)],
          ["描述", (c: Camera) => c.description || ""],
          ["拉流地址", (c: Camera) => c.sourceUrl || ""]
        ],
        base: [
          ["设备名称", (c: Camera) => c.name],
          ["所在区域", (c: Camera) => c.area || "未分配"],
          ["设备编号", (c: Camera) => c.deviceCode || ""],
          ["设备序列号", (c: Camera) => c.serialNumber || ""],
          ["厂商", (c: Camera) => c.vendor || ""],
          ["设备状态", (c: Camera) => statusText(c)]
        ],
        connect: [
          ["设备名称", (c: Camera) => c.name],
          ["接入协议", (c: Camera) => c.protocol || ""],
          ["IP", (c: Camera) => c.ip || ""],
          ["端口", (c: Camera) => c.port || ""],
          ["拉流地址", (c: Camera) => c.sourceUrl || ""]
        ]
      };
      const columns = columnSets[this.exportFields] || columnSets.all;
      const rows = cameras.map((camera: Camera) => {
        const row: any = {};
        columns.forEach(([label, getter]: any) => {
          row[label] = getter(camera);
        });
        return row;
      });
      const sheet = XLSX.utils.json_to_sheet(rows);
      const book = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(book, sheet, "设备列表");
      const date = new Date().toISOString().slice(0, 10).replace(/-/g, "");
      XLSX.writeFile(book, `设备导出_${date}.xlsx`);
      this.showToast("设备列表已按当前范围导出");
      this.$emit("close");
    },
    goPlayback() {
      // 带上即时回放的查询参数：录像回放页按设备 + 时间段直接检索并播放同一录像片段
      const camera = this.quickReplayCamera;
      const playbackQuery = camera && this.quickReplayStartMs && this.quickReplayEndMs
        ? { cameraId: camera.id, startMs: this.quickReplayStartMs, endMs: this.quickReplayEndMs }
        : null;
      this.$emit("close");
      this.setRoute("mediaPlayback", { playbackQuery });
    },
    // --- 即时回放：复用录像检索/回放流链路，回看当前窗口设备最近 N 秒 ---
    stopQuickReplayTimer() {
      if (this.quickReplayTimer) window.clearInterval(this.quickReplayTimer);
      this.quickReplayTimer = null;
    },
    startQuickReplayTimer() {
      this.stopQuickReplayTimer();
      // 墙钟计时：进度 ≈ 起流时刻 + 已播放秒数（1 倍速），仅展示不可拖拽
      this.quickReplayTimer = window.setInterval(() => {
        const elapsed = Math.floor((Date.now() - this.quickReplayStartedAt) / 1000);
        this.quickReplayCurrent = Math.max(0, Math.min(this.quickReplayDuration, elapsed));
        if (this.quickReplayCurrent >= this.quickReplayDuration) this.stopQuickReplayTimer();
      }, 1000);
    },
    teardownQuickReplay() {
      // 递增序号：作废旧请求的迟到响应（含关闭弹窗后的在途 initQuickReplay）
      this.quickReplaySeq += 1;
      this.stopQuickReplayTimer();
      this.quickReplayUrl = undefined;
      this.quickReplayError = "";
      this.quickReplayLoading = false;
      this.quickReplayStartMs = 0;
      this.quickReplayEndMs = 0;
    },
    async initQuickReplay() {
      // 序号守卫：切换回放时长/重复打开时，旧请求的迟到响应不得覆盖新状态
      this.teardownQuickReplay();
      const seq = this.quickReplaySeq;
      this.quickReplayCurrent = 0;
      this.quickReplayDuration = 0;
      const camera = this.quickReplayCamera;
      if (!camera || !camera.id) {
        this.quickReplayError = "未传入设备，请从实时预览页选择一路视频后打开即时回放";
        return;
      }
      const now = Date.now();
      const startMs = now - Number(this.quickReplaySeconds) * 1000;
      // 检索窗口与回放窗口解耦：NVR 最新录像段存在落盘/索引延迟，进行中或刚结束的段
      // 用 15/30/60 秒窄窗口检索不到（现场实测 60s 内 0 段），故固定用最近 30 分钟宽窗口检索
      const searchStartMs = now - QUICK_REPLAY_SEARCH_WINDOW_MS;
      this.quickReplayLoading = true;
      try {
        const result = await api.searchRecordings({ cameraId: camera.id, startTime: toLocalIsoSeconds(searchStartMs), endTime: toLocalIsoSeconds(now) });
        if (seq !== this.quickReplaySeq) return;
        const segments: RecordingSegment[] = (result && result.data) || [];
        // 优先取覆盖回放窗口起点（now - N秒）的段；NVR 索引延迟导致覆盖段检索不到时，
        // 回退取最晚一段（其 endTime 一定早于 startMs，起流时从段起点 clamp）
        const segment = segments.find((item) => parseLocalMs(item.endTime) >= startMs) || segments[segments.length - 1] || null;
        if (!segment) return; // 宽窗口也无段：模板显示「该设备近期无录像」
        const segStartMs = parseLocalMs(segment.startTime);
        const segEndMs = parseLocalMs(segment.endTime) || now;
        // 起流范围 clamp 进该段实际覆盖区间，进度总长也按实际可播内容计算
        const streamEndMs = Math.min(now, segEndMs);
        let baseStartMs = Math.max(segStartMs, startMs);
        if (baseStartMs >= streamEndMs) {
          // 段整体早于回放窗口（索引延迟场景）：回放该段最后 N 秒
          baseStartMs = Math.max(segStartMs, streamEndMs - Number(this.quickReplaySeconds) * 1000);
        }
        // 现场海康 NVR 对「最近约 60 秒内」的回放起点返回 404 该时段无录像（分片未落盘），
        // 实测 now-75s/now-60s 起流正常；因此 404 时按 30 秒步长逐步回退起点重试
        let stream = null as any;
        let usedStartMs = baseStartMs;
        let lastError: any = null;
        for (const backoffMs of [0, 30000, 60000, 90000]) {
          const tryStartMs = Math.max(segStartMs, baseStartMs - backoffMs);
          if (tryStartMs >= streamEndMs) break;
          try {
            stream = await api.startRecordingStream({
              cameraId: camera.id,
              startTime: toLocalIsoSeconds(tryStartMs),
              endTime: toLocalIsoSeconds(streamEndMs),
              speed: 1
            });
            usedStartMs = tryStartMs;
            break;
          } catch (error) {
            if (seq !== this.quickReplaySeq) return;
            lastError = error;
            const message = error instanceof Error ? error.message : String(error);
            if (!/无录像|404/.test(message)) throw error; // 非「无录像」错误（如 400 反查失败）不重试
          }
        }
        if (seq !== this.quickReplaySeq) return;
        if (!stream) throw lastError || new Error("回放流启动失败");
        this.quickReplayDuration = Math.max(1, Math.round((streamEndMs - usedStartMs) / 1000));
        this.quickReplayStartedAt = Date.now();
        this.quickReplayStartMs = usedStartMs;
        this.quickReplayEndMs = streamEndMs;
        this.quickReplayUrl = stream.url;
        this.startQuickReplayTimer();
      } catch (error) {
        if (seq !== this.quickReplaySeq) return;
        // 404 无录像 / 400 反查失败等：错误消息直接展示在弹窗内
        this.quickReplayError = error instanceof Error ? error.message : String(error);
      } finally {
        if (seq === this.quickReplaySeq) this.quickReplayLoading = false;
      }
    }
  },
  beforeUnmount() {
    this.stopQuickReplayTimer();
  }
};
</script>

<template>
  <div class="modal-mask" :class="{ open: modal.open }" :inert="!modal.open" @click.self="$emit('close')">
    <section class="modal-dialog" :class="[{ narrow: modal.narrow }, { wide: modal.wide }, { 'event-detail-dialog': modal.type === 'eventDetail' || modal.type === 'reviewTaskDetail' }]" aria-label="弹窗表单">
      <div class="modal-head">
        <h3>{{ modal.title }}</h3>
        <button class="modal-close" aria-label="关闭" @click="$emit('close')">×</button>
      </div>
      <div class="modal-body">
        <template v-if="modal.type === 'reviewTask'">
          <div class="modal-form-row">
            <label><span class="required">*</span>事件编码：</label>
            <select class="select" v-model="reviewTypeId">
              <option value="">请选择事件编码</option>
              <option v-for="item in reviewTypeOptions" :key="item.id" :value="item.id">{{ item.name }}（{{ item.code }}）</option>
            </select>
          </div>
          <div class="modal-form-row">
            <label><span class="required">*</span>大模型：</label>
            <select class="select" v-model="reviewLlmId">
              <option value="">请选择大模型</option>
              <option v-for="item in reviewLlmConfigs" :key="item.id" :value="item.id">{{ item.name }}（{{ item.deployType === 'local' ? '本地' : '云端' }}）</option>
            </select>
          </div>
          <div class="modal-form-row">
            <label><span class="required">*</span>图片：</label>
            <div>
              <input ref="reviewImageInput" type="file" accept="image/*" style="display:none" @change="handleReviewImage" />
              <button class="modal-upload" @click="triggerReviewImage"><span><span class="plus">＋</span>上传</span></button>
              <div v-if="reviewImageUrl" style="margin-top:8px;">
                <img :src="reviewImageUrl" :alt="reviewImageName" style="max-width:180px;max-height:120px;border-radius:6px;display:block;margin-bottom:4px;" />
                <span style="font-size:12px;color:#888;">{{ reviewImageName }}</span>
              </div>
            </div>
          </div>
          <div class="modal-form-row">
            <label>视频：</label>
            <div>
              <button class="modal-upload" disabled style="opacity:.5;cursor:not-allowed;"><span><span class="plus">＋</span>上传</span></button>
              <span style="font-size:12px;color:#999;margin-left:8px;">暂不支持</span>
            </div>
          </div>
        </template>
        <template v-if="modal.type === 'eventDetail' && modal.item">
          <div class="event-detail-grid">
            <dl class="event-detail-field"><dt>事件有效</dt><dd :class="modal.item.timeValid === '有效' ? 'text-success' : 'text-danger'">{{ modal.item.timeValid === '有效' ? '是' : '否' }}</dd></dl>
            <dl class="event-detail-field"><dt>事件地点</dt><dd>{{ modal.item.location }}</dd></dl>
            <dl class="event-detail-field"><dt>事件时间</dt><dd>{{ modal.item.created }}</dd></dl>
            <dl class="event-detail-field"><dt>任务状态</dt><dd><span class="status-pill" :class="statusClass(modal.item.executionStatus)">{{ modal.item.executionStatus }}</span></dd></dl>
            <dl class="event-detail-field"><dt>任务执行时长</dt><dd>{{ modal.item.duration }}</dd></dl>
          </div>
          <div class="event-detail-section">
            <h4>研判原因</h4>
            <p>{{ modal.item.reason }}</p>
          </div>
          <div class="event-detail-section">
            <h4>证据信息</h4>
            <pre class="event-detail-evidence">{{ modal.item.evidence }}</pre>
          </div>
          <div class="event-detail-section">
            <h4>事件图片</h4>
            <div class="event-detail-image"><img :src="modal.item.image" :alt="modal.item.type + '事件图片'" /><span class="event-detail-image-time">{{ modal.item.created }}</span></div>
          </div>
        </template>
        <template v-if="modal.type === 'reviewTaskDetail' && modal.item">
          <div class="event-detail-grid">
            <dl class="event-detail-field"><dt>事件类型</dt><dd>{{ modal.item.reviewTypeName }}（{{ modal.item.reviewTypeCode }}）</dd></dl>
            <dl class="event-detail-field"><dt>大模型</dt><dd>{{ modal.item.llmConfigName }}</dd></dl>
            <dl class="event-detail-field"><dt>任务状态</dt><dd><span class="status-pill" :class="statusClass(modal.item.status)">{{ modal.item.status }}</span></dd></dl>
            <dl class="event-detail-field"><dt>判定结果</dt><dd :class="modal.item.verdict === '有效' ? 'text-success' : (modal.item.verdict === '无效' ? 'text-danger' : '')">{{ modal.item.verdict || '-' }}</dd></dl>
          </div>
          <div class="event-detail-section">
            <h4>研判原因</h4>
            <p>{{ modal.item.reason || '-' }}</p>
          </div>
          <div class="event-detail-section">
            <h4>事件图片</h4>
            <div class="event-detail-image"><img :src="modal.item.imageUrl" alt="复核任务图片" /></div>
          </div>
        </template>
        <template v-if="modal.type === 'algorithm'">
          <p v-if="isAlgorithmEdit" class="modal-hint">算法编号、算法引擎与版本信息创建后不可修改；新版本请在列表的「版本号」中上传。</p>
          <div class="modal-form-row">
            <label><span class="required">*</span>算法名称：</label>
            <input class="input" v-model="algorithmName" placeholder="请输入算法名称" />
          </div>
          <div class="modal-form-row">
            <label><span class="required">*</span>算法编号：</label>
            <select class="select" v-model="algorithmCode" :disabled="isAlgorithmEdit">
              <option value="" disabled>请选择算法编号</option>
              <option v-for="row in algorithmEventInfos" :key="row.code" :value="row.code">{{ row.code }}（{{ row.name }}）</option>
            </select>
          </div>
          <div class="modal-form-row">
            <label><span class="required">*</span>算法引擎：</label>
            <select class="select" v-model="algorithmEngineType" :disabled="isAlgorithmEdit">
              <option value="">请选择算法引擎</option>
              <option v-for="engine in algorithmEngines" :key="engine.engineType" :value="engine.engineType">{{ engine.label }}（{{ engine.engineType }}）</option>
            </select>
          </div>
          <div class="modal-form-row">
            <label>应用场景：</label>
            <input class="input" v-model="algorithmScene" placeholder="请输入应用场景，如 园区周界" />
          </div>
          <div class="modal-form-row">
            <label>负责人：</label>
            <input class="input" v-model="algorithmOwner" placeholder="请输入负责人" />
          </div>
          <div class="modal-form-row">
            <label><span class="required">*</span>{{ isAlgorithmEdit ? '当前版本：' : '初始版本：' }}</label>
            <input class="input" v-model="algorithmVersion" :disabled="isAlgorithmEdit" :placeholder="isAlgorithmEdit ? '' : '请输入初始版本，如 v1.0.0'" />
          </div>
          <div class="modal-form-row">
            <label>版本名称：</label>
            <input class="input" v-model="algorithmVersionName" :disabled="isAlgorithmEdit" placeholder="请输入版本名称" />
          </div>
          <div class="modal-form-row">
            <label><span class="required">*</span>算法包文件：</label>
            <div class="deploy-target-field">
              <input v-if="!isAlgorithmEdit" ref="algorithmPackageInput" class="hidden-file-input" type="file" accept=".zip" @change="handleAlgorithmPackage" />
              <button v-if="!isAlgorithmEdit" class="file-upload-tile version-upload-single" type="button" @click="triggerAlgorithmPackage"><span><b>{{ algorithmPackageName || '＋ 上传算法包文件' }}</b><br />仅支持 zip</span></button>
              <div v-else class="file-upload-tile version-upload-single is-readonly"><span><b>{{ algorithmPackageName || '暂无算法包信息' }}</b><br />算法包按版本上传，请在「版本号」中管理</span></div>
            </div>
          </div>
          <div class="modal-form-row">
            <label>版本说明：</label>
            <textarea class="textarea" style="height:82px;" v-model="algorithmNotes" :disabled="isAlgorithmEdit" placeholder="请输入版本说明"></textarea>
          </div>
          <div class="modal-form-row">
            <label>算法描述：</label>
            <textarea class="textarea" style="height:96px;" v-model="algorithmDesc" placeholder="请输入算法描述"></textarea>
          </div>
        </template>
        <template v-if="modal.type === 'deployTask'">
          <div class="modal-form-row">
            <label><span class="required">*</span>布控目标：</label>
            <div class="deploy-target-field">
              <input ref="deployTargetFileInput" class="hidden-file-input" type="file" accept="image/*" @change="handleDeployTargetFile" />
              <div v-if="deployTargetPreview" class="deploy-target-preview">
                <img :src="deployTargetPreview" alt="布控目标" />
                <span v-if="deployTargetCrop && !deployTargetFile" class="deploy-target-crop" :style="deployTargetCropStyle"></span>
              </div>
              <button v-if="deployTargetPreview" class="deploy-target-clear" type="button" @click="clearDeployTargetImage">清除</button>
              <button v-else class="file-upload-tile version-upload-single" type="button" @click="triggerDeployTargetFile"><span><b>＋ 点击上传布控图像</b><br />jpg / png 等图片</span></button>
            </div>
          </div>
          <div class="modal-form-row">
            <label>从人脸库选取：</label>
            <div class="face-combo">
              <input class="input" v-model="deployFaceFilter" placeholder="输入姓名筛选人脸库" @focus="deployFaceDropdownOpen = true" @input="deployFaceDropdownOpen = true" @blur="closeDeployFaceDropdownSoon" />
              <button v-if="deployFaceProfileId" class="face-combo-clear" type="button" aria-label="清除人脸库选择" @mousedown.prevent="clearDeployFace">×</button>
              <div v-if="deployFaceDropdownOpen" class="face-combo-list">
                <button v-for="face in filteredFaceProfiles" :key="face.id" class="face-combo-item" :class="{ active: face.id === deployFaceProfileId }" type="button" @mousedown.prevent="selectDeployFace(face)">
                  <img v-if="face.photoUrl" :src="face.photoUrl" :alt="face.name" />
                  <span>{{ face.name }}</span>
                </button>
                <div v-if="!filteredFaceProfiles.length" class="face-combo-empty">无匹配人脸</div>
              </div>
            </div>
          </div>
          <div class="modal-form-row">
            <label><span class="required">*</span>任务名称：</label>
            <input class="input" v-model="deployTaskName" placeholder="请输入任务名称" />
          </div>
          <div class="modal-form-row">
            <label><span class="required">*</span>算法编号：</label>
            <div class="deploy-algorithm-field">
              <select class="select" v-model="deployAlgorithmCode">
                <option value="">请选择算法编号</option>
                <option v-for="item in deployEventInfos" :key="item.id" :value="item.code">{{ item.code }}（{{ item.name }}）</option>
              </select>
              <span v-if="deployAlgorithmHint" class="hint-text" :class="{ 'hint-warn': !deploySelectedAlgorithm }">{{ deployAlgorithmHint }}</span>
            </div>
          </div>
          <div class="modal-form-row">
            <label><span class="required">*</span>布控区域：</label>
            <div class="exact-tree-select deploy-camera-tree">
              <button class="exact-tree-trigger" :class="{ open: deployCameraTreeOpen }" type="button" @click="deployCameraTreeOpen = !deployCameraTreeOpen"><span>{{ deployCameraSummary }}</span><span>{{ deployCameraTreeOpen ? '收起' : '展开' }}⌄</span></button>
              <div v-if="deployCameraTreeOpen" class="exact-tree-dropdown">
                <div v-for="area in deployCameraAreas" :key="area.name">
                  <button class="exact-tree-area-row" type="button" @click="toggleDeployArea(area.name)"><span>{{ deployAreaExpanded[area.name] ? '⌄' : '›' }} {{ area.name }}</span><span>{{ area.cameras.length }} 台设备</span></button>
                  <div v-if="deployAreaExpanded[area.name]" class="exact-tree-children">
                    <label v-for="camera in area.cameras" :key="camera.id" class="exact-tree-device deploy-tree-camera"><input type="checkbox" :checked="deploySelectedCameras.includes(camera.id)" :aria-label="'选择' + camera.name" @change="toggleDeployCamera(camera.id)" /><span class="camera-name">{{ camera.name }}</span><span>{{ cameraStatusText(camera) }}</span></label>
                  </div>
                </div>
                <div v-if="!deployCameraAreas.length" class="exact-tree-children"><span style="padding:8px 12px;display:block;">暂无摄像机，请先在设备管理中接入</span></div>
              </div>
            </div>
          </div>
          <div class="modal-form-row">
            <label><span class="required">*</span>生效时间：</label>
            <div class="effective-range"><input class="input" type="date" v-model="deployEffectiveStart" aria-label="生效开始日期" /><span class="range-arrow">→</span><input class="input" type="date" v-model="deployEffectiveEnd" aria-label="生效结束日期" /></div>
          </div>
          <div class="modal-form-row">
            <label><span class="required">*</span>循环周期：</label>
            <div class="effective-range"><input class="input" type="time" v-model="deployCycleStart" aria-label="循环开始时间" /><span class="range-arrow">→</span><input class="input" type="time" v-model="deployCycleEnd" aria-label="循环结束时间" /></div>
          </div>
          <div class="modal-form-row">
            <label><span class="required">*</span>相似度：</label>
            <div class="deploy-similarity-field"><input type="range" min="0" max="100" step="1" v-model.number="deploySimilarity" aria-label="相似度" /><output>{{ deploySimilarity }}%</output></div>
          </div>
          <div class="modal-form-row">
            <label>识别频次：</label>
            <input class="input" type="number" min="1" v-model.number="deployRecognitionPerMinute" placeholder="每分钟识别次数" />
          </div>
          <div class="modal-form-row">
            <label>任务描述：</label>
            <textarea class="textarea" style="height:96px;" v-model="deployDesc" placeholder="请输入任务描述"></textarea>
          </div>
        </template>
        <template v-if="modal.type === 'version'">
          <div class="modal-form-row">
            <label><span class="required">*</span>所属算法：</label>
            <select class="select">
              <option v-for="row in store.algorithmManageRows" :key="row.id">{{ row.name }}</option>
            </select>
          </div>
          <div class="modal-form-row">
            <label><span class="required">*</span>版本号：</label>
            <input class="input" value="v3.1.0" />
          </div>
          <div class="modal-form-row">
            <label><span class="required">*</span>版本名称：</label>
            <input class="input" placeholder="请输入版本名称" />
          </div>
          <div class="modal-form-row">
            <label>版本说明：</label>
            <textarea class="textarea" style="height:72px;" placeholder="请输入本次版本优化内容"></textarea>
          </div>
          <div class="modal-form-row">
            <label><span class="required">*</span>版本文件：</label>
            <div class="deploy-target-field">
              <input ref="versionFileInput" class="hidden-file-input" type="file" accept=".onnx,.pt,.zip,.json,.yaml,.yml,.md,.pdf,.doc,.docx" @change="handleVersionFile" />
              <button class="file-upload-tile version-upload-single" type="button" @click="triggerVersionFile"><span><b>{{ versionFileName || '＋ 上传版本文件' }}</b><br />onnx / pt / zip / json / yaml / md / pdf / doc</span></button>
            </div>
          </div>
        </template>
        <template v-if="modal.type === 'eventSource'">
          <div class="modal-form-row">
            <label><span class="required">*</span>数据源名称：</label>
            <input class="input" value="视频事件平台" placeholder="请输入数据源名称" />
          </div>
          <div class="modal-form-row">
            <label><span class="required">*</span>接口地址：</label>
            <input class="input" value="video-event.platform.cn/api" placeholder="请输入接口地址" />
          </div>
          <div class="modal-form-row">
            <label><span class="required">*</span>接入方式：</label>
            <select class="select"><option>主动拉取</option><option>被动接收</option><option>Webhook推送</option></select>
          </div>
          <div class="modal-form-row">
            <label><span class="required">*</span>事件类型：</label>
            <input class="input" value="跌倒检测、聚集检测" placeholder="请输入事件类型，多个用顿号分隔" />
          </div>
          <div class="modal-form-row">
            <label>拉取频率：</label>
            <select class="select"><option>实时推送</option><option>每5分钟</option><option>每10分钟</option><option>每30分钟</option></select>
          </div>
          <div class="modal-form-row">
            <label>状态：</label>
            <select class="select"><option>运行中</option><option>停止</option><option>停止</option></select>
          </div>
          <div class="modal-form-row">
            <label>说明：</label>
            <textarea class="textarea" style="height:82px;" placeholder="请输入接入说明">聚合后的事件将作为原始事件，为后续去重、复核提供支撑。</textarea>
          </div>
        </template>
        <template v-if="modal.type === 'permissionRole'">
          <div class="modal-form-row">
            <label><span class="required">*</span>角色名称：</label>
            <input class="input" value="安防运营" placeholder="请输入角色名称" />
          </div>
          <div class="modal-form-row">
            <label><span class="required">*</span>角色编码：</label>
            <input class="input" value="SECURITY_OPERATOR" placeholder="请输入角色编码" />
          </div>
          <div class="modal-form-row">
            <label><span class="required">*</span>数据范围：</label>
            <select class="select"><option>全部数据</option><option>安防中心</option><option>算法组</option><option>万物核</option><option>只读演示</option></select>
          </div>
          <div class="modal-form-row">
            <label><span class="required">*</span>启用状态：</label>
            <select class="select"><option>启用</option><option>停用</option></select>
          </div>
          <div class="modal-form-row">
            <label>角色描述：</label>
            <textarea class="textarea" style="height:90px;" placeholder="请输入角色描述">负责万物搜、布控任务、事件处置和日志查看。</textarea>
          </div>
        </template>
        <template v-if="modal.type === 'mediaImport'">
          <input ref="importFileInput" type="file" accept=".xlsx,.csv" style="display:none" aria-label="选择导入文件" @change="handleImportFile" />
          <div class="modal-drop-zone" style="cursor:pointer;" @click="triggerImportFile" @dragover.prevent @drop.prevent="handleImportDrop">
            <strong><span class="required">*</span>{{ importFileName || '拖拽或点击选择文件上传' }}</strong>
            <span>支持 .xlsx / .csv，字段包含设备名称、接入协议、IP、端口、所在区域、账号、密码、设备编号。</span>
          </div>
          <div v-if="importResult" class="modal-summary-strip" style="margin-top:10px;"><strong>导入结果</strong><span>成功 {{ importResult.ok }} 条，失败 {{ importResult.fail.length }} 条</span></div>
          <ul v-if="importResult && importResult.fail.length" style="max-height:140px;overflow:auto;margin:8px 0 0;padding-left:18px;">
            <li v-for="(failure, index) in importResult.fail" :key="index">第 {{ failure.row }} 行：{{ failure.reason }}</li>
          </ul>
        </template>
        <template v-if="modal.type === 'mediaExport'">
          <div class="modal-form-row"><label>导出范围：</label><select class="select" v-model="exportRange"><option value="filtered">当前筛选结果</option><option value="selected">选中设备</option><option value="all">全部设备</option></select></div>
          <div class="modal-form-row"><label>导出字段：</label><select class="select" v-model="exportFields"><option value="all">全部展示字段</option><option value="base">基础信息</option><option value="connect">连接信息</option></select></div>
        </template>
        <template v-if="modal.type === 'mediaMove'">
          <p class="modal-hint">将已选择 {{ (modal.item && modal.item.rows ? modal.item.rows.length : 0) }} 台设备移动到其他区域，通道与告警联动关系保持不变。</p>
          <div class="modal-form-row"><label><span class="required">*</span>目标区域：</label><select class="select" v-model="moveArea"><option v-for="area in ((modal.item && modal.item.areas) || [])" :key="area" :value="area">{{ area }}</option></select></div>
        </template>
        <template v-if="modal.type === 'mediaCapability'">
          <template v-if="!capabilityReport">
            <p class="modal-hint">将为已选择的 {{ (modal.item && modal.item.rows ? modal.item.rows.length : 0) }} 台设备设置能力参数；勾选项已按设备当前配置回填，可直接编辑修改。</p>
            <div class="modal-check-grid">
              <label class="video-device-include"><input type="checkbox" v-model="capabilityPtz" />云台控制</label>
            </div>
            <div class="modal-form-row"><label>配置策略：</label><select class="select" v-model="capabilityStrategy"><option value="overwrite">覆盖原能力配置</option><option value="append">仅追加新增能力</option><option value="onlineOnly">仅应用到在线设备</option></select></div>
            <p v-if="capabilityPtz" class="modal-hint">保存时会先探测每台设备的云台能力：不支持的设备不会被设置，保存后会在本弹窗列出明细。</p>
            <p v-if="capabilityProbing" class="modal-hint">正在探测设备云台能力：{{ capabilityProgress.done }}/{{ capabilityProgress.total }} 台…</p>
          </template>
          <template v-else>
            <p class="modal-hint">
              已为 <b>{{ capabilityReport.applied }}</b> 台设备{{ capabilityReport.ptzOn ? "开启云台控制" : "关闭云台控制" }}；共选择 {{ capabilityReport.total }} 台，{{ capabilityReport.skipped.length }} 台未设置。
            </p>
            <div v-if="capabilityReport.skipped.length" class="capability-report">
              <h4>以下设备{{ capabilityReport.ptzOn ? "不支持云台控制" : "未能设置" }}，已忽略：</h4>
              <ul class="capability-report-list">
                <li v-for="item in capabilityReport.skipped" :key="item.name"><b>{{ item.name }}</b><span>{{ item.reason }}</span></li>
              </ul>
            </div>
          </template>
        </template>
        <template v-if="modal.type === 'mediaRegion'">
          <p class="modal-hint">区域树与「所在区域」下拉框数据一致，支持多级区域；拖拽同级节点可调整显示顺序，重命名会同步更新占用该区域的设备（含下级区域）。</p>
          <div class="modal-form-row">
            <label><span class="required">*</span>空间服务地址：</label>
            <div style="display:flex;gap:8px;flex:1;">
              <input class="input" style="flex:1;" v-model.trim="regionSpatialBaseUrl" placeholder="http://172.17.2.131:8080" @keyup.enter="saveSpatialConfig" />
              <button class="btn" :disabled="regionSpatialSaving" @click="saveSpatialConfig">{{ regionSpatialSaving ? '保存中…' : '保存' }}</button>
            </div>
          </div>
          <div class="modal-form-row">
            <label>同步空间区域：</label>
            <div style="display:flex;gap:10px;align-items:center;flex:1;">
              <button class="btn" :disabled="regionSpatialSyncing" @click="syncSpatialRegions">{{ regionSpatialSyncing ? '同步中…' : '⤓ 从空间服务同步' }}</button>
              <span class="hint-text">按上方地址同步，只新增空间树中缺失的园区 / 区域 / 楼栋 / 楼层，已有区域不改动</span>
            </div>
          </div>
          <div class="modal-form-row">
            <label><span class="required">*</span>添加根区域：</label>
            <div style="display:flex;gap:8px;flex:1;">
              <input class="input" style="flex:1;" v-model.trim="regionRootNew" placeholder="请输入根区域名称，如：东区" @keyup.enter="addRootRegion" />
              <button class="btn primary" @click="addRootRegion">＋ 添加</button>
            </div>
          </div>
          <div class="region-editor">
            <div class="region-tree-panel">
              <div
                v-for="row in regionRows"
                :key="row.node.id"
                class="region-tree-row"
                :class="{ selected: regionSelectedId === row.node.id, 'drop-before': regionDropTargetId === row.node.id && regionDropPosition === 'before', 'drop-after': regionDropTargetId === row.node.id && regionDropPosition === 'after' }"
                :style="{ paddingLeft: (row.depth * 18 + 8) + 'px' }"
                draggable="true"
                @click="selectRegion(row)"
                @dragstart="onRegionDragStart($event, row)"
                @dragover="onRegionDragOver($event, row)"
                @dragleave="onRegionDragLeave(row)"
                @drop="onRegionDrop($event, row)"
                @dragend="onRegionDragEnd"
              >
                <span v-if="row.hasChildren" class="region-tree-arrow" @click.stop="toggleRegionExpand(row.fullPath)">{{ isRegionExpanded(row.fullPath) ? '▾' : '▸' }}</span>
                <span v-else class="region-tree-arrow placeholder"></span>
                <span class="region-tree-name">{{ row.node.name }}</span>
                <span v-if="row.node.deviceCount > 0" class="hint-text">（{{ row.node.deviceCount }} 台设备）</span>
              </div>
              <div v-if="!regionRows.length" class="region-tree-empty">暂无区域，请在上方添加根区域</div>
            </div>
            <div class="region-detail-panel">
              <template v-if="regionSelected">
                <p class="modal-hint" style="margin-bottom:10px;">完整路径：{{ regionSelected.fullPath }}</p>
                <div class="modal-form-row" style="grid-template-columns:84px 1fr;margin-bottom:12px;">
                  <label><span class="required">*</span>重命名：</label>
                  <div style="display:flex;gap:8px;flex:1;">
                    <input class="input" style="flex:1;" v-model.trim="regionRenameValue" @keyup.enter="saveRegionRename" />
                    <button class="btn primary" @click="saveRegionRename">保存</button>
                  </div>
                </div>
                <div class="modal-form-row" style="grid-template-columns:84px 1fr;margin-bottom:12px;">
                  <label><span class="required">*</span>添加子节点：</label>
                  <div style="display:flex;gap:8px;flex:1;">
                    <input class="input" style="flex:1;" v-model.trim="regionChildNew" placeholder="请输入子区域名称" @keyup.enter="addChildRegion" />
                    <button class="btn" @click="addChildRegion">添加</button>
                  </div>
                </div>
                <div class="modal-form-row" style="grid-template-columns:84px 1fr;margin-bottom:12px;">
                  <label><span class="required">*</span>添加同级节点：</label>
                  <div style="display:flex;gap:8px;flex:1;">
                    <input class="input" style="flex:1;" v-model.trim="regionSiblingNew" placeholder="请输入同级区域名称" @keyup.enter="addSiblingRegion" />
                    <button class="btn" @click="addSiblingRegion">添加</button>
                  </div>
                </div>
                <div class="modal-form-row" style="grid-template-columns:84px 1fr;margin-bottom:0;">
                  <label>删除区域：</label>
                  <div style="display:flex;gap:10px;align-items:center;flex:1;">
                    <button class="btn danger" :disabled="!regionDeletable" @click="deleteSelectedRegion">删除</button>
                    <span v-if="!regionDeletable" class="hint-text">存在子区域或已挂载设备，不可删除</span>
                  </div>
                </div>
              </template>
              <p v-else class="modal-hint" style="margin-bottom:0;">在左侧选择区域后，可进行重命名、添加子节点 / 同级节点、删除等操作。</p>
            </div>
          </div>
        </template>
        <template v-if="modal.type === 'mediaCloud'">
          <div class="modal-form-grid">
            <div class="modal-form-row"><label><span class="required">*</span>云平台：</label><select class="select" v-model="cloudPlatformId" @change="resetCloudSync"><option value="" disabled>请选择云平台</option><option v-for="platform in cloudPlatforms" :key="platform.id" :value="platform.id">{{ platform.name }}（{{ platform.ip }}:{{ platform.port }}）</option></select></div>
            <div class="modal-form-row" v-if="isGb28181Mode"><label><span class="required">*</span>级联服务器：</label><select class="select" v-model="gb28181EntryId" @change="onGb28181EntryChange"><option value="" disabled>请选择级联服务器</option><option v-for="entry in gb28181Entries" :key="entry.id" :value="entry.id">{{ entry.name }}（{{ entry.sipIp }}:{{ entry.sipPort }}）{{ entry.onlineStatus === 'ONLINE' ? '（在线）' : entry.onlineStatus === 'OFFLINE' ? '（离线）' : '' }}</option></select></div>
            <div class="modal-form-row"><label>冲突处理：</label><select class="select" v-model="cloudConflictStrategy"><option value="overwrite">云端覆盖本地</option><option value="skip">保留本地，仅新增</option></select></div>
            <div class="modal-form-row"><label>所属区域：</label><input class="input" v-model.trim="cloudTargetArea" list="cloud-target-area-options" placeholder="留空则沿用云端区域" /><datalist id="cloud-target-area-options"><option v-for="area in cloudAreaOptions" :key="area" :value="area"></option></datalist></div>
          </div>
          <p v-if="isGb28181Mode && !gb28181Entries.length" class="modal-hint">请先在接入配置页添加级联服务器</p>
          <div class="modal-summary-strip"><strong>预计同步</strong><span v-if="cloudSummary">新增 {{ cloudSummary.newCount }} 台，更新 {{ cloudSummary.updateCount }} 台</span><span v-else>请选择云平台后点击「预检查」</span></div>
          <div class="modal-table-wrap">
            <table class="prototype-table">
              <thead><tr><th style="width:36px;"><input type="checkbox" :checked="cloudAllChecked" :disabled="!cloudItems.length" aria-label="全选云端设备" @change="toggleCloudAll" /></th><th>设备名称</th><th>云端区域</th><th>接入协议</th><th>{{ isGb28181Mode ? '国标编码' : 'IP地址' }}</th><th>处理方式</th></tr></thead>
              <tbody>
                <tr v-for="(item, index) in cloudItems" :key="item.ip || item.gbCode || index"><td><input type="checkbox" v-model="item.checked" /></td><td>{{ item.name }}</td><td>{{ item.area || '-' }}</td><td>{{ item.protocol || '-' }}</td><td>{{ isGb28181Mode ? (item.gbCode || '-') : item.ip }}</td><td><span class="status-pill" :class="item.status === 'new' ? 'pass' : 'waiting'">{{ item.status === 'new' ? '新增' : '更新' }}</span></td></tr>
                <tr v-if="!cloudItems.length"><td colspan="6" class="empty-cell">{{ cloudBusy ? '正在拉取云端设备...' : '尚未预检查' }}</td></tr>
              </tbody>
            </table>
          </div>
        </template>
        <template v-if="modal.type === 'mediaNvrImport'">
          <div class="modal-form-grid">
            <div class="modal-form-row"><label><span class="required">*</span>NVR/CVR地址：</label>
              <div>
                <div v-for="(row, index) in nvrHostRows" :key="index" style="display:flex;gap:6px;margin-bottom:6px;">
                  <input class="input" v-model="nvrHostRows[index]" placeholder="如 192.168.1.100 或 192.168.1.100:8080" />
                  <button class="btn" :disabled="nvrHostRows.length <= 1" @click="removeNvrHostRow(index)">删除</button>
                </div>
                <button class="btn" @click="addNvrHostRow">＋ 添加地址</button>
              </div>
            </div>
            <div class="modal-form-row"><label><span class="required">*</span>登录账号：</label><input class="input" v-model.trim="nvrUsername" placeholder="如 admin" /></div>
            <div class="modal-form-row"><label><span class="required">*</span>登录密码：</label><input class="input" type="password" v-model="nvrPassword" /></div>
            <div class="modal-form-row"><label>所属区域：</label><input class="input" v-model.trim="nvrTargetArea" list="nvr-target-area-options" placeholder="留空则使用默认区域" /><datalist id="nvr-target-area-options"><option v-for="area in nvrAreaOptions" :key="area" :value="area"></option></datalist></div>
          </div>
          <p class="modal-hint">导入仅新增设备：设备列表中已存在的设备（源 IP 相同）会跳过，不会被更新或覆盖。</p>
          <div class="modal-summary-strip"><strong>预计导入</strong><span v-if="nvrSummary">新增 {{ nvrSummary.newCount }} 台，已存在跳过 {{ nvrSummary.existingCount }} 台</span><span v-else>请填写地址与账号后点击「预检查」</span></div>
          <p v-if="nvrSummary && nvrSummary.failures.length" class="modal-hint danger">以下设备读取失败：{{ nvrSummary.failures.map((f) => `${f.host}（${f.reason}）`).join("、") }}</p>
          <div class="modal-table-wrap">
            <table class="prototype-table">
              <thead><tr><th style="width:36px;"><input type="checkbox" :checked="nvrAllChecked" :disabled="!nvrItems.length" aria-label="全选通道" @change="toggleNvrAll" /></th><th>设备名称</th><th>通道</th><th>源IP地址</th><th>所属NVR</th><th>处理方式</th></tr></thead>
              <tbody>
                <tr v-for="item in nvrItems" :key="item.nvrHost + '-' + item.trackId"><td><input type="checkbox" v-model="item.checked" /></td><td>{{ item.name }}</td><td>{{ item.channel }}</td><td>{{ item.ip || '-' }}</td><td>{{ item.nvrHost }}</td><td><span class="status-pill" :class="item.status === 'new' ? 'pass' : 'waiting'">{{ item.status === 'new' ? '新增' : '已存在（跳过）' }}</span></td></tr>
                <tr v-if="!nvrItems.length"><td colspan="6" class="empty-cell">{{ nvrBusy ? '正在读取NVR/CVR通道...' : '尚未预检查' }}</td></tr>
              </tbody>
            </table>
          </div>
        </template>
        <template v-if="modal.type === 'videoConfig'">
          <div class="modal-split video-config-modal">
            <div class="modal-split-main">
              <h4 class="modal-block-title" id="video-config-base">基础配置</h4>
              <div class="modal-form-grid">
                <div class="modal-form-row"><label>保存路径：</label><input class="input" v-model="videoSettings.savePath" /></div>
                <div class="modal-form-row"><label>启动窗口：</label><select class="select" v-model.number="videoSettings.startupLayout"><option :value="4">2x2</option><option :value="1">1x1</option><option :value="9">3x3</option><option :value="16">4x4</option></select></div>
              </div>
              <h4 class="modal-block-title" id="video-config-video">视频配置</h4>
              <div class="modal-form-grid">
                <div class="modal-form-row"><label>重连次数：</label><input class="input" type="number" min="0" v-model.number="videoSettings.reconnectCount" /></div>
                <div class="modal-form-row"><label>重连间隔（秒）：</label><input class="input" type="number" min="1" v-model.number="videoSettings.reconnectIntervalSec" /></div>
                <div class="modal-form-row"><label>码流策略：</label><select class="select" v-model="videoSettings.streamStrategy"><option value="auto">根据窗口数量自动切换</option><option value="main">优先主码流</option><option value="sub" disabled>优先子码流（暂未接入）</option></select></div>
                <div class="modal-form-row"><label>性能阈值：</label><select class="select" v-model="videoSettings.perfThreshold"><option value="cpu80">CPU 超过 80% 切子码流</option><option value="cpu70">CPU 超过 70% 切子码流</option></select></div>
              </div>
              <h4 class="modal-block-title" id="video-config-replay">回放与抓图</h4>
              <div class="modal-form-grid">
                <div class="modal-form-row"><label>即时回放：</label><select class="select" v-model.number="videoSettings.instantReplaySec"><option :value="15">前15秒</option><option :value="30">前30秒</option><option :value="60">前60秒</option></select></div>
                <div class="modal-form-row"><label>录像格式：</label><select class="select" v-model="videoSettings.recordFormat"><option>MP4</option><option>FLV</option></select></div>
                <div class="modal-form-row" id="video-config-snapshot"><label>抓图格式：</label><select class="select" v-model="videoSettings.snapshotFormat"><option>JPG</option><option>PNG</option></select></div>
                <div class="modal-form-row"><label>命名规则：</label><input class="input" v-model="videoSettings.namingRule" placeholder="{设备名称}_{通道}_{时间}" /></div>
              </div>
            </div>
          </div>
        </template>
        <template v-if="modal.type === 'customLayout'">
          <div class="modal-split">
            <div class="modal-split-main">
              <div class="modal-wall-canvas cols-3">
                <div class="media-wall-window active">窗口 1</div>
                <div class="media-wall-window">窗口 2</div>
                <div class="media-wall-window">窗口 3</div>
                <div class="media-wall-window">窗口 4</div>
                <div class="media-wall-window">窗口 5</div>
              </div>
            </div>
            <aside class="modal-split-side" style="flex-basis:220px;">
              <div class="modal-form-row" style="grid-template-columns:70px 1fr;"><label>布局名称：</label><input class="input" value="园区重点点位布局" /></div>
              <div class="modal-form-row" style="grid-template-columns:70px 1fr;"><label>窗口数量：</label><select class="select"><option>5</option><option>7</option><option>10</option><option>13</option><option>17</option></select></div>
              <div class="modal-form-row" style="grid-template-columns:70px 1fr;"><label>画面比例：</label><select class="select"><option>原始宽高比</option><option>满屏窗口</option></select></div>
              <p class="modal-hint">拖拽窗口边界可调整大小，拖拽窗口标题可交换两个播放窗口画面。</p>
            </aside>
          </div>
        </template>
        <template v-if="modal.type === 'quickReplay'">
          <p class="modal-hint">回放当前窗口设备{{ quickReplayCamera ? `「${quickReplayCamera.name}」` : '' }}最近 {{ quickReplaySeconds }} 秒的录像画面。</p>
          <div class="modal-replay-preview">
            <div v-if="quickReplayUrl" style="height:260px;"><video-player :url="quickReplayUrl" format="flv" :show-zoom-bar="false" /></div>
            <template v-else>
              <span>{{ (quickReplayCamera && quickReplayCamera.name) || '未选择设备' }}</span>
              <b v-if="quickReplayLoading">正在查询录像…</b>
              <b v-else-if="quickReplayError">{{ quickReplayError }}</b>
              <b v-else>该设备近期无录像</b>
            </template>
          </div>
          <p v-if="quickReplayUrl" class="modal-hint">{{ quickReplayProgressText }}</p>
          <div class="modal-form-row"><label>回放时长：</label><select class="select" v-model.number="quickReplaySeconds"><option :value="15">前15秒</option><option :value="30">前30秒</option><option :value="60">前60秒</option></select></div>
        </template>
        <template v-if="modal.type === 'recordDownload'">
          <div class="modal-replay-preview"><span>{{ (recordDownloadCamera && recordDownloadCamera.name) || '未选择摄像头' }}</span><b>录像将导出为 MP4 文件，耗时随时段增长</b></div>
          <div class="modal-form-row"><label><span class="required">*</span>开始时间：</label><input class="input" type="datetime-local" v-model="recordDownloadStart" :disabled="!recordDownloadCamera" /></div>
          <div class="modal-form-row"><label><span class="required">*</span>结束时间：</label><input class="input" type="datetime-local" v-model="recordDownloadEnd" :disabled="!recordDownloadCamera" /></div>
          <div class="modal-form-row"><label>文件格式：</label><select class="select" disabled><option>MP4</option></select></div>
          <p v-if="!recordDownloadCamera" class="modal-hint danger">请先到录像回放页选择摄像头和时段，再打开录像下载</p>
          <p v-else-if="recordDownloadError" class="modal-hint danger">{{ recordDownloadError }}</p>
          <div v-if="recordDownloadUrl" class="modal-form-row"><label>下载链接：</label><a :href="recordDownloadUrl" download>点击下载录像 MP4</a></div>
        </template>
        <template v-if="modal.type === 'recordEmpty'">
          <p class="modal-hint">设备「{{ recordEmptyCameraName }}」在 {{ recordEmptyRangeText }} 时段内没有查询到录像。可能是该设备未开启录像计划、未配置录像存储，或所选时段内没有录像数据（录像也可能已过保留期被覆盖）。请确认设备录像配置，或调整查询时间范围后重试。</p>
        </template>
      </div>
      <div class="modal-footer">
        <template v-if="modal.type === 'eventDetail'">
          <button class="btn" @click="$emit('close')">关闭</button>
          <button class="btn primary" @click="$emit('close')">重试</button>
          <button class="btn danger" @click="$emit('close')">删除</button>
        </template>
        <template v-else-if="modal.type === 'reviewTaskDetail'">
          <button class="btn primary" @click="$emit('close')">关闭</button>
        </template>
        <template v-else-if="modal.type === 'mediaImport'">
          <button class="btn" @click="downloadImportTemplate">下载模板</button>
          <button class="btn primary" :disabled="importBusy" @click="runImport">{{ importResult ? '重新导入' : '开始校验 / 导入' }}</button>
        </template>
        <template v-else-if="modal.type === 'mediaExport'">
          <button class="btn" @click="$emit('close')">取消</button>
          <button class="btn primary" @click="runExport">导出</button>
        </template>
        <template v-else-if="modal.type === 'mediaRegion'">
          <button class="btn primary" @click="$emit('close')">关闭</button>
        </template>
        <template v-else-if="modal.type === 'mediaCloud'">
          <button class="btn" :disabled="cloudBusy || !cloudPlatformId || (isGb28181Mode && !gb28181EntryId)" @click="runCloudPrecheck">{{ cloudSummary ? '重新预检查' : '预检查' }}</button>
          <button class="btn primary" :disabled="cloudBusy || !cloudCheckedItems.length" @click="runCloudSync">开始同步</button>
        </template>
        <template v-else-if="modal.type === 'mediaNvrImport'">
          <button class="btn" :disabled="nvrBusy" @click="runNvrPrecheck">{{ nvrSummary ? '重新预检查' : '预检查' }}</button>
          <button class="btn primary" :disabled="nvrBusy || !nvrCheckedItems.length" @click="runNvrSync">开始导入</button>
        </template>
        <template v-else-if="modal.type === 'videoConfig'">
          <button class="btn" @click="resetVideoConfig">恢复默认配置</button>
          <button class="btn" @click="$emit('close')">取消</button>
          <button class="btn primary" @click="saveVideoConfig">确定</button>
        </template>
        <template v-else-if="modal.type === 'quickReplay'">
          <button class="btn" @click="goPlayback">切至历史录像</button>
          <button class="btn primary" @click="$emit('submit', modal.type)">返回实况</button>
        </template>
        <template v-else-if="modal.type === 'recordDownload'">
          <button class="btn" @click="$emit('close')">取消</button>
          <button class="btn primary" :disabled="recordDownloadBusy || !recordDownloadCamera" @click="submitRecordDownload">{{ recordDownloadBusy ? '导出中…' : '开始下载' }}</button>
        </template>
        <template v-else-if="modal.type === 'mediaCapability'">
          <template v-if="capabilityReport">
            <button class="btn primary" @click="$emit('close')">知道了</button>
          </template>
          <template v-else>
            <button class="btn" :disabled="capabilitySaving" @click="$emit('close')">取消</button>
            <button class="btn primary" :disabled="capabilitySaving" @click="handleSubmit">{{ capabilitySaving ? (capabilityProbing ? '探测中…' : '保存中…') : '批量保存' }}</button>
          </template>
        </template>
        <template v-else-if="modal.type === 'recordEmpty'">
          <button class="btn primary" @click="$emit('close')">知道了</button>
        </template>
        <template v-else>
          <button class="btn" @click="$emit('close')">取消</button>
          <button class="btn primary" :class="{ danger: modal.type === 'mediaDelete' }" :disabled="(modal.type === 'mediaCapability' && capabilitySaving) || (modal.type === 'reviewTask' && reviewTaskSubmitting)" @click="handleSubmit">{{ submitLabel }}</button>
        </template>
      </div>
    </section>
  </div>
</template>
