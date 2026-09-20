<template>
  <section class="content review-wide">
    <div class="review-titlebar"><div><h1>任务管理</h1><p>异常事件复查、人工补核、离线分析与效果测试</p></div></div>
    <div class="review-board">
      <div class="prototype-filter">
        <div class="review-task-filter-actions"><button class="btn primary" @click="openModal('reviewTask')">上传复核任务</button><button class="btn" @click="applyFilters">查询</button><button class="btn" @click="resetFilters">重置</button></div>
        <div class="filter-item"><span>搜索：</span><input class="input" v-model="keyword" placeholder="搜索任务ID、事件类型" /></div>
        <div class="filter-item"><span>状态：</span><select class="select" v-model="statusFilter"><option value="">全部</option><option>进行中</option><option>已完成</option><option>失败</option></select></div>
        <div class="filter-item"><span>开始时间：</span><input class="input" type="datetime-local" v-model="startTime" aria-label="开始时间" /></div>
        <div class="filter-item"><span>结束时间：</span><input class="input" type="datetime-local" v-model="endTime" aria-label="结束时间" /></div>
      </div>
      <table class="prototype-table">
        <colgroup><col style="width:90px;" /><col style="width:200px;" /><col style="width:170px;" /><col style="width:150px;" /><col style="width:110px;" /><col style="width:110px;" /><col style="width:80px;" /></colgroup>
        <thead><tr><th>任务ID</th><th class="left">事件类型</th><th class="left">大模型</th><th>创建时间</th><th>事件有效</th><th>任务状态</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="row in filteredRows" :key="row.id" class="review-task-row" @click="openModal('reviewTaskDetail', row)">
            <td :title="row.id">{{ row.id.slice(0, 8) }}</td>
            <td class="left">{{ row.reviewTypeName }}（{{ row.reviewTypeCode }}）</td>
            <td class="left">{{ row.llmConfigName }}</td>
            <td>{{ formatTime(row.createdAt) }}</td>
            <td><span class="status-pill" :class="statusClass(row.verdict)">{{ row.verdict || "-" }}</span></td>
            <td><span class="status-pill" :class="statusClass(row.status)">{{ row.status }}</span></td>
            <td><button class="link-red" @click.stop="remove(row)">删除</button></td>
          </tr>
          <tr v-if="!loading && !filteredRows.length"><td colspan="7" class="empty-cell">暂无复核任务</td></tr>
          <tr v-if="loading"><td colspan="7" class="empty-cell">加载中...</td></tr>
        </tbody>
      </table>
      <div class="table-footer"><span>共 {{ filteredRows.length }} 条记录</span></div>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { api } from "../api";
import type { ReviewTask } from "../types";
import { statusClass } from "../utils/prototype-helpers";

export default defineComponent({
  name: "ReviewTasksPage",
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  inject: {
    openModal: { from: "openModal", default: (type: string, item?: any) => {} },
    showToast: { from: "showToast", default: (message: string) => {} },
  },
  data() {
    return {
      rows: [] as ReviewTask[],
      loading: false,
      statusFilter: "",
      keyword: "",
      startTime: "",
      endTime: "",
      pollTimer: null as number | null
    };
  },
  computed: {
    filteredRows(): ReviewTask[] {
      const keyword = this.keyword.trim().toLowerCase();
      // datetime-local 精度到分钟，结束时间按当分 59 秒兜底，避免同分任务被截掉
      const start = this.startTime ? new Date(this.startTime).getTime() : null;
      const end = this.endTime ? new Date(this.endTime).getTime() + 59999 : null;
      return this.rows.filter((row) => {
        if (this.statusFilter && row.status !== this.statusFilter) return false;
        if (start !== null || end !== null) {
          const created = new Date(row.createdAt).getTime();
          if (Number.isNaN(created)) return false;
          if (start !== null && created < start) return false;
          if (end !== null && created > end) return false;
        }
        if (!keyword) return true;
        return [row.id, row.reviewTypeName, row.reviewTypeCode]
          .some((field) => (field || "").toLowerCase().includes(keyword));
      });
    }
  },
  watch: {
    // 上传复核任务提交成功后 App 会自增 reviewTasksVersion，触发列表刷新
    "store.reviewTasksVersion"() {
      this.loadRows();
    }
  },
  mounted() {
    this.loadRows();
  },
  unmounted() {
    this.clearPoll();
  },
  methods: {
    statusClass,
    async loadRows(silent = false) {
      if (!silent) this.loading = true;
      try {
        this.rows = await api.reviewTasks();
      } catch (error) {
        this.showToast(error instanceof Error ? error.message : "复核任务加载失败");
      } finally {
        this.loading = false;
        this.schedulePoll();
      }
    },
    // 存在「进行中」任务时每 5 秒轮询一次，等待大模型研判结果
    schedulePoll() {
      this.clearPoll();
      if (this.rows.some((row) => row.status === "进行中")) {
        this.pollTimer = window.setTimeout(() => {
          this.pollTimer = null;
          this.loadRows(true);
        }, 5000);
      }
    },
    clearPoll() {
      if (this.pollTimer !== null) {
        window.clearTimeout(this.pollTimer);
        this.pollTimer = null;
      }
    },
    applyFilters() {
      // 起止倒置时拦截并提示，与录像回放页保持一致
      if (this.startTime && this.endTime && this.startTime > this.endTime) {
        this.showToast("开始时间必须早于结束时间");
        return;
      }
      this.loadRows();
    },
    resetFilters() {
      this.statusFilter = "";
      this.keyword = "";
      this.startTime = "";
      this.endTime = "";
    },
    formatTime(iso?: string | null): string {
      if (!iso) return "-";
      const date = new Date(iso);
      if (Number.isNaN(date.getTime())) return iso;
      const pad = (n: number) => n.toString().padStart(2, "0");
      return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
    },
    async remove(row: ReviewTask) {
      if (!window.confirm(`确认删除复核任务「${row.reviewTypeName}（${row.id.slice(0, 8)}）」？`)) return;
      try {
        await api.deleteReviewTask(row.id);
        this.showToast("复核任务已删除");
        await this.loadRows();
      } catch (error) {
        this.showToast(error instanceof Error ? error.message : "复核任务删除失败");
      }
    }
  }
});
</script>
