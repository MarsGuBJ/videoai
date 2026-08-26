<template>
  <section :class="embedded ? 'event-config-tab-pane' : 'content review-wide'">
    <div v-if="!embedded" class="review-titlebar"><div><h1>消息订阅配置</h1><p>管理事件推送任务、推送地址、状态和推送日志</p></div><button class="btn" @click="setRoute('eventConfig')">返回事件配置</button></div>
    <div class="event-config-page-board"><div class="event-config-filter"><div class="event-config-filter-left"><button class="btn primary" @click="openCreate">＋ 新增推送</button><button class="btn primary" @click="showToast('已按当前条件查询')">查询</button><button class="btn" @click="reset">重置</button><button class="btn danger" @click="removeSelected">一键删除</button><span style="color:#41546a;font-size:13px;">搜索</span><input v-model="keyword" class="input" style="width:190px;" placeholder="请输入" /><span style="color:#41546a;font-size:13px;">推送类型</span><select v-model="type" class="select" style="width:120px;"><option value="">请选择</option><option value="mq">mq</option><option value="http">http</option></select></div></div>
      <div class="table-wrap"><table class="prototype-table"><thead><tr><th><input type="checkbox" aria-label="选择全部" :checked="allSelected" @change="toggleAll" /></th><th>序号</th><th class="left">任务名称</th><th>推送类型<span style="display:inline-grid;place-items:center;width:14px;height:14px;margin-left:4px;border:1px solid #b6c2cf;border-radius:50%;color:#98a2b3;font-size:10px;vertical-align:middle;">?</span></th><th>推送地址<span style="display:inline-grid;place-items:center;width:14px;height:14px;margin-left:4px;border:1px solid #b6c2cf;border-radius:50%;color:#98a2b3;font-size:10px;vertical-align:middle;">?</span></th><th>状态</th><th>描述</th><th>操作</th></tr></thead><tbody><tr v-for="(row, index) in paginatedRows" :key="row.id"><td><input type="checkbox" :aria-label="'选择' + row.name" :checked="selectedIds.includes(row.id)" @change="toggleSelect(row.id)" /></td><td>{{ (activePage - 1) * pageSize + index + 1 }}</td><td class="left">{{ row.name }}</td><td>{{ row.type }}</td><td><code>{{ row.address }}</code></td><td><button class="event-config-switch" :class="{ active: row.enabled }" type="button" :aria-label="row.enabled ? '已启用' : '已停用'" @click="toggle(row)"></button></td><td>{{ row.desc || "-" }}</td><td><div class="event-config-actions"><button class="link-blue" @click="openLogs(row)">推送日志</button><button class="link-blue" @click="openEdit(row)">编辑</button><button class="link-blue danger" @click="remove(row)">删除</button></div></td></tr><tr v-if="!loading && !paginatedRows.length"><td colspan="8" class="empty-cell">暂无匹配推送任务</td></tr><tr v-if="loading"><td colspan="8" class="empty-cell">加载中...</td></tr></tbody></table></div>
      <div class="event-config-pagination"><span style="color:#98a2b3;font-size:11px;margin-right:auto;">共 {{ filteredRows.length }} 条</span><button type="button" aria-label="上一页" :disabled="activePage === 1" @click="activePage--">‹</button><button v-for="page in pageCount" :key="page" type="button" :class="{ active: activePage === page }" @click="activePage = page">{{ page }}</button><button type="button" aria-label="下一页" :disabled="activePage === pageCount" @click="activePage++">›</button><select class="select" v-model.number="pageSize" aria-label="每页条数" @change="activePage = 1"><option :value="10">10条/页</option><option :value="20">20条/页</option><option :value="50">50条/页</option></select></div>
    </div>
    <div v-if="modal === 'form'" class="event-config-modal-mask" @click.self="closeModal">
      <section class="event-config-modal wide" role="dialog" aria-modal="true" :aria-label="editing ? '编辑推送任务' : '新增推送任务'">
        <div class="event-config-modal-head"><h3>{{ editing ? "编辑推送任务" : "新增推送任务" }}</h3><button class="event-config-modal-close" aria-label="关闭" @click="closeModal">×</button></div>
        <section>
          <h4 class="event-config-section-title">基础信息</h4>
          <div class="event-config-form-grid cols-3">
            <label class="event-config-field"><span>* 推送任务名称</span><input v-model="form.name" class="input" placeholder="请输入推送任务名称" /></label>
            <div class="event-config-field"><span>* 推送类型</span><div class="event-config-radio-row"><label><input type="radio" value="mq" v-model="form.pushType" /> MQ</label><label><input type="radio" value="http" v-model="form.pushType" /> HTTP</label></div></div>
            <template v-if="form.pushType === 'mq'">
              <label class="event-config-field"><span>* MQ地址</span><input v-model="form.mqAddr" class="input" placeholder="请输入MQ地址" /></label>
              <label class="event-config-field"><span>MQ地址用户名</span><input v-model="form.mqUser" class="input" placeholder="请输入MQ地址用户名" /></label>
              <label class="event-config-field"><span>MQ地址密码</span><input v-model="form.mqPass" type="password" class="input" :placeholder="editing && editing.mqPassConfigured ? '已配置，留空则不修改' : '请输入MQ地址密码'" /></label>
            </template>
            <label v-else class="event-config-field"><span>* TOKEN</span><span class="event-config-input-group"><input v-model="form.token" class="input" placeholder="请输入TOKEN" /><button class="event-config-input-button" type="button" @click="genToken">自动生成</button></span></label>
            <label class="event-config-field"><span>* 推送地址</span><input v-model="form.address" class="input" placeholder="请输入推送地址" /></label>
            <div class="event-config-field"><span>* 推送记录过期时间</span><span class="event-config-stepper"><button type="button" aria-label="减少天数" @click="step(-1)">−</button><input v-model.number="form.expireDays" type="number" min="1" aria-label="过期天数" /><button type="button" aria-label="增加天数" @click="step(1)">＋</button><em class="event-config-input-addon">天</em></span></div>
            <label class="event-config-field wide"><span>描述</span><textarea v-model="form.desc" placeholder="请输入描述"></textarea></label>
          </div>
        </section>
        <section>
          <h4 class="event-config-section-title">推送内容</h4>
          <div class="event-config-form-grid">
            <label class="event-config-field"><span>* 事件来源</span><input v-model="form.eventSource" class="input" /></label>
            <label class="event-config-field"><span>* 事件类型</span><input v-model="form.eventTypes" class="input" /></label>
          </div>
        </section>
        <div class="event-config-modal-actions"><button class="btn" @click="closeModal">取消</button><button class="btn primary" :disabled="saving" @click="save">确认</button></div>
      </section>
    </div>
    <div v-if="modal === 'logs'" class="event-config-modal-mask" @click.self="closeModal">
      <section class="event-config-modal" role="dialog" aria-modal="true" aria-label="推送日志">
        <div class="event-config-modal-head"><h3>推送日志</h3><button class="event-config-modal-close" aria-label="关闭" @click="closeModal">×</button></div>
        <div class="event-config-log-tabs"><button type="button" :class="{ active: logTab === 'latest' }" @click="logTab = 'latest'">最新推送</button><button type="button" :class="{ active: logTab === 'history' }" @click="logTab = 'history'">历史推送</button></div>
        <template v-if="logTab === 'latest'">
          <div class="event-config-log-meta"><span><b>推送任务名称：</b>{{ logTask ? logTask.name : "--" }}</span><span><b>最新推送时间：</b>--</span><span><b>推送结果：</b>--</span><span style="display:flex;align-items:center;justify-content:space-between;gap:10px;"><b>推送内容：</b><button class="btn" type="button" @click="copySample">复制示例</button></span></div>
          <pre class="event-config-json-preview">{{ sampleJson }}</pre>
        </template>
        <template v-else>
          <div class="event-config-filter" style="justify-content:flex-start;"><div class="event-config-filter-left"><select v-model="historyFilters.result" class="select" style="width:140px;"><option value="">推送结果</option><option>成功</option><option>失败</option></select><input v-model="historyFilters.range" class="input" style="width:220px;" placeholder="开始日期  至  结束日期" /><button class="btn primary" @click="showToast('已按当前条件查询')">查询</button></div></div>
          <div class="table-wrap"><table class="prototype-table"><thead><tr><th>序号</th><th class="left">推送任务名称</th><th>推送结果</th><th>失败信息</th><th>推送内容</th><th>推送时间</th></tr></thead><tbody><tr><td colspan="6" class="empty-cell">暂无数据</td></tr></tbody></table></div>
          <div class="event-config-pagination"><button type="button" aria-label="上一页" :disabled="historyPage === 1" @click="historyPage--">‹</button><button v-for="page in [1, 2, 3]" :key="page" type="button" :class="{ active: historyPage === page }" @click="historyPage = page">{{ page }}</button><span>…</span><button type="button" :class="{ active: historyPage === 9 }" @click="historyPage = 9">9</button><select class="select" aria-label="每页条数"><option>10条/页</option><option>20条/页</option></select><span>跳至</span><input class="input" type="number" min="1" value="5" aria-label="跳至页码" /><span>页</span></div>
        </template>
      </section>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { api } from "../api";
