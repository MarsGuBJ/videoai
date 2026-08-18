<template>
  <section class="content review-wide">
    <div class="review-titlebar"><div><h1>消息订阅配置</h1><p>管理事件推送任务、推送地址、状态和推送日志</p></div><button class="btn" @click="setRoute('eventConfig')">返回事件配置</button></div>
    <div class="event-config-page-board"><div class="event-config-filter"><div class="event-config-filter-left"><button class="btn primary" @click="openCreate">＋ 新增推送</button><button class="btn primary" @click="showToast('已按当前条件查询')">查询</button><button class="btn" @click="reset">重置</button><button class="btn danger" @click="removeSelected">一键删除</button><span style="color:#41546a;font-size:13px;">搜索</span><input v-model="keyword" class="input" style="width:190px;" placeholder="请输入" /><span style="color:#41546a;font-size:13px;">推送类型</span><select v-model="type" class="select" style="width:120px;"><option value="">请选择</option><option value="mq">mq</option><option value="http">http</option></select></div></div>
      <div class="table-wrap"><table class="prototype-table"><thead><tr><th><input type="checkbox" aria-label="选择全部" :checked="allSelected" @change="toggleAll" /></th><th>序号</th><th class="left">任务名称</th><th>推送类型<span style="display:inline-grid;place-items:center;width:14px;height:14px;margin-left:4px;border:1px solid #b6c2cf;border-radius:50%;color:#98a2b3;font-size:10px;vertical-align:middle;">?</span></th><th>推送地址<span style="display:inline-grid;place-items:center;width:14px;height:14px;margin-left:4px;border:1px solid #b6c2cf;border-radius:50%;color:#98a2b3;font-size:10px;vertical-align:middle;">?</span></th><th>状态</th><th>描述</th><th>操作</th></tr></thead><tbody><tr v-for="(row, index) in filteredRows" :key="row.id"><td><input type="checkbox" :aria-label="'选择' + row.name" :checked="selectedIds.includes(row.id)" @change="toggleSelect(row.id)" /></td><td>{{ row.id }}</td><td class="left">{{ row.name }}</td><td>{{ row.type }}</td><td><code>{{ row.address }}</code></td><td><button class="event-config-switch" :class="{ active: row.enabled }" type="button" :aria-label="row.enabled ? '已启用' : '已停用'" @click="toggle(row)"></button></td><td>{{ row.desc }}</td><td><div class="event-config-actions"><button class="link-blue" @click="openLogs(row)">推送日志</button><button class="link-blue" @click="openEdit(row)">编辑</button><button class="link-blue danger" @click="remove(index)">删除</button></div></td></tr><tr v-if="!filteredRows.length"><td colspan="8" class="empty-cell">暂无匹配推送任务</td></tr></tbody></table></div>
      <div class="event-config-pagination"><button type="button" aria-label="上一页" :disabled="activePage === 1" @click="activePage--">‹</button><button v-for="page in [1, 2, 3]" :key="page" type="button" :class="{ active: activePage === page }" @click="activePage = page">{{ page }}</button><span>…</span><button type="button" :class="{ active: activePage === 9 }" @click="activePage = 9">9</button><select class="select" aria-label="每页条数"><option>10条/页</option><option>20条/页</option></select><span>跳至</span><input class="input" type="number" min="1" value="5" aria-label="跳至页码" /><span>页</span></div>
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
              <label class="event-config-field"><span>MQ地址密码</span><input v-model="form.mqPass" type="password" class="input" placeholder="请输入MQ地址密码" /></label>
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
        <div class="event-config-modal-actions"><button class="btn" @click="closeModal">取消</button><button class="btn primary" @click="save">确认</button></div>
      </section>
    </div>
    <div v-if="modal === 'logs'" class="event-config-modal-mask" @click.self="closeModal">
      <section class="event-config-modal" role="dialog" aria-modal="true" aria-label="推送日志">
        <div class="event-config-modal-head"><h3>推送日志</h3><button class="event-config-modal-close" aria-label="关闭" @click="closeModal">×</button></div>
        <div class="event-config-log-tabs"><button type="button" :class="{ active: logTab === 'latest' }" @click="logTab = 'latest'">最新推送</button><button type="button" :class="{ active: logTab === 'history' }" @click="logTab = 'history'">历史推送</button></div>
        <template v-if="logTab === 'latest'">
          <div class="event-config-log-meta"><span><b>推送任务名称：</b>公交车数据推送任务</span><span><b>最新推送时间：</b>--</span><span><b>推送结果：</b>--</span><span style="display:flex;align-items:center;justify-content:space-between;gap:10px;"><b>推送内容：</b><button class="btn" type="button" @click="copySample">复制示例</button></span></div>
          <pre class="event-config-json-preview">{{ sampleJson }}</pre>
        </template>
        <template v-else>
          <div class="event-config-filter" style="justify-content:flex-start;"><div class="event-config-filter-left"><select v-model="historyFilters.result" class="select" style="width:140px;"><option value="">推送结果</option><option>成功</option><option>失败</option></select><input v-model="historyFilters.range" class="input" style="width:220px;" placeholder="开始日期  至  结束日期" /><button class="btn primary" @click="showToast('已按当前条件查询')">查询</button></div></div>
          <div class="table-wrap"><table class="prototype-table"><thead><tr><th>序号</th><th class="left">推送任务名称</th><th>推送结果</th><th>失败信息</th><th>推送内容</th><th>推送时间</th></tr></thead><tbody><tr><td colspan="6" class="empty-cell">暂无数据</td></tr></tbody></table></div>
          <div class="event-config-pagination"><button type="button" aria-label="上一页" :disabled="activePage === 1" @click="activePage--">‹</button><button v-for="page in [1, 2, 3]" :key="page" type="button" :class="{ active: activePage === page }" @click="activePage = page">{{ page }}</button><span>…</span><button type="button" :class="{ active: activePage === 9 }" @click="activePage = 9">9</button><select class="select" aria-label="每页条数"><option>10条/页</option><option>20条/页</option></select><span>跳至</span><input class="input" type="number" min="1" value="5" aria-label="跳至页码" /><span>页</span></div>
        </template>
      </section>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";

