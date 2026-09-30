<template>
  <section class="content review-wide">
    <div class="review-titlebar"><div><h1>大模型配置</h1><p>维护用于事件复核、告警解释与结构化研判的大模型服务</p></div></div>
    <div class="event-config-page-board">
      <div class="event-config-filter"><div class="event-config-filter-left"><button class="btn primary" @click="openCreate">＋ 新增配置</button><button class="btn primary" @click="loadConfigs">查询</button><button class="btn" @click="reset">重置</button><input v-model="keyword" class="input" style="width:260px;" placeholder="请输入名称" /></div></div>
      <div class="table-wrap"><table class="prototype-table"><thead><tr><th class="left">配置ID</th><th class="left">模型名称</th><th class="left">接口地址</th><th>部署方式</th><th>状态</th><th>延迟</th><th>操作</th></tr></thead><tbody><tr v-for="row in paginatedRows" :key="row.id"><td class="left"><code>{{ row.id }}</code></td><td class="left">{{ row.name }}</td><td class="left"><code>{{ row.baseUrl }}</code></td><td>{{ row.deployType === "cloud" ? "云端服务" : "本地部署" }}</td><td><span class="status-pill" :class="statusClass(statusOf(row))">{{ statusOf(row) }}</span></td><td>{{ latencyOf(row) }}</td><td><div class="event-config-actions"><button class="link-blue" :disabled="!!testing[row.id]" @click="test(row)">{{ testing[row.id] ? "检测中..." : "检测" }}</button><button class="link-blue" @click="openEdit(row)">编辑</button><button class="link-blue danger" @click="remove(row)">删除</button></div></td></tr><tr v-if="!loading && !paginatedRows.length"><td colspan="7" class="empty-cell">暂无大模型配置</td></tr><tr v-if="loading"><td colspan="7" class="empty-cell">加载中...</td></tr></tbody></table></div>
      <div class="event-config-pagination"><span style="color:#98a2b3;font-size:11px;margin-right:auto;">共 {{ filteredRows.length }} 条</span><button type="button" aria-label="上一页" :disabled="activePage === 1" @click="activePage--">‹</button><button v-for="page in pageCount" :key="page" type="button" :class="{ active: activePage === page }" @click="activePage = page">{{ page }}</button><button type="button" aria-label="下一页" :disabled="activePage === pageCount" @click="activePage++">›</button><select class="select" v-model.number="pageSize" aria-label="每页条数" @change="activePage = 1"><option :value="10">10条/页</option><option :value="20">20条/页</option><option :value="50">50条/页</option></select></div>
    </div>
    <div v-if="modalOpen" class="event-config-modal-mask" @click.self="closeForm">
      <section class="event-config-modal wide" role="dialog" aria-modal="true" :aria-label="editing ? '编辑配置' : '新增配置'">
        <div class="event-config-modal-head"><h3>{{ editing ? "编辑配置" : "新增配置" }}</h3><button class="event-config-modal-close" aria-label="关闭" @click="closeForm">×</button></div>
        <div class="model-config-section-title">基础配置</div>
        <div class="modal-form-row">
          <label><span class="required">*</span>模型名称：</label>
          <input v-model="form.name" class="input" list="llm-provider-options" placeholder="请选择或输入模型名称" @input="onNameInput" />
          <datalist id="llm-provider-options"><option v-for="provider in llmProviders" :key="provider.name" :value="provider.name"></option></datalist>
        </div>
        <div class="modal-form-row">
          <label><span class="required">*</span>接口地址：</label>
          <input v-model="form.baseUrl" class="input" placeholder="请输入接口地址" />
        </div>
        <div class="modal-form-row">
          <label><span class="required">*</span>API Key：</label>
          <div class="model-api-field">
            <input v-model="form.apiKey" class="input" :type="showApiKey ? 'text' : 'password'" :placeholder="editing && editing.apiKeyConfigured ? '已配置，留空则不修改' : '请输入API Key'" />
            <button class="model-api-toggle" type="button" aria-label="显示或隐藏 API Key" @click="showApiKey = !showApiKey">&#xf06e;</button>
          </div>
        </div>
        <div class="modal-form-row">
          <label>模型标识：</label>
          <select v-if="modelOptions.length" v-model="form.model" class="input">
            <option v-for="option in modelOptionsWithCurrent" :key="option" :value="option">{{ option }}</option>
          </select>
          <input v-else v-model="form.model" class="input" :placeholder="modelsLoading ? '正在查询可用模型...' : '请输入模型标识，如 qwen-vl-max'" />
        </div>
        <p class="model-config-field-note" v-if="modelsLoading">正在根据接口地址和 API Key 查询可用模型...</p>
        <p class="model-config-field-note" v-else-if="modelsError">模型自动查询失败（{{ modelsError }}），可手工输入模型标识</p>
        <p class="model-config-field-note" v-else-if="modelOptions.length">已查询到 {{ modelOptions.length }} 个可用模型，请下拉选择</p>
        <div class="modal-form-row">
          <label><span class="required">*</span>部署方式：</label>
          <div class="model-config-radio-group">
            <label class="model-config-radio"><input type="radio" value="cloud" v-model="form.deployType" />云端部署</label>
            <label class="model-config-radio"><input type="radio" value="local" v-model="form.deployType" />本地部署</label>
          </div>
        </div>
        <div class="model-config-section-title">高级配置</div>
        <div class="modal-form-row">
          <label><span class="required">*</span>超时时间（秒）：</label>
          <input class="input" type="number" min="10" max="120" v-model.number="form.timeout" />
        </div>
        <p class="model-config-field-note">请求的最大等待时间，建议范围：10 - 120s</p>
        <div class="modal-form-row">
          <label><span class="required">*</span>温度参数（Temperature）：</label>
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

