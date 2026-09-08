<template>
  <section class="content review-wide">
    <div class="review-titlebar">
      <div><h1>{{ titleText }}</h1><p>版本号管理作为算法管理二级页面，从算法列表的版本号入口进入</p></div>
      <div class="segmented"><button class="btn" @click="setRoute('algorithms')">返回算法管理</button><button class="btn primary" :disabled="!currentAlgorithmId" @click="openCreate">新增版本号</button></div>
    </div>
    <summary-cards :cards="cards"></summary-cards>
    <div class="review-board">
      <div class="page-actions">
        <div class="left">
          <select class="select" style="width:220px;" v-model="currentAlgorithmId" @change="onAlgorithmChange">
            <option value="">请选择算法</option>
            <option v-for="algorithm in algorithms" :key="algorithm.id" :value="algorithm.id">{{ algorithm.name }}（{{ algorithm.code }}）</option>
          </select>
          <input class="input" style="width:240px;" v-model="keyword" placeholder="搜索版本号、版本名称" />
          <select class="select" style="width:150px;" v-model="statusFilter"><option value="">全部状态</option><option value="READY">就绪</option><option value="MISSING_FILES">缺模型文件</option><option value="active">当前版本</option></select>
        </div>
        <div class="right"><button class="btn" @click="loadVersions">查询</button><button class="btn" @click="resetFilters">重置</button></div>
      </div>
      <table class="prototype-table">
        <colgroup><col style="width:110px;" /><col style="width:150px;" /><col style="width:100px;" /><col style="width:120px;" /><col /><col style="width:150px;" /><col style="width:90px;" /></colgroup>
        <thead><tr><th>版本号</th><th class="left">版本名称</th><th>状态</th><th>是否当前版本</th><th class="left">版本说明</th><th>创建时间</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="row in filteredRows" :key="row.id">
            <td><span class="mini-tag">{{ row.version }}</span></td>
            <td class="left">{{ row.versionName || "—" }}</td>
            <td>
              <span v-if="row.status === 'READY'" class="status-pill pass">就绪</span>
              <span v-else class="status-pill waiting" :title="'缺失文件：' + (row.missingFiles || []).join('、')">缺模型文件</span>
            </td>
            <td><span v-if="row.active" class="status-pill processing">当前版本</span><span v-else>—</span></td>
            <td class="left ellipsis" :title="row.notes || ''">{{ row.notes || "—" }}</td>
            <td>{{ formatTime(row.createdAt) }}</td>
            <td><button v-if="!row.active" class="link-blue" @click="activate(row)">发布</button><span v-else>—</span></td>
          </tr>
          <tr v-if="!loading && !currentAlgorithmId"><td colspan="7" class="empty-cell">请先选择算法</td></tr>
          <tr v-else-if="!loading && !filteredRows.length"><td colspan="7" class="empty-cell">暂无版本</td></tr>
          <tr v-if="loading"><td colspan="7" class="empty-cell">加载中...</td></tr>
        </tbody>
      </table>
    </div>
    <div v-if="modalOpen" class="event-config-modal-mask" @click.self="closeForm">
      <section class="event-config-modal" role="dialog" aria-modal="true" aria-label="新增版本号">
        <div class="event-config-modal-head"><h3>新增版本号</h3><button class="event-config-modal-close" aria-label="关闭" @click="closeForm">×</button></div>
        <div class="modal-form-row">
          <label><span class="required">*</span>版本号：</label>
          <input class="input" v-model="form.version" placeholder="请输入版本号，如 v1.0.1" />
        </div>
        <div class="modal-form-row">
          <label>版本名称：</label>
          <input class="input" v-model="form.versionName" placeholder="请输入版本名称" />
        </div>
        <div class="modal-form-row">
          <label>版本说明：</label>
          <textarea class="textarea" style="height:72px;" v-model="form.notes" placeholder="请输入本次版本优化内容"></textarea>
        </div>
        <div class="modal-form-row">
          <label><span class="required">*</span>版本文件：</label>
          <div class="deploy-target-field">
            <input ref="versionFileInput" class="hidden-file-input" type="file" accept=".zip" @change="handleFile" />
            <button class="file-upload-tile version-upload-single" type="button" @click="triggerFile"><span><b>{{ form.fileName || '＋ 上传版本文件' }}</b><br />仅支持 zip，上传后服务端会先备份旧版本再安装</span></button>
          </div>
        </div>
        <div class="event-config-modal-actions"><button class="btn" @click="closeForm">取消</button><button class="btn primary" :disabled="saving" @click="save">保存</button></div>
      </section>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import SummaryCards from "../components/SummaryCards.vue";
import { api } from "../api";
import type { Algorithm, AlgorithmVersion } from "../types";

