<template>
  <section class="content review-wide">
    <div class="review-titlebar"><div><h1>大模型配置</h1><p>维护用于事件复核、告警解释与结构化研判的大模型服务</p></div></div>
    <div class="event-config-page-board">
      <div class="event-config-filter"><div class="event-config-filter-left"><button class="btn primary" @click="openCreate">＋ 新增配置</button><button class="btn primary" @click="loadConfigs">查询</button><button class="btn" @click="reset">重置</button><input v-model="keyword" class="input" style="width:260px;" placeholder="请输入名称" /></div></div>
      <div class="table-wrap"><table class="prototype-table"><thead><tr><th class="left">模型名称</th><th class="left">接口地址</th><th>部署方式</th><th>状态</th><th>延迟</th><th>操作</th></tr></thead><tbody><tr v-for="row in paginatedRows" :key="row.id"><td class="left">{{ row.name }}</td><td class="left"><code>{{ row.baseUrl }}</code></td><td>{{ row.deployType === "cloud" ? "云端服务" : "本地部署" }}</td><td><span class="status-pill" :class="statusClass(statusOf(row))">{{ statusOf(row) }}</span></td><td>{{ latencyOf(row) }}</td><td><div class="event-config-actions"><button class="link-blue" :disabled="!!testing[row.id]" @click="test(row)">{{ testing[row.id] ? "检测中..." : "检测" }}</button><button class="link-blue" @click="openEdit(row)">编辑</button><button class="link-blue danger" @click="remove(row)">删除</button></div></td></tr><tr v-if="!loading && !paginatedRows.length"><td colspan="6" class="empty-cell">暂无大模型配置</td></tr><tr v-if="loading"><td colspan="6" class="empty-cell">加载中...</td></tr></tbody></table></div>
      <div class="event-config-pagination"><span style="color:#98a2b3;font-size:11px;margin-right:auto;">共 {{ filteredRows.length }} 条</span><button type="button" aria-label="上一页" :disabled="activePage === 1" @click="activePage--">‹</button><button v-for="page in pageCount" :key="page" type="button" :class="{ active: activePage === page }" @click="activePage = page">{{ page }}</button><button type="button" aria-label="下一页" :disabled="activePage === pageCount" @click="activePage++">›</button><select class="select" v-model.number="pageSize" aria-label="每页条数" @change="activePage = 1"><option :value="10">10条/页</option><option :value="20">20条/页</option><option :value="50">50条/页</option></select></div>
    </div>
    <div v-if="modalOpen" class="event-config-modal-mask" @click.self="closeForm">
      <section class="event-config-modal wide" role="dialog" aria-modal="true" :aria-label="editing ? '编辑配置' : '新增配置'">
        <div class="event-config-modal-head"><h3>{{ editing ? "编辑配置" : "新增配置" }}</h3><button class="event-config-modal-close" aria-label="关闭" @click="closeForm">×</button></div>
        <div class="model-config-section-title">基础配置</div>
        <div class="modal-form-row">
          <label><span class="required">*</span>模型名称：</label>
          <input v-model="form.name" class="input" placeholder="请输入模型名称" />
        </div>
        <div class="modal-form-row">
          <label><span class="required">*</span>接口地址：</label>
          <input v-model="form.baseUrl" class="input" placeholder="请输入接口地址" />
        </div>
        <div class="modal-form-row">
          <label>模型标识：</label>
          <input v-model="form.model" class="input" placeholder="请输入模型标识，如 qwen-vl-max" />
        </div>
        <div class="modal-form-row">
          <label><span class="required">*</span>API Key：</label>
          <div class="model-api-field">
            <input v-model="form.apiKey" class="input" :type="showApiKey ? 'text' : 'password'" :placeholder="editing && editing.apiKeyConfigured ? '已配置，留空则不修改' : '请输入API Key'" />
            <button class="model-api-toggle" type="button" aria-label="显示或隐藏 API Key" @click="showApiKey = !showApiKey">&#xf06e;</button>
          </div>
        </div>
        <div class="modal-form-row">
          <label><span class="required">*</span>部署方式：</label>
          <div class="model-config-radio-group">
            <label class="model-config-radio"><input type="radio" value="cloud" v-model="form.deployType" />云端部署</label>
            <label class="model-config-radio"><input type="radio" value="local" v-model="form.deployType" />本地部署</label>
          </div>
        </div>
        <div class="model-config-section-title">高级配置</div>
        <div class="modal-form-row">
          <label>超时时间（秒）：</label>
          <input class="input" type="number" min="10" max="120" v-model.number="form.timeout" />
        </div>
        <p class="model-config-field-note">请求的最大等待时间，建议范围：10 - 120s</p>
        <div class="modal-form-row">
          <label>温度参数（Temperature）：</label>
          <div class="model-config-range">
            <input type="range" min="0" max="1" step="0.1" v-model.number="form.temperature" />
            <output>{{ form.temperature }}</output>
          </div>
        </div>
        <p class="model-config-field-note">控制输出的随机性：0 表示最稳定，1 表示最富创造力</p>
        <div class="modal-form-row">
          <label>最大输出长度（Tokens）：</label>
          <input class="input" type="number" min="1" v-model.number="form.maxTokens" />
        </div>
        <p class="model-config-field-note">模型生成的最大 Token 数量</p>
        <div class="modal-form-row">
          <label>视频帧数（FPS）：</label>
          <input class="input" type="number" min="1" v-model.number="form.fps" />
        </div>
        <p class="model-config-field-note">视频理解任务中的采样帧率</p>
        <div class="event-config-modal-actions"><button class="btn" @click="closeForm">取消</button><button class="btn primary" :disabled="saving" @click="save">保存</button></div>
      </section>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { api } from "../api";
