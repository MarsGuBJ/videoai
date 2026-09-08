<script lang="ts">
import { defineComponent } from "vue";
import SummaryCards from "../components/SummaryCards.vue";
import { api } from "../api";
import type { Algorithm } from "../types";

function formatTime(iso?: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const pad = (n: number) => n.toString().padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export default defineComponent({
  name: "AlgorithmsPage",
  components: { SummaryCards },
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  // Aliased injection + same-named method wrappers (see ImageResults.vue note);
  // matches the prototype's `inject: ["openModal", "openVersionManager", "showToast"]`.
  inject: {
    openModalImpl: { from: "openModal" },
    openVersionManagerImpl: { from: "openVersionManager" },
    showToastImpl: { from: "showToast" }
  },
  data() {
    return {
      rows: [] as Algorithm[],
      loading: false,
      keyword: "",
      statusFilter: "",
      sceneFilter: ""
    };
  },
  computed: {
    filteredRows(): Algorithm[] {
      const keyword = this.keyword.trim().toLowerCase();
      return this.rows.filter((row) => {
        if (keyword && !`${row.name}${row.code}`.toLowerCase().includes(keyword)) return false;
        if (this.statusFilter && row.status !== this.statusFilter) return false;
        if (this.sceneFilter && (row.scene || "") !== this.sceneFilter) return false;
        return true;
      });
    },
    sceneOptions(): string[] {
      return Array.from(new Set(this.rows.map((row) => row.scene || "").filter(Boolean)));
    },
    cards(): any[] {
      return [
        { label: "算法总数", value: this.rows.length },
        { label: "运行中", value: this.rows.filter((row) => row.status === "RUNNING").length },
        { label: "缺模型", value: this.rows.filter((row) => row.currentVersionStatus === "MISSING_FILES").length },
        { label: "已停用", value: this.rows.filter((row) => row.status === "DISABLED").length }
      ];
    }
  },
  mounted() {
    this.loadAlgorithms();
  },
  methods: {
    openModal(key: string, item?: any) {
      (this as any).openModalImpl(key, item);
    },
    openVersionManager(row: Algorithm) {
      (this as any).openVersionManagerImpl(row);
    },
    showToast(m: string) {
      (this as any).showToastImpl(m);
    },
    formatTime,
    statusText(row: Algorithm): string {
      return row.status === "RUNNING" ? "运行中" : "已停用";
    },
    resetFilters() {
      this.keyword = "";
      this.statusFilter = "";
      this.sceneFilter = "";
    },
    async loadAlgorithms() {
      if (this.loading) return;
      this.loading = true;
      try {
        this.rows = await api.algorithms();
      } catch (error) {
        this.showToast(error instanceof Error ? error.message : "算法列表加载失败");
      } finally {
        this.loading = false;
      }
    },
    async toggleStatus(row: Algorithm) {
      const status = row.status === "RUNNING" ? "DISABLED" : "RUNNING";
      try {
        await api.updateAlgorithm(row.id, { status });
        this.showToast(status === "RUNNING" ? `算法「${row.name}」已启用` : `算法「${row.name}」已停用`);
        await this.loadAlgorithms();
      } catch (error) {
        this.showToast(error instanceof Error ? error.message : "算法状态切换失败");
      }
    }
  }
});
</script>

<template>
  <section class="content review-wide">
    <div class="review-titlebar"><div><h1>算法管理</h1><p>维护算法基础信息、运行状态与当前版本</p></div></div>
    <summary-cards :cards="cards"></summary-cards>
    <div class="review-board">
      <div class="page-actions">
        <div class="left"><button class="btn primary" @click="openModal('algorithm')">新增算法</button><button class="btn" @click="loadAlgorithms">查询</button><button class="btn" @click="resetFilters">重置</button><input class="input" style="width:260px;" v-model="keyword" placeholder="搜索算法名称、算法编码" /><select class="select" style="width:150px;" v-model="statusFilter"><option value="">全部状态</option><option value="RUNNING">运行中</option><option value="DISABLED">已停用</option></select><select class="select" style="width:170px;" v-model="sceneFilter"><option value="">全部场景</option><option v-for="scene in sceneOptions" :key="scene" :value="scene">{{ scene }}</option></select></div>
      </div>
      <table class="prototype-table">
        <colgroup><col style="width:110px;" /><col style="width:150px;" /><col style="width:165px;" /><col style="width:120px;" /><col style="width:80px;" /><col style="width:110px;" /><col style="width:80px;" /><col style="width:150px;" /><col style="width:170px;" /></colgroup>
        <thead><tr><th>算法ID</th><th class="left">算法名称</th><th class="left">算法编码</th><th>应用场景</th><th>当前版本</th><th>状态</th><th>创建人</th><th>更新时间</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="row in filteredRows" :key="row.id">
            <td class="ellipsis" :title="row.id">{{ row.id }}</td><td class="left">{{ row.name }}</td><td class="left">{{ row.code }}</td><td>{{ row.scene || "—" }}</td><td><button v-if="row.currentVersion" class="link-blue" @click="openVersionManager(row)">{{ row.currentVersion }}</button><span v-else>—</span></td>
            <td>
              <span class="status-pill" :class="statusClass(statusText(row))">{{ statusText(row) }}</span>
              <span v-if="row.currentVersionStatus === 'MISSING_FILES'" class="status-pill waiting" :title="'缺失文件：' + (row.missingFiles || []).join('、')">缺模型文件</span>
            </td>
            <td>{{ row.owner || "—" }}</td><td>{{ formatTime(row.updatedAt) }}</td>
            <td><button class="link-blue" @click="openVersionManager(row)">版本号</button><button class="link-blue" @click="openModal('algorithm', row)">编辑</button><button class="link-red" @click="toggleStatus(row)">{{ row.status === "RUNNING" ? "停用" : "启用" }}</button></td>
          </tr>
          <tr v-if="!loading && !filteredRows.length"><td colspan="9" class="empty-cell">暂无算法</td></tr>
          <tr v-if="loading"><td colspan="9" class="empty-cell">加载中...</td></tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
