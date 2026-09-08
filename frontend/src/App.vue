<script lang="ts">
import { defineComponent } from "vue";
import { store } from "./store";
import { api } from "./api";
import type { DeploymentTaskCreate } from "./types";
import { APP_DEFAULT_ROUTE } from "./router";
import AppSidebar from "./components/AppSidebar.vue";
import AppTopbar from "./components/AppTopbar.vue";
import DrawerHost from "./components/DrawerHost.vue";
import ModalHost from "./components/ModalHost.vue";
import ImageCropDialog from "./components/ImageCropDialog.vue";
import SxinAgent from "./components/SxinAgent.vue";

export default defineComponent({
  components: {
    AppSidebar,
    AppTopbar,
    DrawerHost,
    ModalHost,
    ImageCropDialog,
    SxinAgent
  },
  data() {
    return {
      store,
      state: {
        route: "home",
        routeVersion: 0,
        trackView: "timeline",
        prefill: "",
        imageCrop: null as any,
        selectedResultIndexes: [] as any[],
        camerasVersion: 0
      },
      selectedVersion: store.versionRows[0],
      selectedDeployTask: store.deployTaskRows[0],
      selectedEvent: store.eventRows[0],
      selectedAlgorithm: null as any,
      selectedCamera: null as any,
      drawer: {
        open: false,
        type: "",
        title: "",
        item: null as any,
        resultIndex: -1
      } as any,
      drawerCrop: {
        open: false,
        action: "",
        item: null as any,
        itemIndex: -1
      },
      modal: {
        open: false,
        type: "",
        title: "",
        narrow: false
      } as any,
      toast: {
        show: false,
        message: ""
      },
      toastTimer: null as any,
      sidebarCollapsed: false,
      sxinOpen: false,
      sxinMessageHandler: null as any
    };
  },
  watch: {
    "$route.name": {
      immediate: true,
      handler(name: any) {
        if (name) this.state.route = String(name);
      }
    }
  },
  provide() {
    return {
      setRoute: (route: string, options?: any) => this.setRoute(route, options),
      showToast: (message: string) => this.showToast(message),
      openResult: (index: number, item?: any) => this.openResult(index, item),
      openReviewTask: (index: number) => this.openReviewTask(index),
      openModal: (type: string, item?: any) => this.openModal(type, item),
      clearImage: () => this.clearImage(),
      setTrackView: (view: string) => this.setTrackView(view),
      openVersionManager: (row: any) => this.openVersionManager(row),
      openVersionDetail: (row: any) => this.openVersionDetail(row),
      openVersionPreview: (row: any) => this.openVersionPreview(row),
      openDeployDetail: (row: any) => this.openDeployDetail(row),
      openEventDetail: (row: any) => this.openEventDetail(row),
      openCameraDetail: (row: any) => this.openCameraDetail(row),
      openCameraEdit: (row: any) => this.openCameraEdit(row),
      refreshCameras: () => this.refreshCameras()
    };
  },
  mounted() {
    this.sxinMessageHandler = (event: MessageEvent) => {
      const payload = event.data;
      const frame = document.querySelector(".sxin-embed-frame");
      if (!this.sxinOpen || !frame || event.source !== (frame as HTMLIFrameElement).contentWindow || !payload || payload.type !== "sxin-result-crop-confirm") return;
      this.handleSxinCropConfirm(payload);
    };
    window.addEventListener("message", this.sxinMessageHandler);
  },
  beforeUnmount() {
    if (this.sxinMessageHandler) window.removeEventListener("message", this.sxinMessageHandler);
  },
  methods: {
    handleNav(item: any) {
      if (item.pending) {
        this.showToast("待确认当前模块后继续完善");
        return;
      }
      this.setRoute(item.key);
    },
    setRoute(route: string, options: any = {}) {
      const previousRoute = this.state.route;
      if (route === "newDeployTask") {
        this.openModal("deployTask");
        route = "deployTasks";
      }
      if (route === "newAlgorithm") {
        this.openModal("algorithm");
        route = "algorithms";
      }
      if (route === "newVersion") {
        this.openModal("version");
        route = "versionManager";
      }
      // 子包构建只含本模块路由：跨模块跳转回退到子包默认路由。
      // 全量模式所有 route 均存在，行为零变化。
      if (!this.$router.hasRoute(route)) route = APP_DEFAULT_ROUTE;
      if (options.prefill) this.state.prefill = options.prefill;
      if (Object.prototype.hasOwnProperty.call(options, "imageCrop")) this.state.imageCrop = options.imageCrop;
      else if (options.prefill) this.state.imageCrop = null;
      if (options.trackView) this.state.trackView = options.trackView;
      if (Array.isArray(options.selectedIndexes)) {
        this.state.selectedResultIndexes = [...options.selectedIndexes];
      } else if (route === "track") {
        this.state.selectedResultIndexes = [];
      }
      this.state.route = route;
      if (previousRoute === route) this.state.routeVersion += 1;
      this.$router.push({ name: route, query: options.query }).catch(() => {});
      this.$nextTick(() => {
        const workspace = document.getElementById("workspace");
        if (workspace) workspace.scrollTo({ top: 0, behavior: "instant" as ScrollBehavior });
      });
    },
    setTrackView(view: string) {
      this.state.trackView = view;
    },
    clearImage() {
      this.state.prefill = "";
      this.state.imageCrop = null;
      this.showToast("已清除参考图");
    },
    openResult(index: number, item?: any) {
      // Pages with backend-loaded results (e.g. 图搜图) pass their own item;
      // otherwise fall back to the prototype's mock gallery.
      const resolved = item || this.store.results[index] || this.store.results[0];
      const resultIndex = item ? -1 : (this.store.results[index] ? index : 0);
      this.drawer = { open: true, type: "result", title: "分析结果详情", item: resolved, resultIndex, contextRoute: this.state.route };
    },
    openReviewTask(index: number) {
      const item = this.store.reviewTasks[index] || this.store.reviewTasks[0];
      this.drawer = { open: true, type: "reviewTask", title: "复核任务详情", item };
    },
    closeDrawer() {
      this.drawer.open = false;
    },
    handleDrawerRoute(route: string) {
      const selected = this.drawer.item;
      this.closeDrawer();
      this.setRoute(route, { prefill: selected && selected.image, trackView: route === "track" ? "timeline" : this.state.trackView });
    },
    openQuickDeployModal() {
      const selected = this.drawer.item;
      if (selected && selected.image) this.state.prefill = selected.image;
      this.closeDrawer();
      this.openModal("deployTask");
    },
    openDrawerCrop(action: string) {
      const item = this.drawer.item;
      if (!item) return;
      const itemIndex = Number.isInteger(this.drawer.resultIndex) ? this.drawer.resultIndex : this.store.results.indexOf(item);
      this.drawerCrop = { open: true, action, item, itemIndex };
      this.closeDrawer();
    },
    closeDrawerCrop() {
      this.drawerCrop = { open: false, action: "", item: null, itemIndex: -1 };
    },
    confirmDrawerCrop(payload: any) {
      const { action, item, index, crop: selection } = payload;
      const crop = { ...selection, sourceName: item.title, sourceTime: item.date, sourceIndex: index };
      this.closeDrawerCrop();
      if (action === "imageSearch") {
        this.setRoute("imageSearch", { prefill: item.image, imageCrop: crop });
      } else if (action === "quickDeploy") {
        this.setRoute("newDeployTask", { prefill: item.image, imageCrop: crop });
      } else if (action === "track") {
        this.setRoute("track", { prefill: item.image, imageCrop: crop, selectedIndexes: [index], trackView: "timeline" });
      }
    },
    openModal(type: string, item: any = null) {
      const config = ({
        reviewTask: { title: "事件判断", narrow: false },
        reviewTaskDetail: { title: "复核结果详情", narrow: false },
        eventDetail: { title: "事件详情", narrow: false },
        algorithm: { title: item && item.id ? "编辑算法" : "新增算法", narrow: false },
        deployTask: { title: item && item.id ? "编辑布控任务" : "新建布控任务", narrow: false },
        version: { title: "新增版本号", narrow: false },
        eventSource: { title: "新增数据源", narrow: false },
        permissionRole: { title: "新建角色", narrow: false },
        mediaImport: { title: "批量导入设备", wide: true },
        mediaExport: { title: "导出设备", narrow: true },
        mediaMove: { title: "批量设备移动", narrow: true },
        mediaCapability: { title: "批量配置设备能力", narrow: true },
        mediaCloud: { title: "从云平台同步设备", wide: true },
        mediaDelete: { title: "删除设备", narrow: true },
        videoConfig: { title: "视频参数配置", wide: true },
        customLayout: { title: "自定义分屏布局", wide: true },
        quickReplay: { title: "即时回放", narrow: true },
        recordDownload: { title: "下载录像", narrow: true }
      } as any)[type] || { title: "新增", narrow: false };
      this.modal = { open: true, type, title: config.title, narrow: !!config.narrow, wide: !!config.wide, item };
    },
    closeModal() {
      // 关闭新建布控任务弹窗时，清掉快速布防带入的目标图，避免下次新建残留
      if (this.modal.type === "deployTask" && !(this.modal.item && this.modal.item.id)) {
        this.state.prefill = "";
        this.state.imageCrop = null;
      }
      this.modal.open = false;
    },
    async submitModal(type: string, payload?: any) {
      if (type === "mediaDelete") {
        this.submitMediaDelete();
        return;
      }
      if (type === "mediaMove") {
        this.submitMediaMove();
        return;
      }
      if (type === "algorithm") {
        await this.submitAlgorithm(payload || {});
        return;
      }
      if (type === "deployTask") {
        await this.submitDeployTask(payload || {});
        return;
      }
      if (type === "reviewTask") {
        await this.submitReviewTask(payload || {});
        return;
      }
      const messages: Record<string, string> = {
        version: "版本号已保存，已停留在版本号管理页面",
        eventSource: "数据源已保存，已停留在事件配置页面",
        permissionRole: "角色已保存，已停留在权限中心页面",
        mediaImport: "导入文件校验已通过，设备已加入导入队列",
        mediaExport: "设备列表已按当前范围导出",
        mediaCapability: "设备能力配置已批量保存",
        videoConfig: "视频参数配置已保存",
        customLayout: "自定义分屏布局已保存",
        quickReplay: "已返回实时预览画面",
        recordDownload: "录像下载任务已创建"
      };
      this.closeModal();
      this.showToast(messages[type] || "配置已保存");
      if (type === "version") this.setRoute("versionManager");
      if (type === "eventSource") this.setRoute("eventConfig");
      if (type === "permissionRole") this.setRoute("permissions");
    },
    async submitReviewTask(payload: any) {
      if (!payload.reviewTypeId || !payload.llmConfigId || !payload.image) {
        this.showToast("请选择事件编码、大模型并上传图片");
        return;
      }
      const form = new FormData();
      form.append("reviewTypeId", payload.reviewTypeId);
      form.append("llmConfigId", payload.llmConfigId);
      form.append("image", payload.image);
      try {
        await api.createReviewTask(form);
        this.closeModal();
        this.showToast("复核任务已提交，大模型研判中");
        store.reviewTasksVersion += 1;
        this.setRoute("reviewTasks");
      } catch (error) {
        // 提交失败时保留弹窗，便于用户修正后重试
        this.showToast(error instanceof Error ? error.message : "复核任务提交失败");
      }
    },
    async submitAlgorithm(payload: any) {
      try {
        if (payload.id) {
          await api.updateAlgorithm(payload.id, {
            name: payload.name || undefined,
            scene: payload.scene || undefined,
            owner: payload.owner || undefined,
            description: payload.description || undefined
          });
          this.showToast("算法已更新");
        } else {
          if (!payload.name || !payload.code || !payload.engineType || !payload.version) {
            this.showToast("请填写算法名称、编号、引擎和初始版本");
            return;
          }
          if (!payload.file) {
            this.showToast("请上传算法包 zip 文件");
            return;
          }
          const form = new FormData();
          form.append("name", payload.name);
          form.append("code", payload.code);
          form.append("engineType", payload.engineType);
          form.append("version", payload.version);
          if (payload.scene) form.append("scene", payload.scene);
          if (payload.owner) form.append("owner", payload.owner);
          if (payload.description) form.append("description", payload.description);
          if (payload.versionName) form.append("versionName", payload.versionName);
          if (payload.notes) form.append("notes", payload.notes);
          form.append("file", payload.file);
          await api.createAlgorithm(form);
          this.showToast("算法已创建");
        }
        this.closeModal();
        // 同路由跳转触发 routeVersion 自增，页面重挂载刷新列表
        this.setRoute("algorithms");
      } catch (error) {
        this.showToast(error instanceof Error ? error.message : "算法保存失败");
      }
    },
    async submitDeployTask(payload: any) {
      if (!payload.name) {
        this.showToast("请输入任务名称");
        return;
      }
      if (!payload.cameraIds || !payload.cameraIds.length) {
        this.showToast("请选择布控点位");
        return;
      }
      const body: DeploymentTaskCreate = {
        name: payload.name,
        pipeline: payload.algorithmName || "",
        algorithmId: payload.algorithmId,
        algorithmName: payload.algorithmName,
        algorithmCode: payload.algorithmCode,
        engineType: payload.engineType,
        cameraIds: payload.cameraIds,
        faceProfileId: payload.faceProfileId,
        faceProfilePhotoUrl: payload.faceProfilePhotoUrl || null,
        recognitionPerMinute: payload.recognitionPerMinute,
        desc: payload.desc,
        area: payload.area || null,
        areaCount: payload.areaCount
      };
      try {
        if (payload.id) {
          await api.updateDeploymentTask(payload.id, body);
          this.showToast("布控任务已更新");
        } else {
          await api.createDeploymentTask(body);
          this.showToast("布控任务已创建");
        }
        this.closeModal();
        this.setRoute("deployTasks");
      } catch (error) {
        this.showToast(error instanceof Error ? error.message : "布控任务保存失败");
      }
    },
    async submitMediaDelete() {
      const rows = (this.modal.item && this.modal.item.rows) || [];
      this.closeModal();
      let succeeded = 0;
      let failed = 0;
      for (const row of rows) {
        try {
          await api.deleteCamera(row.id);
          succeeded += 1;
        } catch {
          failed += 1;
        }
      }
      if (failed === 0) this.showToast(`已删除 ${succeeded} 台设备`);
      else this.showToast(`已删除 ${succeeded} 台设备，${failed} 台删除失败`);
      this.refreshCameras();
    },
    async submitMediaMove() {
      const item = this.modal.item || {};
      const rows = item.rows || [];
      const area = item.area;
      this.closeModal();
      if (!area) {
        this.showToast("请选择目标区域");
        return;
      }
      let succeeded = 0;
      let failed = 0;
      for (const row of rows) {
        try {
          await api.updateCamera(row.id, { area });
          succeeded += 1;
        } catch {
          failed += 1;
        }
      }
      if (failed === 0) this.showToast(`已移动 ${succeeded} 台设备到「${area}」`);
      else this.showToast(`已移动 ${succeeded} 台设备，${failed} 台移动失败`);
      this.refreshCameras();
    },
    openVersionManager(row: any) {
      this.selectedAlgorithm = row;
      this.setRoute("versionManager", row && row.id ? { query: { algorithmId: row.id } } : {});
    },
    openVersionDetail(row: any) {
      this.selectedVersion = row || this.store.versionRows[0];
      this.setRoute("versionDetail");
    },
    openVersionPreview(row: any) {
      this.selectedVersion = row || this.store.versionRows[0];
      this.setRoute("previewFile");
    },
    openDeployDetail(row: any) {
      this.selectedDeployTask = row || this.store.deployTaskRows[0];
      this.setRoute("deployTaskDetail");
    },
    openEventDetail(row: any) {
      this.selectedEvent = row || this.store.eventRows[0];
      this.setRoute("eventDetail");
    },
    openCameraDetail(row: any) {
      this.selectedCamera = row;
      this.setRoute("mediaDeviceDetail");
    },
    openCameraEdit(row: any) {
      this.selectedCamera = row;
      this.setRoute("mediaDeviceEdit");
    },
    refreshCameras() {
      this.state.camerasVersion = (this.state.camerasVersion || 0) + 1;
    },
    handleDrawerAction(name: string) {
      const messages: Record<string, string> = {
        approveReview: "复核已通过，任务状态已模拟更新",
        rejectReview: "复核已驳回，结果将沉淀为误报样本",
        generateReviewReport: "复核报告已生成，可用于客户演示"
      };
      this.showToast(messages[name] || "操作已模拟完成");
    },
    openSxin() {
      this.sxinOpen = true;
    },
    closeSxin() {
      this.sxinOpen = false;
    },
    handleSxinRoute(route: string) {
      this.setRoute(route);
      this.closeSxin();
    },
    handleSxinCropConfirm(payload: any) {
      const { action, item, crop: selection } = payload;
      if (!item || !item.img || !selection || !["imageSearch", "quickDeploy", "track"].includes(action)) return;
      const crop = {
        ...selection,
        sourceName: item.title,
        sourceTime: item.time,
        sourceIndex: -1
      };
      this.closeSxin();
      if (action === "imageSearch") {
        this.setRoute("imageSearch", { prefill: item.img, imageCrop: crop });
      } else if (action === "quickDeploy") {
        this.setRoute("newDeployTask", { prefill: item.img, imageCrop: crop });
      } else {
        this.setRoute("track", { prefill: item.img, imageCrop: crop, selectedIndexes: [], trackView: "timeline" });
      }
    },
    showToast(message: string) {
      this.toast.message = message;
      this.toast.show = true;
      clearTimeout(this.toastTimer);
      this.toastTimer = setTimeout(() => {
        this.toast.show = false;
      }, 1700);
    }
  }
});
</script>

