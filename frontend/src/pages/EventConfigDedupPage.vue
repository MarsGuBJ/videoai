<template>
  <section :class="embedded ? 'event-config-tab-pane' : 'content review-wide'">
    <template v-if="view === 'cards'">
      <div v-if="!embedded" class="review-titlebar"><div><h1>事件去重配置</h1><p>维护事件去重规则、执行策略和规则日志</p></div><button class="btn" @click="setRoute('eventConfig')">返回事件配置</button></div>
      <div class="event-config-rule-grid"><button class="event-config-rule-create" type="button" @click="openCreate"><span style="font-size:24px;">＋</span><span>点击创建事件过滤规则</span></button><article v-for="card in rules" :key="card.id" class="event-config-rule-card"><div class="event-config-rule-head"><strong>{{ card.name }}</strong><div class="event-config-rule-menu"><button type="button" aria-label="规则菜单">☰</button><div class="event-config-rule-menu-drop"><button type="button" @click="openDetail(card)">详情</button><button type="button" @click="openLogs(card)">日志</button><button type="button" @click="openEdit(card)">编辑</button><button type="button" class="danger" @click="removeRule(card)">删除</button></div></div></div><span><em v-if="card.enabled">已生效</em></span><p>{{ card.strategy }}：{{ cardParams(card) }}</p><button class="event-config-switch" :class="{ active: card.enabled }" type="button" :aria-label="card.enabled ? '已启用' : '已停用'" @click="toggleRule(card)"></button></article></div>
      <p v-if="loading" style="color:#98a2b3;font-size:13px;padding:12px 4px;">加载中...</p>
      <p v-else-if="!rules.length" style="color:#98a2b3;font-size:13px;padding:12px 4px;">暂无去重规则，点击左侧按钮创建</p>
    </template>
    <template v-else>
      <div class="review-titlebar"><div><h1>{{ editingId ? "编辑去重规则" : "新增去重规则" }}</h1><p>配置事件属性、关联算法、摄像头范围和执行策略</p></div><button class="btn" @click="view = 'cards'">← 返回</button></div>
      <div class="event-config-page-board" style="min-height:0;margin-bottom:14px;">
        <h4 class="event-config-section-title">事件属性</h4>
        <div class="event-config-form-grid">
          <label class="event-config-field"><span>* 名称</span><input v-model="form.name" class="input" /></label>
          <label class="event-config-field"><span>* 关联算法</span><select v-model="form.algorithm" class="select"><option>区域入侵</option><option>车辆违停</option><option>垃圾识别</option></select></label>
          <label class="event-config-field"><span>* 摄像头</span><span class="event-config-input-group"><input v-model="form.camera" class="input" :placeholder="camerasFailed ? '输入摄像头名称' : '搜索摄像头'" /><button v-if="camerasFailed" class="event-config-input-button" type="button" @click="addManualCamera">添加</button></span></label>
          <div class="event-config-field"><span>摄像头范围</span><div class="event-config-radio-row"><label><input type="checkbox" v-model="form.allCameras" /> 全选</label><label v-for="name in cameraChoices" :key="name"><input type="checkbox" :value="name" v-model="form.cameras" /> {{ name }}</label><span v-if="!camerasFailed && !camerasLoading && !cameraChoices.length" style="color:#98a2b3;font-size:12px;">无匹配摄像头</span><span v-if="camerasLoading" style="color:#98a2b3;font-size:12px;">摄像头加载中...</span></div></div>
        </div>
      </div>
      <div class="event-config-page-board" style="min-height:0;margin-bottom:14px;">
        <h4 class="event-config-section-title">执行策略</h4>
        <div class="event-config-tabs"><button v-for="tab in tabs" :key="tab" type="button" :class="{ active: form.tab === tab }" @click="form.tab = tab">{{ tab }}</button></div>
        <div class="event-config-form-grid">
          <label class="event-config-field"><span>* 时间长度</span><span class="event-config-input-group"><input v-model="form.duration" class="input" /><em class="event-config-input-addon">分钟</em></span></label>
          <label class="event-config-field"><span>* 相似度</span><input v-model="form.similarity" class="input" /></label>
        </div>
      </div>
      <div class="event-config-page-board" style="min-height:0;">
        <h4 class="event-config-section-title">备注说明</h4>
        <textarea v-model="form.remark" placeholder="请填写说明，最多不超过200字" style="width:100%;min-height:86px;padding:8px 10px;border:1px solid #cbd5df;border-radius:6px;font:inherit;resize:vertical;"></textarea>
      </div>
      <div class="event-config-modal-actions"><button class="btn" @click="resetForm">重置</button><button class="btn primary" :disabled="saving" @click="submit">提交</button><button class="btn" @click="view = 'cards'">返回</button></div>
    </template>
    <div v-if="modal === 'logs'" class="event-config-modal-mask" @click.self="modal = null">
      <section class="event-config-modal" role="dialog" aria-modal="true" aria-label="规则日志">
        <div class="event-config-modal-head"><h3>规则日志</h3><button class="event-config-modal-close" aria-label="关闭" @click="modal = null">×</button></div>
        <div class="event-config-log-filters"><select v-model="logFilters.eventType" class="select"><option value="">事件类型</option></select><input v-model="logFilters.ruleName" class="input" placeholder="规则名称" /><select v-model="logFilters.device" class="select"><option value="">设备名称</option></select><select v-model="logFilters.ruleType" class="select"><option value="">规则类型</option></select><select v-model="logFilters.status" class="select"><option value="">执行状态</option></select><input v-model="logFilters.range" class="input" placeholder="开始日期  ->  结束日期" /><button class="btn" @click="resetLogFilters">重置</button><button class="btn primary" @click="showToast('已按当前条件查询')">查询</button></div>
        <div class="table-wrap"><table class="prototype-table"><thead><tr><th class="left">设备名称</th><th>规则名称</th><th>算法类型</th><th>规则类型</th><th>执行状态</th><th>过滤数量</th><th>执行时间</th><th>操作</th></tr></thead><tbody><tr><td colspan="8" class="empty-cell">暂无数据</td></tr></tbody></table></div>
        <div class="event-config-pagination"><button type="button" aria-label="上一页" :disabled="activePage === 1" @click="activePage--">‹</button><button v-for="page in [1, 2, 3]" :key="page" type="button" :class="{ active: activePage === page }" @click="activePage = page">{{ page }}</button><span>…</span><button type="button" :class="{ active: activePage === 9 }" @click="activePage = 9">9</button><select class="select" aria-label="每页条数"><option>10条/页</option><option>20条/页</option></select><span>跳至</span><input class="input" type="number" min="1" value="5" aria-label="跳至页码" /><span>页</span></div>
      </section>
    </div>
    <div v-if="modal === 'detail'" class="event-config-modal-mask" @click.self="modal = null">
      <section class="event-config-modal" role="dialog" aria-modal="true" aria-label="事件规则详情">
        <div class="event-config-modal-head"><h3><button class="link-blue" style="padding:0;" aria-label="返回规则日志" @click="modal = 'logs'">←</button> 事件规则详情</h3><button class="event-config-modal-close" aria-label="关闭" @click="modal = null">×</button></div>
        <div class="event-config-detail-grid"><span><b>规则名称：</b>{{ selectedRule ? selectedRule.name : "--" }}</span><span><b>规则状态：</b>{{ selectedRule && selectedRule.enabled ? "已生效" : "未生效" }}</span><span><b>关联算法：</b>{{ selectedRule ? selectedRule.algorithm : "--" }}</span><span><b>过滤类型：</b>{{ selectedRule ? selectedRule.strategy : "--" }}</span><span><b>{{ selectedRule && selectedRule.strategy === "时间维度去重" ? "过滤时长：" : "相似度：" }}</b>{{ selectedRule ? detailParam(selectedRule) : "--" }}</span><span><b>设备名称：</b>{{ selectedRule ? detailCameras(selectedRule) : "--" }}</span></div>
        <h4 class="event-config-section-title">过滤详情</h4>
        <div class="event-config-filter-preview"><em>已保留</em><b><span>相似度</span><span>95</span></b><strong>2024-09-27 13:33:46</strong></div>
      </section>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { api } from "../api";
