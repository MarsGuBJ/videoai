<template>
  <section :class="embedded ? 'event-config-tab-pane' : 'content review-wide'">
    <div v-if="!embedded" class="review-titlebar"><div><h1>定时任务管理</h1><p>维护按 cron 表达式定时执行的复核任务</p></div></div>
    <div class="review-board">
      <div class="algorithm-toolbar"><button class="btn primary" @click="openCreate">新建</button></div>
      <table class="prototype-table">
        <colgroup><col style="width:48px;" /><col style="width:180px;" /><col style="width:200px;" /><col style="width:150px;" /><col style="width:90px;" /><col style="width:80px;" /><col style="width:150px;" /><col /><col style="width:230px;" /></colgroup>
        <thead><tr><th>ID</th><th class="left">任务名称</th><th class="left">复核类型</th><th class="left">cron 表达式</th><th>每批条数</th><th>状态</th><th>上次执行时间</th><th class="left">上次执行结果</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="row in rows" :key="row.id">
            <td :title="row.id">{{ row.id.slice(0, 8) }}</td><td class="left">{{ row.name }}</td><td class="left">{{ row.reviewTypeName }}（{{ row.reviewTypeCode }}）</td><td class="left">{{ row.cron }}</td><td>{{ row.batchSize }}</td><td><span class="mini-tag">{{ row.enabled ? "启用" : "停用" }}</span></td><td>{{ formatTime(row.lastRunAt) }}</td><td class="left ellipsis">{{ row.lastResult || "-" }}</td>
            <td><button class="link-blue" @click="openEdit(row)">编辑</button><button class="link-blue" @click="toggle(row)">{{ row.enabled ? "停用" : "启用" }}</button><button class="link-blue" @click="runNow(row)">立即执行</button><button class="link-red" @click="remove(row)">删除</button></td>
          </tr>
          <tr v-if="!loading && !rows.length"><td colspan="9" class="empty-cell">暂无定时任务</td></tr>
          <tr v-if="loading"><td colspan="9" class="empty-cell">加载中...</td></tr>
        </tbody>
      </table>
    </div>
    <div v-if="modalOpen" class="event-config-modal-mask" @click.self="closeForm">
      <section class="event-config-modal wide" role="dialog" aria-modal="true" :aria-label="editing ? '编辑定时任务' : '新增定时任务'">
        <div class="event-config-modal-head"><h3>{{ editing ? "编辑定时任务" : "新增定时任务" }}</h3><button class="event-config-modal-close" aria-label="关闭" @click="closeForm">×</button></div>
        <div class="event-config-form-grid">
          <label class="event-config-field wide"><span>* 任务名称</span><input v-model="form.name" class="input" placeholder="请输入任务名称" /></label>
          <label class="event-config-field wide"><span>* 复核类型</span><select v-model="form.reviewTypeId" class="select"><option value="">请选择复核类型</option><option v-for="row in reviewTypeOptions" :key="row.id" :value="row.id">{{ row.name }}（{{ row.code }}）</option></select></label>
          <label class="event-config-field"><span>* cron 表达式</span><input v-model="form.cron" class="input" placeholder="*/30 * * * *" /></label>
          <label class="event-config-field"><span>每批处理条数</span><input v-model.number="form.batchSize" type="number" min="1" class="input" /></label>
          <label class="event-config-field"><span>启用</span><span style="display:flex;align-items:center;gap:6px;"><input v-model="form.enabled" type="checkbox" /> 启用该任务</span></label>
        </div>
        <div class="event-config-modal-actions"><button class="btn" @click="closeForm">取消</button><button class="btn primary" :disabled="saving" @click="save">保存</button></div>
      </section>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { api } from "../api";
import type { ReviewSchedule, ReviewType } from "../types";