<template>
  <div class="app" :class="{ 'sidebar-collapsed': sidebarCollapsed }">
    <app-sidebar :groups="store.navGroups" :route="state.route" :collapsed="sidebarCollapsed" @navigate="handleNav" @toggle-sidebar="sidebarCollapsed = !sidebarCollapsed"></app-sidebar>
    <section class="shell">
      <app-topbar :route="state.route" :names="store.routeNames"></app-topbar>
      <main class="workspace" id="workspace">
        <div class="workspace-inner">
          <router-view :key="state.route + '-' + state.routeVersion" :store="store" :state="state" :selected-version="selectedVersion" :selected-deploy-task="selectedDeployTask" :selected-event="selectedEvent" :selected-algorithm="selectedAlgorithm" :selected-camera="selectedCamera"></router-view>
        </div>
      </main>
    </section>
  </div>
  <drawer-host :drawer="drawer" :store="store" @close="closeDrawer" @route="handleDrawerRoute" @action="handleDrawerAction" @quick-deploy="openQuickDeployModal" @crop-action="openDrawerCrop"></drawer-host>
  <image-crop-dialog :open="drawerCrop.open" :item="drawerCrop.item" :action="drawerCrop.action" :item-index="drawerCrop.itemIndex" @close="closeDrawerCrop" @confirm="confirmDrawerCrop"></image-crop-dialog>
  <modal-host :modal="modal" :store="store" :state="state" @close="closeModal" @submit="submitModal"></modal-host>
  <button v-if="!sxinOpen" class="sxin-fab" title="打开 SXin 智能体" aria-label="打开 SXin 智能体" @click="openSxin"><span class="sxin-fab-mark">S</span></button>
  <sxin-agent v-if="sxinOpen" @close="closeSxin"></sxin-agent>
  <div class="toast" :class="{ show: toast.show }">{{ toast.message }}</div>
</template>