import type { DedupRule, DedupRulePayload } from "../types";

export default defineComponent({
  name: "EventConfigDedupPage",
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm", "embedded"],
  inject: {
    setRoute: { from: "setRoute", default: (route: string, options?: any) => {} },
    showToast: { from: "showToast", default: (message: string) => {} },
  },
  data() {
    return {
      view: "cards",
      modal: null as string | null,
      activePage: 1,
      tabs: ["时间维度去重", "区间重叠图像去重", "实时重叠图像去重"],
      rules: [] as DedupRule[],
      loading: false,
      saving: false,
      editingId: null as string | null,
      selectedRule: null as DedupRule | null,
      cameraOptions: [] as string[],
      camerasLoading: false,
      camerasFailed: false,
      form: { name: "去重", algorithm: "区域入侵", camera: "", allCameras: true, cameras: [] as string[], tab: "时间维度去重", duration: "", similarity: "", remark: "" },
      logFilters: { eventType: "", ruleName: "", device: "", ruleType: "", status: "", range: "" }
    };
  },
  computed: {
    cameraChoices(): string[] {
      // 接口失败时降级为手输：勾选列表直接回显已手输的摄像头名
      if (this.camerasFailed) return this.form.cameras;
      const value = this.form.camera.trim().toLowerCase();
      return value ? this.cameraOptions.filter(name => name.toLowerCase().includes(value)) : this.cameraOptions;
    }
  },
  mounted() {
    this.loadRules();
    this.loadCameras();
  },
  methods: {
    async loadRules() {
      if (this.loading) return;
      this.loading = true;
      try {
        this.rules = await api.eventDedupRules();
      } catch (error) {
        this.showToast(error instanceof Error ? error.message : "去重规则加载失败");
      } finally {
        this.loading = false;
      }
    },
    async loadCameras() {
      this.camerasLoading = true;
      try {
        const cameras = await api.cameras();
        this.cameraOptions = (cameras || []).map(camera => camera.name).filter(Boolean);
        this.camerasFailed = false;
      } catch (error) {
        this.camerasFailed = true;
      } finally {
        this.camerasLoading = false;
      }
    },
    cardParams(rule: DedupRule): string {
      return rule.strategy === "时间维度去重" ? `过滤时长 ${rule.durationMinutes ?? 0}m` : `相似度 ${rule.similarity ?? "-"}`;
    },
    detailParam(rule: DedupRule): string {
      return rule.strategy === "时间维度去重" ? `${rule.durationMinutes ?? "--"} 分钟` : `${rule.similarity ?? "--"}`;
    },
    detailCameras(rule: DedupRule): string {
      return rule.allCameras ? "全部摄像头" : (rule.cameras || []).join("、") || "--";
    },
    blankForm() {
      return { name: "去重", algorithm: "区域入侵", camera: "", allCameras: true, cameras: [] as string[], tab: "时间维度去重", duration: "", similarity: "", remark: "" };
    },
    openCreate() { this.editingId = null; this.form = this.blankForm(); this.view = "create"; },
    openEdit(rule: DedupRule) {
      this.editingId = rule.id;
      this.form = {
        name: rule.name,
        algorithm: rule.algorithm || "区域入侵",
        camera: "",
        allCameras: rule.allCameras,
        cameras: [...(rule.cameras || [])],
        tab: this.tabs.includes(rule.strategy) ? rule.strategy : "时间维度去重",
        duration: rule.durationMinutes != null ? String(rule.durationMinutes) : "",
        similarity: rule.similarity != null ? String(rule.similarity) : "",
        remark: rule.remark || ""
      };
      this.view = "create";
    },
    addManualCamera() {
      const name = this.form.camera.trim();
      if (!name) { this.showToast("请输入摄像头名称"); return; }
      if (!this.form.cameras.includes(name)) this.form.cameras.push(name);
      this.form.camera = "";
    },
    resetForm() { const editingId = this.editingId; this.form = this.blankForm(); this.editingId = editingId; },
    buildPayload(enabled: boolean): DedupRulePayload {
      const timed = this.form.tab === "时间维度去重";
      return {
        name: this.form.name.trim(),
        algorithm: this.form.algorithm,
        strategy: this.form.tab,
        durationMinutes: timed && this.form.duration !== "" ? Number(this.form.duration) : null,
        similarity: !timed && this.form.similarity !== "" ? Number(this.form.similarity) : null,
        allCameras: this.form.allCameras,
        cameras: this.form.allCameras ? [] : [...this.form.cameras],
        remark: this.form.remark.trim(),
        enabled
      };
    },
    async submit() {
      if (!this.form.name.trim()) { this.showToast("请填写规则名称"); return; }
      if (!this.form.allCameras && !this.form.cameras.length) { this.showToast("请选择摄像头或勾选全选"); return; }
      if (this.saving) return;
      const editing = this.editingId ? this.rules.find(rule => rule.id === this.editingId) : null;
      const payload = this.buildPayload(editing ? editing.enabled : true);
      this.saving = true;
      try {
        if (editing) {
          await api.updateEventDedupRule(editing.id, payload);
          this.showToast(`去重规则已更新：${payload.name}`);
        } else {
          await api.createEventDedupRule(payload);
          this.showToast(`去重规则已提交：${payload.name}`);
        }
        this.view = "cards";
        await this.loadRules();
      } catch (error) {
        this.showToast(error instanceof Error ? error.message : "去重规则保存失败");
      } finally {
        this.saving = false;
      }
    },
    async toggleRule(rule: DedupRule) {
      try {
        await api.updateEventDedupRule(rule.id, {
          name: rule.name,
          algorithm: rule.algorithm,
          strategy: rule.strategy,
          durationMinutes: rule.durationMinutes ?? null,
          similarity: rule.similarity ?? null,
          allCameras: rule.allCameras,
          cameras: rule.cameras || [],
          remark: rule.remark || "",
          enabled: !rule.enabled
        });
        this.showToast(`${rule.name}已${rule.enabled ? "停用" : "启用"}`);
        await this.loadRules();
      } catch (error) {
        this.showToast(error instanceof Error ? error.message : "规则状态更新失败");
      }
    },
    async removeRule(rule: DedupRule) {
      if (!window.confirm(`确认删除规则「${rule.name}」？`)) return;
      try {
        await api.deleteEventDedupRule(rule.id);
        this.showToast(`已删除规则：${rule.name}`);
        await this.loadRules();
      } catch (error) {
        this.showToast(error instanceof Error ? error.message : "去重规则删除失败");
      }
    },
    openDetail(rule: DedupRule) { this.selectedRule = rule; this.modal = "detail"; },
    openLogs(rule: DedupRule) { this.selectedRule = rule; this.modal = "logs"; },
    resetLogFilters() { this.logFilters = { eventType: "", ruleName: "", device: "", ruleType: "", status: "", range: "" }; }
  }
});
</script>