// 常用国内大模型供应商预设：选中后自动填入 OpenAI 兼容接口地址
const LLM_PROVIDERS = [
  { name: "DeepSeek", baseUrl: "https://api.deepseek.com/v1" },
  { name: "智谱", baseUrl: "https://open.bigmodel.cn/api/paas/v4" },
  { name: "Kimi", baseUrl: "https://api.moonshot.cn/v1" },
  { name: "阿里百炼", baseUrl: "https://dashscope.aliyuncs.com/compatible-mode/v1" },
  { name: "Minimax", baseUrl: "https://api.minimax.chat/v1" },
  { name: "百度千帆", baseUrl: "https://qianfan.baidubce.com/v2" },
  { name: "SiliconFlow", baseUrl: "https://api.siliconflow.cn/v1" }
];

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
      modelOptions: [] as string[],
      modelsLoading: false,
      modelsError: "",
      modelsQuerySeq: 0,
      modelsDebounce: null as number | null,
      llmProviders: LLM_PROVIDERS,
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
    },
    // 当前已保存的模型标识若不在新查询结果中，保留为首选项避免丢失
    modelOptionsWithCurrent(): string[] {
      const current = this.form.model.trim();
      return current && !this.modelOptions.includes(current) ? [current, ...this.modelOptions] : this.modelOptions;
    }
  },
  watch: {
    "form.baseUrl"() {
      this.scheduleModelsQuery();
    },
    "form.apiKey"() {
      this.scheduleModelsQuery();
    }
  },
  mounted() {
    // 每次打开页面：先加载配置列表，再异步静默检测每个模型的状态并更新状态列
    this.autoCheckAll();
  },
  methods: {
    statusClass,
    // 名称与某个供应商预设完全匹配时，自动带入其接口地址（baseUrl 的 watch 会触发模型查询）
    onNameInput() {
      const name = this.form.name.trim();
      const provider = this.llmProviders.find(item => item.name === name);
      if (provider && this.form.baseUrl !== provider.baseUrl) this.form.baseUrl = provider.baseUrl;
    },
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
    openCreate() { this.editing = null; this.form = this.blankForm(); this.showApiKey = false; this.resetModelsQuery(); this.modalOpen = true; },
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
      this.resetModelsQuery();
      this.modalOpen = true;
      // 编辑时 API Key 留空（复用已存密钥），打开弹窗即自动查询可用模型
      this.scheduleModelsQuery();
    },
    resetModelsQuery() {
      this.modelsQuerySeq++;
      if (this.modelsDebounce !== null) {
        window.clearTimeout(this.modelsDebounce);
        this.modelsDebounce = null;
      }
      this.modelOptions = [];
      this.modelsLoading = false;
      this.modelsError = "";
    },
    // 接口地址与 API Key 填好后防抖自动查询可用模型
    scheduleModelsQuery() {
      if (!this.modalOpen) return;
      if (this.modelsDebounce !== null) window.clearTimeout(this.modelsDebounce);
      this.modelsDebounce = window.setTimeout(() => {
        this.modelsDebounce = null;
        this.queryModels();
      }, 600);
    },
    async queryModels() {
      const baseUrl = this.form.baseUrl.trim();
      const apiKey = this.form.apiKey.trim();
      if (!baseUrl || (!apiKey && !this.editing?.apiKeyConfigured)) {
        this.modelOptions = [];
        this.modelsError = "";
        return;
      }
      const seq = ++this.modelsQuerySeq;
      this.modelsLoading = true;
      this.modelsError = "";
      try {
        const result = await api.llmModels({
          baseUrl,
          ...(apiKey ? { apiKey } : {}),
          ...(this.editing ? { configId: this.editing.id } : {})
        });
        if (seq !== this.modelsQuerySeq) return;
        if (result.ok) {
          this.modelOptions = result.models;
          // 当前未选模型时默认选中第一个可用模型
          if (!this.form.model.trim() && result.models.length) this.form.model = result.models[0];
        } else {
          this.modelOptions = [];
          this.modelsError = result.error || "模型查询失败";
        }
      } catch (error) {
        if (seq !== this.modelsQuerySeq) return;
        this.modelOptions = [];
        this.modelsError = error instanceof Error ? error.message : "模型查询失败";
      } finally {
        if (seq === this.modelsQuerySeq) this.modelsLoading = false;
      }
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
    // 页面打开时静默检测全部模型，不弹 Toast；检测中按钮显示"检测中..."
    async autoCheckAll() {
      await this.loadConfigs();
      await Promise.allSettled(this.rows.map(row => this.runTest(row, true)));
    },
    async runTest(row: LlmConfig, quiet: boolean) {
      if (this.testing[row.id]) return;
      this.testing = { ...this.testing, [row.id]: true };
      try {
        const result = await api.testLlmConfig(row.id);
        const latency = result.latencyMs != null ? `${result.latencyMs}ms` : "-";
        this.checks = {
          ...this.checks,
          [row.id]: { status: result.ok ? "在线" : "连接异常", latency: result.ok ? latency : "-" }
        };
        if (quiet) return;
        if (result.ok) {
          this.showToast(`${row.name} 连接正常，延迟 ${latency}`);
        } else {
          this.showToast(`${row.name} 连接异常：${result.error || `HTTP ${result.statusCode ?? "未知"}`}`);
        }
      } catch (error) {
        this.checks = { ...this.checks, [row.id]: { status: "连接异常", latency: "-" } };
        if (!quiet) this.showToast(error instanceof Error ? error.message : `${row.name} 检测失败`);
      } finally {
        this.testing = { ...this.testing, [row.id]: false };
      }
    },
    async test(row: LlmConfig) {
      await this.runTest(row, false);
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
