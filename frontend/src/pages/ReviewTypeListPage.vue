<template>
  <section :class="embedded ? 'event-config-tab-pane' : 'content review-wide'">
    <div v-if="!embedded" class="review-titlebar"><div><h1>复核类型管理</h1><p>维护用于人工复核和大模型判断的算法类型</p></div></div>
    <div class="review-board">
      <div class="algorithm-toolbar"><button class="btn primary" @click="openCreate">新建</button></div>
      <table class="prototype-table">
        <colgroup><col style="width:auto;" /><col style="width:170px;" /><col style="width:210px;" /><col /><col style="width:110px;" /><col style="width:125px;" /><col style="width:150px;" /><col style="width:100px;" /></colgroup>
        <thead><tr><th>ID</th><th class="left">事件名称</th><th class="left">算法编码</th><th class="left">提示词</th><th class="left">备注</th><th>注入事件字段</th><th>更新时间</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="row in rows" :key="row.id">
            <td :title="row.id" style="white-space:nowrap;">{{ row.id }}</td><td class="left">{{ row.name }}</td><td class="left">{{ row.code }}</td><td class="left ellipsis">{{ row.prompt }}</td><td class="left ellipsis">{{ row.remark }}</td><td><span v-if="row.injectEvent" class="mini-tag">{{ row.injectEvent }}</span><span v-else>-</span></td><td>{{ formatTime(row.updatedAt) }}</td>
            <td><button class="link-blue" @click="openEdit(row)">编辑</button><button class="link-red" @click="remove(row)">删除</button></td>
          </tr>
          <tr v-if="!loading && !rows.length"><td colspan="8" class="empty-cell">暂无复核类型</td></tr>
          <tr v-if="loading"><td colspan="8" class="empty-cell">加载中...</td></tr>
        </tbody>
      </table>
    </div>
    <div v-if="modalOpen" class="event-config-modal-mask" @click.self="closeForm">
      <section class="event-config-modal wide" role="dialog" aria-modal="true" :aria-label="editing ? '编辑复核类型' : '新增复核类型'">
        <div class="event-config-modal-head"><h3>{{ editing ? "编辑复核类型" : "新增复核类型" }}</h3><button class="event-config-modal-close" aria-label="关闭" @click="closeForm">×</button></div>
        <div class="event-config-form-grid">
          <label class="event-config-field"><span>* 事件名称</span><select v-model="form.code" class="select"><option value="">请选择事件名称</option><option v-for="row in algorithmOptions" :key="row.id" :value="row.code">{{ row.name }}（{{ row.code }}）</option></select><span v-if="selectedEventInfo" class="hint-text">事件来源：{{ selectedEventInfo.source || "-" }}</span></label>
          <div class="event-config-field"><span>算法编码</span><input class="input" :value="form.code" disabled placeholder="选择事件名称后自动填充" /></div>
          <label class="event-config-field wide"><span>大模型</span><select v-model="form.llmConfigId" class="select"><option value="">请选择大模型</option><option v-for="item in llmOptions" :key="item.id" :value="item.id">{{ item.name }}</option></select></label>
          <label class="event-config-field wide"><span>* 提示词</span><textarea v-model="form.prompt" class="textarea" style="height:220px;" placeholder="你是园区安防监控事件复检助手，请根据图片或视频片段判断是否存在目标事件，并输出结构化判断结果。"></textarea></label>
          <label class="event-config-field wide"><span>注入事件</span><input v-model="form.injectEvent" class="input" placeholder="请输入注入事件字段" /></label>
          <label class="event-config-field wide"><span>备注</span><textarea v-model="form.remark" class="textarea" style="height:64px;" placeholder="请输入备注"></textarea></label>
        </div>
        <div class="event-config-modal-actions"><button class="btn" @click="closeForm">取消</button><button class="btn primary" :disabled="saving" @click="save">保存</button></div>
      </section>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { api } from "../api";
import type { EventInfo, LlmConfig, ReviewType } from "../types";

