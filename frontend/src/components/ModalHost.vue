<script lang="ts">
import * as XLSX from "xlsx";
import { api } from "../api";
import type { Algorithm, AlgorithmEngine, Camera, CloudPlatform, CloudSyncPrecheck, EventInfo, FaceProfile, LlmConfig, ReviewType } from "../types";
import { statusClass } from "../utils/prototype-helpers";
import { loadPlayerSettings, resetPlayerSettings, savePlayerSettings } from "../utils/player-settings";
import { computeSourceUrl } from "../utils/regions";

export default {
  name: "ModalHost",
  props: ["modal", "store", "state"],
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
      deployTaskName: "",
      deployAlgorithmCode: "",
      deployRecognitionPerMinute: 10,
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
      capabilityVideoPreview: true,
      capabilityAudio: false,
      capabilityTalkback: false,
      capabilityPtz: false,
      capabilitySmartAnalysis: false,
      capabilityAlarmIo: false,
      capabilityStrategy: "overwrite",
      capabilitySaving: false,
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
      cloudItems: [] as any[],
      cloudSummary: null as CloudSyncPrecheck | null,
      cloudBusy: false,
      cloudConflictStrategy: "overwrite",
      cloudTargetArea: "",
      cloudAreaOptions: [] as string[],
      // 录像下载弹窗（上下文来自回放页 openModal('recordDownload', { camera, startTime, endTime })）
      recordDownloadStart: "",
      recordDownloadEnd: "",
      recordDownloadBusy: false,
      recordDownloadUrl: "",
      recordDownloadError: ""
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
    // 选中后按其 algorithmCode 在算法列表中匹配出实际布控算法。
    deploySelectedEventInfo(): EventInfo | undefined {
      return this.deployEventInfos.find((item) => item.code === this.deployAlgorithmCode);
    },
    deploySelectedAlgorithm(): Algorithm | undefined {
      const eventInfo = this.deploySelectedEventInfo;
      if (!eventInfo) return undefined;
      return this.deployAlgorithms.find((item) => item.code === eventInfo.algorithmCode);
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
        reviewTask: "确定",
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
    cloudAllChecked(): boolean {
      return this.cloudItems.length > 0 && this.cloudCheckedItems.length === this.cloudItems.length;
    },
    recordDownloadCamera(): any {
      return (this.modal.item && this.modal.item.camera) || null;
    }
  },
  watch: {
    // 打开弹窗时重新读取设置，保证与上次保存/恢复默认后的值一致
    "modal.type"(type: string) {
      if (type === "videoConfig") this.videoSettings = loadPlayerSettings();
      if (type === "quickReplay") this.quickReplaySeconds = loadPlayerSettings().instantReplaySec;
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
      } else if (this.modal.type === "mediaCapability") {
        this.initCapabilityForm();
      } else if (this.modal.type === "recordDownload") {
        this.initRecordDownloadForm();
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
      this.cloudItems = [];
      this.cloudSummary = null;
      this.cloudBusy = false;
      this.cloudConflictStrategy = "overwrite";
      this.cloudTargetArea = "";
      api.cloudPlatforms()
        .then((rows) => {
          this.cloudPlatforms = rows;
          if (rows.length === 1) this.cloudPlatformId = rows[0].id;
        })
        .catch((error) => this.showToast(`云平台列表加载失败：${error instanceof Error ? error.message : error}`));
      api.cameras()
        .then((list) => {
          const areas = (list || []).map((camera) => (camera.area || "").trim()).filter(Boolean);
          this.cloudAreaOptions = Array.from(new Set(areas));
        })
        .catch(() => {});
    },
    resetCloudSync() {
      this.cloudItems = [];
      this.cloudSummary = null;
    },
    toggleCloudAll(event: any) {
      const checked = !!(event.target && event.target.checked);
      this.cloudItems.forEach((item) => { item.checked = checked; });
    },
    async runCloudPrecheck() {
      if (!this.cloudPlatformId || this.cloudBusy) return;
      this.cloudBusy = true;
      try {
        const result = await api.cloudPlatformPrecheck(this.cloudPlatformId);
        this.cloudSummary = result;
        this.cloudItems = result.items.map((item) => ({ ...item, checked: true }));
        if (!result.items.length) this.showToast("云平台暂无可同步设备");
      } catch (error) {
        this.resetCloudSync();
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
      this.cloudBusy = true;
      try {
        const result = await api.cloudPlatformSync(this.cloudPlatformId, {
          items,
          targetArea: this.cloudTargetArea,
          overwrite: this.cloudConflictStrategy === "overwrite"
        });
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
    // 能力配置弹窗：回填勾选设备当前的能力开关（全部勾选设备都开启时才勾上），用户可再编辑
    initCapabilityForm() {
      const rows = ((this.modal.item && this.modal.item.rows) || []).map((row: any) => row.raw || row);
      const every = (key: string, fallback: boolean) =>
        rows.length ? rows.every((raw: any) => raw[key] === true) : fallback;
      this.capabilityVideoPreview = every("videoPreviewEnabled", true);
      this.capabilityAudio = every("audioEnabled", false);
      this.capabilityTalkback = every("talkbackEnabled", false);
      this.capabilityPtz = every("ptzEnabled", false);
      this.capabilitySmartAnalysis = every("smartAnalysisEnabled", false);
      this.capabilityAlarmIo = every("alarmIoEnabled", false);
      this.capabilityStrategy = "overwrite";
      this.capabilitySaving = false;
    },
    async submitCapability() {
      const rows = ((this.modal.item && this.modal.item.rows) || []).map((row: any) => row.raw || row);
      if (!rows.length) {
        this.showToast("请先选择设备");
        return;
      }
      if (this.capabilitySaving) return;
      this.capabilitySaving = true;
      const desired: Record<string, boolean> = {
        videoPreviewEnabled: this.capabilityVideoPreview,
        audioEnabled: this.capabilityAudio,
        talkbackEnabled: this.capabilityTalkback,
        ptzEnabled: this.capabilityPtz,
        smartAnalysisEnabled: this.capabilitySmartAnalysis,
        alarmIoEnabled: this.capabilityAlarmIo
      };
      let targets = rows;
      if (this.capabilityStrategy === "onlineOnly") {
        targets = rows.filter((raw: any) => String(raw.status || "").toUpperCase() === "RUNNING");
        if (!targets.length) {
          this.capabilitySaving = false;
          this.showToast("所选设备中没有在线设备");
          return;
        }
      }
      let succeeded = 0;
      const failures: string[] = [];
      for (const raw of targets) {
        // 覆盖：六项全量下发；追加：只下发勾选为开的项，其余保持原值
        const payload: Record<string, boolean> = {};
        Object.keys(desired).forEach((key) => {
          if (this.capabilityStrategy !== "append" || desired[key]) payload[key] = desired[key];
        });
        if (!Object.keys(payload).length) {
          succeeded += 1;
          continue;
        }
        try {
          await api.updateCamera(raw.id, payload);
          succeeded += 1;
        } catch (error) {
          failures.push(raw.name || raw.id);
        }
      }
      this.capabilitySaving = false;
      if (succeeded > 0) this.refreshCameras();
      if (!failures.length) {
        this.showToast(`能力配置已应用到 ${succeeded} 台设备`);
        this.$emit("close");
      } else {
        this.showToast(`能力配置完成：成功 ${succeeded} 台，失败 ${failures.length} 台（${failures.join("、")}）`);
      }
    },
    toggleDeployArea(name: string) {
      this.deployAreaExpanded[name] = !this.deployAreaExpanded[name];
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
    cameraStatusText(status?: string) {
      const value = (status || "").toUpperCase();
      if (value === "RUNNING") return "在线";
      if (value === "STOPPED") return "离线";
      if (value === "DISABLED") return "停用";
      return "未成功连接";
    },
    initAlgorithmForm() {
      const item = this.modal.item;
      this.algorithmName = (item && item.name) || "";
      this.algorithmCode = (item && item.code) || "";
      this.algorithmEngineType = (item && item.engineType) || "";
      this.algorithmVersion = "v1.0.0";
      this.algorithmVersionName = "";
      this.algorithmNotes = "";
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
    },
    initDeployTaskForm() {
      const item = this.modal.item;
      const crop = this.deployTargetCrop;
      const defaultName = this.deployTargetImage ? `快速布防-${(crop && crop.sourceName) || "目标"}` : "";
      this.deployTaskName = (item && item.name) || defaultName;
      this.deployAlgorithmCode = (item && item.algorithmCode) || "";
      this.deploySelectedCameras = item && Array.isArray(item.cameraIds) ? [...item.cameraIds] : [];
      this.deployRecognitionPerMinute = (item && item.recognitionPerMinute) || 10;
      this.deployFaceProfileId = (item && item.faceProfileId) || "";
      this.deployDesc = (item && item.desc) || "";
      // 布控目标图：快速布防带入，或编辑回填（仅当目标图不是来自人脸库时）
      this.deployTargetFile = null;
      if (this.deployTargetLocalPreview) URL.revokeObjectURL(this.deployTargetLocalPreview);
      this.deployTargetLocalPreview = "";
      const itemPhotoUrl = item && item.faceProfilePhotoUrl && !item.faceProfileId ? item.faceProfilePhotoUrl : "";
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
          desc: this.deployDesc.trim(),
          area: this.deploySelectedAreas.join("、"),
          areaCount: this.deploySelectedCameras.length
        });
        return;
      }
      if (this.modal.type === "reviewTask") {
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
          协议: "RTSP 拉流",
          IP: "192.168.1.64",
          端口: "554",
          区域: "园区总部 / A区",
          账号: "admin",
          密码: "12345678",
          设备编号: "100000000000000001",
          序列号: "SN-0001",
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
          const protocol = cell("协议");
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
              area: cell("区域") || undefined,
              deviceCode: cell("设备编号") || undefined,
              serialNumber: cell("序列号") || undefined
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
      const statusText = (status?: string) => {
        const value = (status || "").toUpperCase();
        if (value === "RUNNING") return "在线";
        if (value === "STOPPED") return "离线";
        if (value === "DISABLED") return "停用";
        return "未成功连接";
      };
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
          ["状态", (c: Camera) => statusText(c.status)],
          ["描述", (c: Camera) => c.description || ""],
          ["拉流地址", (c: Camera) => c.sourceUrl || ""]
        ],
        base: [
          ["设备名称", (c: Camera) => c.name],
          ["所在区域", (c: Camera) => c.area || "未分配"],
          ["设备编号", (c: Camera) => c.deviceCode || ""],
          ["设备序列号", (c: Camera) => c.serialNumber || ""],
          ["厂商", (c: Camera) => c.vendor || ""],
          ["状态", (c: Camera) => statusText(c.status)]
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
      this.$emit("close");
      this.setRoute("mediaPlayback");
    }
  }
};
</script>

<template>
  <div class="modal-mask" :class="{ open: modal.open }" :aria-hidden="modal.open ? 'false' : 'true'" @click.self="$emit('close')">
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
          <div class="modal-form-row">
            <label><span class="required">*</span>算法名称：</label>
            <input class="input" v-model="algorithmName" placeholder="请输入算法名称" />
          </div>
          <div class="modal-form-row">
            <label><span class="required">*</span>算法编号：</label>
            <input class="input" v-model="algorithmCode" :disabled="isAlgorithmEdit" placeholder="请输入算法编号" />
          </div>
          <div class="modal-form-row" v-if="!isAlgorithmEdit">
            <label><span class="required">*</span>算法引擎：</label>
            <select class="select" v-model="algorithmEngineType">
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
          <div class="modal-form-row" v-if="!isAlgorithmEdit">
            <label><span class="required">*</span>初始版本：</label>
            <input class="input" v-model="algorithmVersion" placeholder="请输入初始版本，如 v1.0.0" />
          </div>
          <div class="modal-form-row" v-if="!isAlgorithmEdit">
            <label>版本名称：</label>
            <input class="input" v-model="algorithmVersionName" placeholder="请输入版本名称" />
          </div>
          <div class="modal-form-row" v-if="!isAlgorithmEdit">
            <label><span class="required">*</span>算法包文件：</label>
            <div class="deploy-target-field">
              <input ref="algorithmPackageInput" class="hidden-file-input" type="file" accept=".zip" @change="handleAlgorithmPackage" />
              <button class="file-upload-tile version-upload-single" type="button" @click="triggerAlgorithmPackage"><span><b>{{ algorithmPackageName || '＋ 上传算法包文件' }}</b><br />仅支持 zip</span></button>
            </div>
          </div>
          <div class="modal-form-row" v-if="!isAlgorithmEdit">
            <label>版本说明：</label>
            <textarea class="textarea" style="height:82px;" v-model="algorithmNotes" placeholder="请输入版本说明"></textarea>
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
            <select class="select" v-model="deployAlgorithmCode">
              <option value="">请选择算法编号</option>
              <option v-for="item in deployEventInfos" :key="item.id" :value="item.code">{{ item.code }}（{{ item.name }}）</option>
            </select>
          </div>
          <div class="modal-form-row">
            <label><span class="required">*</span>布控区域：</label>
            <div class="exact-tree-select deploy-camera-tree">
              <button class="exact-tree-trigger" :class="{ open: deployCameraTreeOpen }" type="button" @click="deployCameraTreeOpen = !deployCameraTreeOpen"><span>{{ deployCameraSummary }}</span><span>{{ deployCameraTreeOpen ? '收起' : '展开' }}⌄</span></button>
              <div v-if="deployCameraTreeOpen" class="exact-tree-dropdown">
                <div v-for="area in deployCameraAreas" :key="area.name">
                  <button class="exact-tree-area-row" type="button" @click="toggleDeployArea(area.name)"><span>{{ deployAreaExpanded[area.name] ? '⌄' : '›' }} {{ area.name }}</span><span>{{ area.cameras.length }} 台设备</span></button>
                  <div v-if="deployAreaExpanded[area.name]" class="exact-tree-children">
                    <label v-for="camera in area.cameras" :key="camera.id" class="exact-tree-device deploy-tree-camera"><input type="checkbox" :checked="deploySelectedCameras.includes(camera.id)" :aria-label="'选择' + camera.name" @change="toggleDeployCamera(camera.id)" /><span class="camera-name">{{ camera.name }}</span><span>{{ cameraStatusText(camera.status) }}</span></label>
                  </div>
                </div>
                <div v-if="!deployCameraAreas.length" class="exact-tree-children"><span style="padding:8px 12px;display:block;">暂无摄像机，请先在设备管理中接入</span></div>
              </div>
            </div>
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
            <strong>{{ importFileName || '拖拽或点击选择文件上传' }}</strong>
            <span>支持 .xlsx / .csv，字段包含设备名称、协议、IP、端口、区域、账号、密码、设备编号。</span>
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
          <div class="modal-form-row"><label>目标区域：</label><select class="select" v-model="moveArea"><option v-for="area in ((modal.item && modal.item.areas) || [])" :key="area" :value="area">{{ area }}</option></select></div>
        </template>
        <template v-if="modal.type === 'mediaCapability'">
          <p class="modal-hint">将为已选择的 {{ (modal.item && modal.item.rows ? modal.item.rows.length : 0) }} 台设备设置能力参数；勾选项已按设备当前配置回填，可直接编辑修改。</p>
          <div class="modal-check-grid">
            <label class="video-device-include"><input type="checkbox" v-model="capabilityVideoPreview" />视频预览</label>
            <label class="video-device-include"><input type="checkbox" v-model="capabilityAudio" />音频采集</label>
            <label class="video-device-include"><input type="checkbox" v-model="capabilityTalkback" />语音对讲</label>
            <label class="video-device-include"><input type="checkbox" v-model="capabilityPtz" />云台控制</label>
            <label class="video-device-include"><input type="checkbox" v-model="capabilitySmartAnalysis" />智能分析</label>
            <label class="video-device-include"><input type="checkbox" v-model="capabilityAlarmIo" />告警输入输出</label>
          </div>
          <div class="modal-form-row"><label>配置策略：</label><select class="select" v-model="capabilityStrategy"><option value="overwrite">覆盖原能力配置</option><option value="append">仅追加新增能力</option><option value="onlineOnly">仅应用到在线设备</option></select></div>
        </template>
        <template v-if="modal.type === 'mediaCloud'">
          <div class="modal-form-grid">
            <div class="modal-form-row"><label>云平台：</label><select class="select" v-model="cloudPlatformId" @change="resetCloudSync"><option value="" disabled>请选择云平台</option><option v-for="platform in cloudPlatforms" :key="platform.id" :value="platform.id">{{ platform.name }}（{{ platform.ip }}:{{ platform.port }}）</option></select></div>
            <div class="modal-form-row"><label>冲突处理：</label><select class="select" v-model="cloudConflictStrategy"><option value="overwrite">云端覆盖本地</option><option value="skip">保留本地，仅新增</option></select></div>
            <div class="modal-form-row"><label>所属区域：</label><input class="input" v-model.trim="cloudTargetArea" list="cloud-target-area-options" placeholder="留空则沿用云端区域" /><datalist id="cloud-target-area-options"><option v-for="area in cloudAreaOptions" :key="area" :value="area"></option></datalist></div>
          </div>
          <div class="modal-summary-strip"><strong>预计同步</strong><span v-if="cloudSummary">新增 {{ cloudSummary.newCount }} 台，更新 {{ cloudSummary.updateCount }} 台</span><span v-else>请选择云平台后点击「预检查」</span></div>
          <div class="modal-table-wrap">
            <table class="prototype-table">
              <thead><tr><th style="width:36px;"><input type="checkbox" :checked="cloudAllChecked" :disabled="!cloudItems.length" aria-label="全选云端设备" @change="toggleCloudAll" /></th><th>设备名称</th><th>云端区域</th><th>接入协议</th><th>IP地址</th><th>处理方式</th></tr></thead>
              <tbody>
                <tr v-for="(item, index) in cloudItems" :key="item.ip || index"><td><input type="checkbox" v-model="item.checked" /></td><td>{{ item.name }}</td><td>{{ item.area || '-' }}</td><td>{{ item.protocol || '-' }}</td><td>{{ item.ip }}</td><td><span class="status-pill" :class="item.status === 'new' ? 'pass' : 'waiting'">{{ item.status === 'new' ? '新增' : '更新' }}</span></td></tr>
                <tr v-if="!cloudItems.length"><td colspan="6" class="empty-cell">{{ cloudBusy ? '正在拉取云端设备...' : '尚未预检查' }}</td></tr>
              </tbody>
            </table>
          </div>
        </template>
        <template v-if="modal.type === 'mediaDelete'">
          <p class="modal-hint danger">将删除 {{ (modal.item && modal.item.rows ? modal.item.rows.length : 0) }} 台设备。删除后将解除设备、通道、预览分组和告警联动关系。历史录像索引可按策略保留。</p>
          <div class="modal-form-row"><label>删除选项：</label><span style="padding-top:7px;"><label class="video-device-include"><input type="checkbox" />同时删除通道配置</label></span></div>
        </template>
        <template v-if="modal.type === 'videoConfig'">
          <div class="modal-split">
            <div class="modal-split-main">
              <h4 class="modal-block-title" id="video-config-base">基础配置</h4>
              <div class="modal-form-grid">
                <div class="modal-form-row"><label>保存路径：</label><input class="input" v-model="videoSettings.savePath" /></div>
                <div class="modal-form-row"><label>启动窗口：</label><select class="select" v-model.number="videoSettings.startupLayout"><option :value="4">2x2</option><option :value="1">1x1</option><option :value="9">3x3</option><option :value="16">4x4</option></select></div>
              </div>
              <div class="modal-check-grid" style="grid-template-columns:repeat(2,minmax(0,1fr));">
                <label class="video-device-include"><input type="checkbox" v-model="videoSettings.perfWarning" />播放性能不足提示</label>
                <label class="video-device-include"><input type="checkbox" v-model="videoSettings.gpuDecode" />GPU 硬件解码</label>
                <label class="video-device-include"><input type="checkbox" v-model="videoSettings.recordWarning" />录像预警提示</label>
                <label class="video-device-include"><input type="checkbox" v-model="videoSettings.multicast" />是否组播</label>
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
          <p class="modal-hint">无需配置录像存储，直接回看当前预览时间点前 15 秒画面。</p>
          <div class="modal-replay-preview"><span>真实黄区球机_通道_1</span><b>正在回放 00:00:11 / 00:00:15</b></div>
          <div class="modal-form-row"><label>回放时长：</label><select class="select" v-model.number="quickReplaySeconds"><option :value="15">前15秒</option><option :value="30">前30秒</option><option :value="60">前60秒</option></select></div>
        </template>
        <template v-if="modal.type === 'recordDownload'">
          <div class="modal-replay-preview"><span>{{ (recordDownloadCamera && recordDownloadCamera.name) || '未选择摄像头' }}</span><b>录像将导出为 MP4 文件，耗时随时段增长</b></div>
          <div class="modal-form-row"><label>开始时间：</label><input class="input" type="datetime-local" v-model="recordDownloadStart" :disabled="!recordDownloadCamera" /></div>
          <div class="modal-form-row"><label>结束时间：</label><input class="input" type="datetime-local" v-model="recordDownloadEnd" :disabled="!recordDownloadCamera" /></div>
          <div class="modal-form-row"><label>文件格式：</label><select class="select" disabled><option>MP4</option></select></div>
          <p v-if="!recordDownloadCamera" class="modal-hint danger">请先到录像回放页选择摄像头和时段，再打开录像下载</p>
          <p v-else-if="recordDownloadError" class="modal-hint danger">{{ recordDownloadError }}</p>
          <div v-if="recordDownloadUrl" class="modal-form-row"><label>下载链接：</label><a :href="recordDownloadUrl" download>点击下载录像 MP4</a></div>
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
        <template v-else-if="modal.type === 'mediaCloud'">
          <button class="btn" :disabled="cloudBusy || !cloudPlatformId" @click="runCloudPrecheck">{{ cloudSummary ? '重新预检查' : '预检查' }}</button>
          <button class="btn primary" :disabled="cloudBusy || !cloudCheckedItems.length" @click="runCloudSync">开始同步</button>
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
        <template v-else>
          <button class="btn" @click="$emit('close')">取消</button>
          <button class="btn primary" :class="{ danger: modal.type === 'mediaDelete' }" :disabled="modal.type === 'mediaCapability' && capabilitySaving" @click="handleSubmit">{{ submitLabel }}</button>
        </template>
      </div>
    </section>
  </div>
</template>