export default defineComponent({
  name: "ReviewSchedulesPage",
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm", "embedded"],
  inject: {
    showToast: { from: "showToast", default: (message: string) => {} },
  },
  data() {
    return {
      rows: [] as ReviewSchedule[],
      reviewTypeOptions: [] as ReviewType[],
      loading: false,
      saving: false,
      modalOpen: false,
      editing: null as ReviewSchedule | null,
      form: { name: "", reviewTypeId: "", cron: "", enabled: true, batchSize: 50 }
    };
  },
  mounted() {
    this.loadData();
  },
  methods: {
    async loadData() {
      if (this.loading) return;
      this.loading = true;
      try {
        const [rows, reviewTypes] = await Promise.all([api.reviewSchedules(), api.reviewTypes()]);
        this.rows = rows;
        this.reviewTypeOptions = reviewTypes;
      } catch (error) {
        this.showToast(error instanceof Error ? error.message : "定时任务加载失败");
      } finally {
        this.loading = false;
      }
    },
    async loadRows() {
      try {
        this.rows = await api.reviewSchedules();
      } catch (error) {
        this.showToast(error instanceof Error ? error.message : "定时任务加载失败");
      }
    },
    formatTime(iso?: string | null): string {
      if (!iso) return "-";
      const date = new Date(iso);
      if (Number.isNaN(date.getTime())) return iso;
      const pad = (n: number) => n.toString().padStart(2, "0");
      return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
    },
    openCreate() {
      this.editing = null;
      this.form = { name: "", reviewTypeId: "", cron: "", enabled: true, batchSize: 50 };
      this.modalOpen = true;
    },
    openEdit(row: ReviewSchedule) {
      this.editing = row;
      this.form = { name: row.name, reviewTypeId: row.reviewTypeId, cron: row.cron, enabled: row.enabled, batchSize: row.batchSize };
      this.modalOpen = true;
    },
    closeForm() { this.modalOpen = false; },
    async save() {
      if (!this.form.name.trim()) { this.showToast("请填写任务名称"); return; }
      if (!this.form.reviewTypeId) { this.showToast("请选择复核类型"); return; }
      if (!this.form.cron.trim()) { this.showToast("请填写 cron 表达式"); return; }
      if (this.saving) return;
      this.saving = true;
      try {
        const payload = {
          name: this.form.name.trim(),
          reviewTypeId: this.form.reviewTypeId,
          cron: this.form.cron.trim(),
          enabled: this.form.enabled,
          batchSize: this.form.batchSize > 0 ? this.form.batchSize : 50
        };
        if (this.editing) {
          await api.updateReviewSchedule(this.editing.id, payload);
        } else {
          await api.createReviewSchedule(payload);
        }
        this.showToast("定时任务已保存");
        this.closeForm();
        await this.loadRows();
      } catch (error) {
        this.showToast(error instanceof Error ? error.message : "定时任务保存失败");
      } finally {
        this.saving = false;
      }
    },
    async toggle(row: ReviewSchedule) {
      try {
        await api.updateReviewSchedule(row.id, {
          name: row.name,
          reviewTypeId: row.reviewTypeId,
          cron: row.cron,
          enabled: !row.enabled,
          batchSize: row.batchSize
        });
        this.showToast(row.enabled ? "已停用任务" : "已启用任务");
        await this.loadRows();
      } catch (error) {
        this.showToast(error instanceof Error ? error.message : "定时任务更新失败");
      }
    },
    async runNow(row: ReviewSchedule) {
      try {
        await api.runReviewSchedule(row.id);
        this.showToast(`已触发执行：${row.name}`);
        window.setTimeout(() => { this.loadRows(); }, 2000);
      } catch (error) {
        this.showToast(error instanceof Error ? error.message : "触发执行失败");
      }
    },
    async remove(row: ReviewSchedule) {
      if (!window.confirm(`确认删除定时任务「${row.name}」？`)) return;
      try {
        await api.deleteReviewSchedule(row.id);
        this.showToast(`已删除定时任务：${row.name}`);
        await this.loadRows();
      } catch (error) {
        this.showToast(error instanceof Error ? error.message : "定时任务删除失败");
      }
    }
  }
});
</script>