import type { PushTask, PushTaskPayload } from "../types";

export default defineComponent({
  name: "EventConfigSubscriptionsPage",
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm", "embedded"],
  inject: {
    setRoute: { from: "setRoute", default: (route: string, options?: any) => {} },
    showToast: { from: "showToast", default: (message: string) => {} },
  },
  data() {
    return {
      keyword: "",
      type: "",
      activePage: 1,
      pageSize: 10,
      historyPage: 1,
      modal: null as string | null,
      logTab: "latest",
      logTask: null as PushTask | null,
      editing: null as PushTask | null,
      selectedIds: [] as string[],
      rows: [] as PushTask[],
      loading: false,
      saving: false,
      form: { name: "", pushType: "mq" as "mq" | "http", mqAddr: "", mqUser: "", mqPass: "", token: "", address: "", expireDays: 30, desc: "", eventSource: "", eventTypes: "" },
      historyFilters: { result: "", range: "" },
      sampleJson: `{
  "deviceId": "string",
  "deviceCode": "string",
  "deviceData": {
    "lightControlGridActivePower": {
      "id": null,
      "deviceId": "yunzhisheng89",
      "name": "灯控功率",
      "code": "lightControlGridActivePower",
      "dataType": "STRING",
      "value": {
        "value_real": "0",
        "value_format": "0",
        "value": "0"
      },
      "lastTime": "2023-02-17 16:01:19"
    }
  },
  "deviceStatus": "NORMAL",
  "warnMessages": []
}`
    };
  },
  computed: {
    filteredRows(): PushTask[] {
      const value = this.keyword.trim().toLowerCase();
      return this.rows.filter(row => (!value || `${row.name}${row.address}`.toLowerCase().includes(value)) && (!this.type || row.type === this.type));
    },
    pageCount(): number {
      return Math.max(1, Math.ceil(this.filteredRows.length / this.pageSize));
    },
    paginatedRows(): PushTask[] {
      const start = (this.activePage - 1) * this.pageSize;
      return this.filteredRows.slice(start, start + this.pageSize);
    },
    allSelected(): boolean { return this.rows.length > 0 && this.selectedIds.length === this.rows.length; }
  },
  mounted() {
    this.loadRows();
  },
  methods: {
    reset() { this.keyword = ""; this.type = ""; this.activePage = 1; },
    async loadRows() {
      if (this.loading) return;
      this.loading = true;
      try {
        this.rows = await api.eventPushTasks();
      } catch (error) {
        this.showToast(error instanceof Error ? error.message : "推送任务加载失败");
      } finally {
        this.loading = false;
      }
    },
    async toggle(row: PushTask) {
      try {
        await api.updateEventPushTask(row.id, {
          name: row.name,
          type: row.type,
          address: row.address,
          mqAddr: row.mqAddr || "",
          mqUser: row.mqUser || "",
          token: row.token || "",
          expireDays: row.expireDays,
          eventSource: row.eventSource || "",
          eventTypes: row.eventTypes || "",
          desc: row.desc || "",
          enabled: !row.enabled
        });
        this.showToast(`${row.name}已${row.enabled ? "停用" : "启用"}`);
        await this.loadRows();
      } catch (error) {
        this.showToast(error instanceof Error ? error.message : "推送任务状态更新失败");
      }
    },
    toggleSelect(id: string) {
      this.selectedIds = this.selectedIds.includes(id) ? this.selectedIds.filter(item => item !== id) : this.selectedIds.concat(id);
    },
    toggleAll() { this.selectedIds = this.allSelected ? [] : this.rows.map(row => row.id); },
    async removeSelected() {
      if (!this.selectedIds.length) { this.showToast("请先勾选要删除的推送任务"); return; }
      if (!window.confirm(`确认删除选中的 ${this.selectedIds.length} 个推送任务？`)) return;
      try {
        for (const id of this.selectedIds) {
          await api.deleteEventPushTask(id);
        }
        this.selectedIds = [];
        this.showToast("已删除选中的推送任务");
        if (this.activePage > 1 && this.paginatedRows.length === 1) this.activePage--;
        await this.loadRows();
      } catch (error) {
        this.showToast(error instanceof Error ? error.message : "推送任务删除失败");
        await this.loadRows();
      }
    },
    async remove(row: PushTask) {
      if (!window.confirm(`确认删除推送任务「${row.name}」？`)) return;
      try {
        await api.deleteEventPushTask(row.id);
        this.selectedIds = this.selectedIds.filter(id => id !== row.id);
        this.showToast(`已删除推送任务：${row.name}`);
        if (this.activePage > 1 && this.paginatedRows.length === 1) this.activePage--;
        await this.loadRows();
      } catch (error) {
        this.showToast(error instanceof Error ? error.message : "推送任务删除失败");
      }
    },
    blankForm() { return { name: "", pushType: "mq" as "mq" | "http", mqAddr: "", mqUser: "", mqPass: "", token: "", address: "", expireDays: 30, desc: "", eventSource: "", eventTypes: "" }; },
    openCreate() { this.editing = null; this.form = this.blankForm(); this.modal = "form"; },
    openEdit(row: PushTask) {
      this.editing = row;
      this.form = {
        ...this.blankForm(),
        name: row.name,
        pushType: row.type,
        mqAddr: row.mqAddr || "",
        mqUser: row.mqUser || "",
        mqPass: "",
        token: row.token || "",
        address: row.address,
        expireDays: row.expireDays || 30,
        desc: row.desc || "",
        eventSource: row.eventSource || "",
        eventTypes: row.eventTypes || ""
      };
      this.modal = "form";
    },
    closeModal() { this.modal = null; },
    genToken() { this.form.token = `tk_${Math.random().toString(36).slice(2, 10)}`; this.showToast("已自动生成 TOKEN"); },
    step(delta: number) { this.form.expireDays = Math.max(1, (Number(this.form.expireDays) || 0) + delta); },
    async save() {
      if (!this.form.name.trim()) { this.showToast("请填写推送任务名称"); return; }
      if (!this.form.address.trim()) { this.showToast("请填写推送地址"); return; }
      if (this.form.pushType === "mq" && !this.form.mqAddr.trim()) { this.showToast("请填写MQ地址"); return; }
      if (this.form.pushType === "http" && !this.form.token.trim()) { this.showToast("请填写TOKEN"); return; }
      if (!(Number(this.form.expireDays) >= 1)) { this.showToast("推送记录过期时间至少为 1 天"); return; }
      const payload: PushTaskPayload = {
        name: this.form.name.trim(),
        type: this.form.pushType,
        address: this.form.address.trim(),
        mqAddr: this.form.mqAddr.trim(),
        mqUser: this.form.mqUser.trim(),
        token: this.form.token.trim(),
        expireDays: Number(this.form.expireDays),
        eventSource: this.form.eventSource.trim(),
        eventTypes: this.form.eventTypes.trim(),
        desc: this.form.desc.trim(),
        enabled: this.editing ? this.editing.enabled : true
      };
      const mqPass = this.form.mqPass.trim();
      if (mqPass) payload.mqPass = mqPass;
      if (this.saving) return;
      this.saving = true;
      try {
        if (this.editing) {
          await api.updateEventPushTask(this.editing.id, payload);
          this.showToast(`推送任务已更新：${payload.name}`);
        } else {
          await api.createEventPushTask(payload);
          this.showToast(`推送任务已保存：${payload.name}`);
        }
        this.closeModal();
        await this.loadRows();
      } catch (error) {
        this.showToast(error instanceof Error ? error.message : "推送任务保存失败");
      } finally {
        this.saving = false;
      }
    },
    openLogs(row: PushTask) { this.logTask = row; this.logTab = "latest"; this.historyPage = 1; this.modal = "logs"; },
    copySample() {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(this.sampleJson).then(() => this.showToast("推送内容示例已复制"), () => this.showToast("复制失败，请手动选择复制"));
      } else {
        this.showToast("当前环境不支持自动复制");
      }
    }
  },
});
</script>