import type { LlmConfig, LlmConfigPayload } from "../types";
import { statusClass } from "../utils/prototype-helpers";

type RowCheck = { status: string; latency: string };

export default defineComponent({
  name: "ModelConfigPage",
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  inject: {
    showToast: { from: "showToast", default: (message: string) => {} },
  },
  data() {
    return {
      keyword: "",
      activePage: 1,
      pageSize: 10,
      rows: [] as LlmConfig[],
      checks: {} as Record<string, RowCheck>,
      testing: {} as Record<string, boolean>,
      loading: false,
      saving: false,
      modalOpen: false,
      editing: null as LlmConfig | null,
      showApiKey: false,
      form: {
        name: "",
        baseUrl: "",
        model: "",
        apiKey: "",
        deployType: "cloud" as "cloud" | "local",
        timeout: 30,
        temperature: 0.7,
        maxTokens: 2048,
        fps: 1
      }
    };
  },
  computed: {
    filteredRows(): LlmConfig[] {
      const value = this.keyword.trim().toLowerCase();
      return value ? this.rows.filter(row => `${row.name}${row.baseUrl}`.toLowerCase().includes(value)) : this.rows;
    },
    pageCount(): number {
      return Math.max(1, Math.ceil(this.filteredRows.length / this.pageSize));
    },
    paginatedRows(): LlmConfig[] {
      const start = (this.activePage - 1) * this.pageSize;
      return this.filteredRows.slice(start, start + this.pageSize);
    }
  },
  mounted() {
    this.loadConfigs();
  },
  methods: {
    statusClass,
    statusOf(row: LlmConfig): string {
      return this.checks[row.id]?.status || "未检测";
    },
    latencyOf(row: LlmConfig): string {
      return this.checks[row.id]?.latency || "-";
    },
    reset() { this.keyword = ""; this.activePage = 1; },
    async loadConfigs() {
      if (this.loading) return;
      this.loading = true;
      try {
        this.rows = await api.llmConfigs();
      } catch (error) {
        this.showToast(error instanceof Error ? error.message : "大模型配置加载失败");
      } finally {
        this.loading = false;
      }
    },
    blankForm() {
      return { name: "", baseUrl: "", model: "", apiKey: "", deployType: "cloud" as "cloud" | "local", timeout: 30, temperature: 0.7, maxTokens: 2048, fps: 1 };
    },
    openCreate() { this.editing = null; this.form = this.blankForm(); this.showApiKey = false; this.modalOpen = true; },
    openEdit(row: LlmConfig) {
      this.editing = row;
      this.form = {
        name: row.name,
        baseUrl: row.baseUrl,
        model: row.model,
        apiKey: "",
        deployType: row.deployType,
        timeout: row.timeout,
        temperature: row.temperature,
        maxTokens: row.maxTokens,
        fps: row.fps
      };
      this.showApiKey = false;
      this.modalOpen = true;
    },
    closeForm() { this.modalOpen = false; },
    async save() {
      const payload: LlmConfigPayload = {
        name: this.form.name.trim(),
        baseUrl: this.form.baseUrl.trim(),
        model: this.form.model.trim(),
        deployType: this.form.deployType,
        timeout: this.form.timeout,
        temperature: this.form.temperature,
        maxTokens: this.form.maxTokens,
        fps: this.form.fps
      };
      const apiKey = this.form.apiKey.trim();
      if (apiKey) payload.apiKey = apiKey;
      if (!payload.name || !payload.baseUrl) {
        this.showToast("请填写模型名称和接口地址");
        return;
      }
      if (!this.editing && !apiKey) {
        this.showToast("请输入 API Key");
        return;
      }
      if (!(payload.timeout >= 10 && payload.timeout <= 120)) {
        this.showToast("超时时间需在 10 - 120 秒之间");
        return;
      }
      if (!(payload.temperature >= 0 && payload.temperature <= 1)) {
        this.showToast("Temperature 需在 0 - 1 之间");
        return;
      }
      if (this.saving) return;
      this.saving = true;
      try {
        if (this.editing) {
          await api.updateLlmConfig(this.editing.id, payload);
          this.showToast(`大模型配置已更新：${payload.name}`);
        } else {
          await api.createLlmConfig(payload);
          this.showToast(`大模型配置已保存：${payload.name}`);
        }
        this.closeForm();
        await this.loadConfigs();
      } catch (error) {
        this.showToast(error instanceof Error ? error.message : "大模型配置保存失败");
      } finally {
        this.saving = false;
      }
    },
    async test(row: LlmConfig) {
      if (this.testing[row.id]) return;
      this.testing = { ...this.testing, [row.id]: true };
      try {
        const result = await api.testLlmConfig(row.id);
        const latency = result.latencyMs != null ? `${result.latencyMs}ms` : "-";
        this.checks = {
          ...this.checks,
          [row.id]: { status: result.ok ? "在线" : "连接异常", latency: result.ok ? latency : "-" }
        };
        if (result.ok) {
          this.showToast(`${row.name} 连接正常，延迟 ${latency}`);
        } else {
          this.showToast(`${row.name} 连接异常：${result.error || `HTTP ${result.statusCode ?? "未知"}`}`);
        }
      } catch (error) {
        this.checks = { ...this.checks, [row.id]: { status: "连接异常", latency: "-" } };
        this.showToast(error instanceof Error ? error.message : `${row.name} 检测失败`);
      } finally {
        this.testing = { ...this.testing, [row.id]: false };
      }
    },
    async remove(row: LlmConfig) {
      if (!window.confirm(`确认删除大模型配置「${row.name}」？`)) return;
      try {
        await api.deleteLlmConfig(row.id);
        this.showToast(`已删除大模型配置：${row.name}`);
        if (this.activePage > 1 && this.paginatedRows.length === 1) this.activePage--;
        await this.loadConfigs();
      } catch (error) {
        this.showToast(error instanceof Error ? error.message : "大模型配置删除失败");
      }
    }
  }
});
</script>