export default defineComponent({
  name: "ReviewTypeListPage",
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm", "embedded"],
  inject: {
    showToast: { from: "showToast", default: (message: string) => {} },
  },
  data() {
    return {
      rows: [] as ReviewType[],
      eventInfos: [] as EventInfo[],
      llmConfigs: [] as LlmConfig[],
      loading: false,
      saving: false,
      modalOpen: false,
      editing: null as ReviewType | null,
      form: { code: "", prompt: "", injectEvent: "", remark: "", llmConfigId: "" }
    };
  },
  computed: {
    algorithmOptions(): { id: string; code: string; name: string }[] {
      const options = this.eventInfos.map(row => ({ id: row.id, code: row.code, name: row.name }));
      if (this.editing && !options.some(row => row.code === this.editing!.code)) {
        options.unshift({ id: this.editing.id, code: this.editing.code, name: this.editing.name });
      }
      return options;
    },
    selectedEventInfo(): EventInfo | null {
      if (!this.form.code) return null;
      return this.eventInfos.find(row => row.code === this.form.code) || null;
    },
    llmOptions(): { id: string; name: string }[] {
      const options = this.llmConfigs.map(item => ({
        id: item.id,
        name: `${item.name}（${item.deployType === "local" ? "本地" : "云端"}）`
      }));
      const current = this.editing && this.editing.llmConfigId;
      if (current && !options.some(item => item.id === current)) {
        options.unshift({ id: current, name: "已删除的大模型配置" });
      }
      return options;
    }
  },
  mounted() {
    this.loadData();
  },
  methods: {
    async loadData() {
      if (this.loading) return;
      this.loading = true;
      try {
        const [rows, eventInfos, llmConfigs] = await Promise.all([api.reviewTypes(), api.eventInfos(), api.llmConfigs()]);
        this.rows = rows;
        this.eventInfos = eventInfos;
        this.llmConfigs = llmConfigs;
      } catch (error) {
        this.showToast(error instanceof Error ? error.message : "复核类型加载失败");
      } finally {
        this.loading = false;
      }
    },
    async loadRows() {
      try {
        this.rows = await api.reviewTypes();
      } catch (error) {
        this.showToast(error instanceof Error ? error.message : "复核类型加载失败");
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
      this.form = { code: "", prompt: "", injectEvent: "", remark: "", llmConfigId: "" };
      this.modalOpen = true;
    },
    openEdit(row: ReviewType) {
      this.editing = row;
      this.form = { code: row.code, prompt: row.prompt, injectEvent: row.injectEvent, remark: row.remark, llmConfigId: row.llmConfigId || "" };
      this.modalOpen = true;
    },
    closeForm() { this.modalOpen = false; },
    async save() {
      const selected = this.algorithmOptions.find(row => row.code === this.form.code);
      if (!selected) { this.showToast("请选择事件名称"); return; }
      if (!this.form.prompt.trim()) { this.showToast("请填写提示词"); return; }
      if (this.saving) return;
      this.saving = true;
      try {
        const payload = {
          name: selected.name,
          code: selected.code,
          prompt: this.form.prompt.trim(),
          injectEvent: this.form.injectEvent.trim(),
          remark: this.form.remark.trim(),
          llmConfigId: this.form.llmConfigId
        };
        if (this.editing) {
          await api.updateReviewType(this.editing.id, payload);
        } else {
          await api.createReviewType(payload);
        }
        this.showToast("复核类型配置已保存");
        this.closeForm();
        await this.loadRows();
      } catch (error) {
        this.showToast(error instanceof Error ? error.message : "复核类型保存失败");
      } finally {
        this.saving = false;
      }
    },
    async remove(row: ReviewType) {
      if (!window.confirm(`确认删除复核类型「${row.name}」？`)) return;
      try {
        await api.deleteReviewType(row.id);
        this.showToast(`已删除复核类型：${row.name}`);
        await this.loadRows();
      } catch (error) {
        this.showToast(error instanceof Error ? error.message : "复核类型删除失败");
      }
    }
  }
});
</script>