function formatTime(iso?: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const pad = (n: number) => n.toString().padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export default defineComponent({
  name: "VersionManagerPage",
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  components: { SummaryCards },
  inject: {
    setRoute: { from: "setRoute", default: (route: string, options?: any) => {} },
    showToast: { from: "showToast", default: (m: string) => {} }
  },
  data() {
    return {
      algorithms: [] as Algorithm[],
      versions: [] as AlgorithmVersion[],
      currentAlgorithmId: "",
      loading: false,
      keyword: "",
      statusFilter: "",
      modalOpen: false,
      saving: false,
      form: {
        version: "",
        versionName: "",
        notes: "",
        file: null as File | null,
        fileName: ""
      }
    };
  },
  computed: {
    currentAlgorithm(): Algorithm | undefined {
      return this.algorithms.find((item) => item.id === this.currentAlgorithmId);
    },
    titleText(): string {
      return this.currentAlgorithm ? `${this.currentAlgorithm.name} 版本号管理` : "版本号管理";
    },
    filteredRows(): AlgorithmVersion[] {
      const keyword = this.keyword.trim().toLowerCase();
      return this.versions.filter((row) => {
        if (keyword && !`${row.version}${row.versionName || ""}`.toLowerCase().includes(keyword)) return false;
        if (this.statusFilter === "active" && !row.active) return false;
        if (this.statusFilter && this.statusFilter !== "active" && row.status !== this.statusFilter) return false;
        return true;
      });
    },
    cards(): any[] {
      return [
        { label: "版本总数", value: this.versions.length },
        { label: "当前版本", value: this.versions.filter((row) => row.active).length },
        { label: "就绪", value: this.versions.filter((row) => row.status === "READY").length },
        { label: "缺模型", value: this.versions.filter((row) => row.status === "MISSING_FILES").length }
      ];
    }
  },
  watch: {
    "$route.query.algorithmId"(value: any) {
      const id = value ? String(value) : "";
      if (id && id !== this.currentAlgorithmId) {
        this.currentAlgorithmId = id;
        this.loadVersions();
      }
    }
  },
  mounted() {
    this.init();
  },
  methods: {
    formatTime,
    async init() {
      try {
        this.algorithms = await api.algorithms();
      } catch (error) {
        this.showToast(error instanceof Error ? error.message : "算法列表加载失败");
      }
      const queryId = this.$route.query.algorithmId ? String(this.$route.query.algorithmId) : "";
      const injected = (this as any).selectedAlgorithm;
      this.currentAlgorithmId = queryId || (injected && injected.id) || "";
      if (this.currentAlgorithmId) await this.loadVersions();
    },
    onAlgorithmChange() {
      this.loadVersions();
    },
    resetFilters() {
      this.keyword = "";
      this.statusFilter = "";
    },
    async loadVersions() {
      if (!this.currentAlgorithmId) {
        this.versions = [];
        return;
      }
      if (this.loading) return;
      this.loading = true;
      try {
        this.versions = await api.algorithmVersions(this.currentAlgorithmId);
      } catch (error) {
        this.showToast(error instanceof Error ? error.message : "版本列表加载失败");
      } finally {
        this.loading = false;
      }
    },
    openCreate() {
      this.form = { version: "", versionName: "", notes: "", file: null, fileName: "" };
      this.modalOpen = true;
    },
    closeForm() {
      this.modalOpen = false;
    },
    triggerFile() {
      const input: any = this.$refs.versionFileInput;
      if (input) input.click();
    },
    handleFile(event: any) {
      const file = event.target.files && event.target.files[0];
      if (file && !/\.zip$/i.test(file.name)) {
        this.showToast("版本文件仅支持 zip");
        event.target.value = "";
        return;
      }
      this.form.file = file || null;
      this.form.fileName = file ? file.name : "";
    },
    async save() {
      const version = this.form.version.trim();
      if (!version) {
        this.showToast("请输入版本号");
        return;
      }
      if (!this.form.file) {
        this.showToast("请上传版本 zip 文件");
        return;
      }
      if (this.saving) return;
      this.saving = true;
      try {
        const form = new FormData();
        form.append("version", version);
        if (this.form.versionName.trim()) form.append("versionName", this.form.versionName.trim());
        if (this.form.notes.trim()) form.append("notes", this.form.notes.trim());
        form.append("file", this.form.file);
        await api.createAlgorithmVersion(this.currentAlgorithmId, form);
        this.showToast(`版本 ${version} 已创建`);
        this.closeForm();
        await this.loadVersions();
      } catch (error) {
        this.showToast(error instanceof Error ? error.message : "版本创建失败");
      } finally {
        this.saving = false;
      }
    },
    async activate(row: AlgorithmVersion) {
      try {
        await api.activateAlgorithmVersion(this.currentAlgorithmId, row.id);
        this.showToast(`版本 ${row.version} 已发布`);
        await this.loadVersions();
      } catch (error) {
        this.showToast(error instanceof Error ? error.message : "版本发布失败");
      }
    }
  }
});
</script>