export default defineComponent({
  name: "EventConfigSubscriptionsPage",
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  inject: {
    setRoute: { from: "setRoute", default: (route: string, options?: any) => {} },
    showToast: { from: "showToast", default: (message: string) => {} },
  },
  data() {
    return {
      keyword: "",
      type: "",
      activePage: 1,
      modal: null as string | null,
      logTab: "latest",
      editing: null as any,
      selectedIds: [] as number[],
      form: { name: "", pushType: "mq", mqAddr: "", mqUser: "", mqPass: "", token: "", address: "", expireDays: 30, desc: "", eventSource: "", eventTypes: "" },
      historyFilters: { result: "", range: "" },
      rows: [
        { id: 1, name: "安防推送", type: "mq", address: "anfang_topic", enabled: true, desc: "这里推送部分安防的事件" },
        { id: 2, name: "场景编排", type: "http", address: "http:123.123.123.132", enabled: false, desc: "-" },
        { id: 3, name: "SXIN", type: "mq", address: "sin_topic", enabled: true, desc: "推给sxin" },
        { id: 4, name: "物业推送", type: "http", address: "http:234.243.234.324", enabled: false, desc: "-" }
      ],
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
    filteredRows() {
      const value = this.keyword.trim().toLowerCase();
      return this.rows.filter((row: any) => (!value || `${row.name}${row.address}`.toLowerCase().includes(value)) && (!this.type || row.type === this.type));
    },
    allSelected() { return this.rows.length > 0 && this.selectedIds.length === this.rows.length; }
  },
  methods: {
    reset() { this.keyword = ""; this.type = ""; },
    toggle(row: any) { row.enabled = !row.enabled; },
    toggleSelect(id: number) {
      this.selectedIds = this.selectedIds.includes(id) ? this.selectedIds.filter(item => item !== id) : this.selectedIds.concat(id);
    },
    toggleAll() { this.selectedIds = this.allSelected ? [] : this.rows.map(row => row.id); },
    removeSelected() {
      if (!this.selectedIds.length) { this.showToast("请先勾选要删除的推送任务"); return; }
      this.rows = this.rows.filter(row => !this.selectedIds.includes(row.id));
      this.selectedIds = [];
      this.showToast("已删除选中的推送任务");
    },
    remove(index: number) { const [row] = this.rows.splice(index, 1); this.selectedIds = this.selectedIds.filter(id => id !== row.id); this.showToast(`已删除推送任务：${row.name}`); },
    blankForm() { return { name: "", pushType: "mq", mqAddr: "", mqUser: "", mqPass: "", token: "", address: "", expireDays: 30, desc: "", eventSource: "", eventTypes: "" }; },
    openCreate() { this.editing = null; this.form = this.blankForm(); this.modal = "form"; },
    openEdit(row: any) {
      this.editing = row;
      this.form = { ...this.blankForm(), name: row.name, pushType: row.type, address: row.address, desc: row.desc === "-" ? "" : row.desc };
      this.modal = "form";
    },
    closeModal() { this.modal = null; },
    genToken() { this.form.token = `tk_${Math.random().toString(36).slice(2, 10)}`; this.showToast("已自动生成 TOKEN"); },
    step(delta: number) { this.form.expireDays = Math.max(1, (Number(this.form.expireDays) || 0) + delta); },
    save() {
      if (!this.form.name.trim() || !this.form.address.trim()) { this.showToast("请填写推送任务名称和推送地址"); return; }
      if (this.editing) {
        Object.assign(this.editing, { name: this.form.name.trim(), type: this.form.pushType, address: this.form.address.trim(), desc: this.form.desc.trim() || "-" });
        this.showToast(`推送任务已更新：${this.form.name}`);
      } else {
        const nextId = Math.max(0, ...this.rows.map(row => row.id)) + 1;
        this.rows.push({ id: nextId, name: this.form.name.trim(), type: this.form.pushType, address: this.form.address.trim(), enabled: true, desc: this.form.desc.trim() || "-" });
        this.showToast(`推送任务已保存：${this.form.name}`);
      }
      this.closeModal();
    },
    openLogs(row: any) { this.logTab = "latest"; this.modal = "logs"; this.showToast(`已打开推送日志：${row.name}`); },
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
