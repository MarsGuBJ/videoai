<template>
  <section class="content review-wide">
    <div class="review-titlebar"><div><h1>事件接入</h1><p>管理外部告警数据源、接口地址、拉取方式和同步状态</p></div></div>
    <div class="event-config-page-board"><div class="event-config-filter"><div class="event-config-filter-left"><button class="btn primary" @click="openCreate">＋ 新增数据源</button><button class="btn" @click="setRoute('eventConfig')">返回事件配置</button><input v-model="keyword" class="input" style="width:220px;" placeholder="搜索数据源..." /></div></div>
      <div class="table-wrap"><table class="prototype-table"><thead><tr><th class="left">数据源名称</th><th>接口地址</th><th>事件类型</th><th>拉取频率</th><th>状态</th><th>最后同步</th><th>操作</th></tr></thead><tbody><tr v-for="(row, index) in filteredRows" :key="row.name"><td class="left"><span class="event-config-source-dot" :class="statusClass(row.status)"></span>{{ row.name }}</td><td><code>{{ row.endpoint }}</code></td><td><div class="event-config-tags"><span v-for="type in row.types" :key="type" class="event-config-tag">{{ type }}</span></div></td><td>{{ row.frequency }}</td><td><span class="event-config-status" :class="statusClass(row.status)">{{ row.status }}</span></td><td>{{ row.sync }}</td><td><div class="event-config-actions"><button class="link-blue" @click="openEdit(row)">编辑</button><button class="link-blue danger" @click="remove(index)">删除</button></div></td></tr><tr v-if="!filteredRows.length"><td colspan="7" class="empty-cell">暂无匹配数据源</td></tr></tbody></table></div>
      <div class="event-config-table-footer"><span>显示 1-{{ filteredRows.length }} 共 8 条记录</span><div class="event-config-pagination"><button type="button" aria-label="上一页" :disabled="activePage === 1" @click="activePage--">‹</button><button v-for="page in [1, 2, 3]" :key="page" type="button" :class="{ active: activePage === page }" @click="activePage = page">{{ page }}</button><span>…</span><button type="button" :class="{ active: activePage === 9 }" @click="activePage = 9">9</button><select class="select" aria-label="每页条数"><option>10条/页</option><option>20条/页</option></select><span>跳至</span><input class="input" type="number" min="1" value="5" aria-label="跳至页码" /><span>页</span></div></div>
    </div>
    <div v-if="modalOpen" class="event-config-modal-mask" @click.self="closeForm">
      <section class="event-config-modal" role="dialog" aria-modal="true" aria-label="新增告警数据源">
        <div class="event-config-modal-head"><h3>{{ editing ? "编辑告警数据源" : "新增告警数据源" }}</h3><button class="event-config-modal-close" aria-label="关闭" @click="closeForm">×</button></div>
        <div class="event-config-form-grid">
          <label class="event-config-field"><span>* 数据源名称</span><input v-model="form.name" class="input" placeholder="请输入数据源名称" /></label>
          <label class="event-config-field"><span>启停状态</span><select v-model="form.enabledStatus" class="select"><option>启用</option><option>停用</option></select></label>
          <label class="event-config-field wide"><span>* 接口地址</span><input v-model="form.endpoint" class="input" placeholder="https://api.example.com/v1/alerts" /></label>
          <label class="event-config-field"><span>拉取方式</span><select v-model="form.pullType" class="select"><option>定时拉取</option><option>实时推送</option></select></label>
          <label class="event-config-field"><span>拉取频率</span><select v-model="form.frequency" class="select" :disabled="form.pullType === '实时推送'"><option>每 5 分钟</option><option>每 10 分钟</option><option>每 30 分钟</option></select></label>
          <div class="event-config-field wide"><span>事件映射关系</span>
            <div class="event-config-mapping-box"><div v-for="(mapping, index) in form.mappings" :key="index" class="event-config-mapping-row"><input v-model="mapping.code" class="input" placeholder="外部事件编码" /><em>→</em><select v-model="mapping.type" class="select"><option value="" disabled>选择标准事件类型</option><option>人员入侵</option><option>烟火检测</option></select><button class="btn" type="button" aria-label="删除映射" :disabled="form.mappings.length <= 1" @click="removeMapping(index)">🗑</button></div><button class="btn" type="button" @click="addMapping">＋ 添加映射规则</button></div>
          </div>
          <label class="event-config-field wide"><span>描述</span><textarea v-model="form.desc" placeholder="请输入数据源描述（可选）"></textarea></label>
        </div>
        <div class="event-config-modal-actions"><button class="btn" @click="closeForm">取消</button><button class="btn primary" @click="save">保存配置</button></div>
      </section>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";

export default defineComponent({
  name: "EventConfigIngestionPage",
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  inject: {
    setRoute: { from: "setRoute", default: (route: string) => {} },
    showToast: { from: "showToast", default: (m: string) => {} },
  },
  data() {
    return {
      keyword: "",
      activePage: 1,
      modalOpen: false,
      editing: null as any,
      form: { name: "", enabledStatus: "启用", endpoint: "", pullType: "定时拉取", frequency: "每 5 分钟", mappings: [] as any[], desc: "" },
      rows: [
        { name: "云边协同平台 - 边缘算法", endpoint: "api.edge-cloud.com/v1/alerts", types: ["人员入侵", "车辆检测"], frequency: "每 5 分钟", status: "运行中", sync: "2024-01-15 14:30" },
        { name: "中心端布控算法平台", endpoint: "center-control.gov.cn/api/events", types: ["烟火检测", "安全帽"], frequency: "实时推送", status: "运行中", sync: "2024-01-15 14:32" },
        { name: "下游业务系统 A", endpoint: "business-system-a.com/webhook", types: ["区域入侵"], frequency: "每 10 分钟", status: "停止", sync: "2024-01-15 12:00" },
        { name: "视频事件平台", endpoint: "video-event.platform.cn/api", types: ["跌倒检测", "聚集检测"], frequency: "实时推送", status: "运行中", sync: "2024-01-15 14:31" },
        { name: "第三方告警服务", endpoint: "third-party-alerts.io/v2", types: ["设备异常"], frequency: "每 30 分钟", status: "停止", sync: "2024-01-15 10:00" }
      ]
    };
  },
  computed: {
    filteredRows(): any[] { const value = this.keyword.trim().toLowerCase(); return value ? this.rows.filter(row => `${row.name}${row.endpoint}`.toLowerCase().includes(value)) : this.rows; }
  },
  methods: {
    statusClass(status: string) { return status === "运行中" ? "" : status === "停止" ? "muted" : "error"; },
    blankForm() {
      return { name: "", enabledStatus: "启用", endpoint: "", pullType: "定时拉取", frequency: "每 5 分钟", mappings: [{ code: "", type: "" }], desc: "" };
    },
    openCreate() { this.editing = null; this.form = this.blankForm(); this.modalOpen = true; },
    openEdit(row: any) {
      this.editing = row;
      this.form = {
        name: row.name,
        enabledStatus: row.status === "停止" ? "停用" : "启用",
        endpoint: row.endpoint,
        pullType: row.frequency === "实时推送" ? "实时推送" : "定时拉取",
        frequency: row.frequency === "实时推送" ? "每 5 分钟" : row.frequency,
        mappings: row.types.map((type: string) => ({ code: "", type })),
        desc: ""
      };
      this.modalOpen = true;
    },
    closeForm() { this.modalOpen = false; },
    addMapping() { this.form.mappings.push({ code: "", type: "" }); },
    removeMapping(index: number) { if (this.form.mappings.length > 1) this.form.mappings.splice(index, 1); },
    save() {
      if (!this.form.name.trim() || !this.form.endpoint.trim()) { this.showToast("请填写数据源名称和接口地址"); return; }
      const types = this.form.mappings.map((mapping: any) => mapping.type).filter(Boolean);
      const payload = {
        name: this.form.name.trim(),
        endpoint: this.form.endpoint.trim(),
        types: types.length ? types : ["人员入侵"],
        frequency: this.form.pullType === "实时推送" ? "实时推送" : this.form.frequency,
        status: this.form.enabledStatus === "启用" ? "运行中" : "停止",
        sync: "2024-01-15 14:33"
      };
      if (this.editing) {
        Object.assign(this.editing, payload);
        this.showToast(`数据源已更新：${payload.name}`);
      } else {
        this.rows.push(payload);
        this.showToast(`数据源已保存：${payload.name}`);
      }
      this.closeForm();
    },
    remove(index: number) { const [row] = this.rows.splice(index, 1); this.showToast(`已删除数据源：${row.name}`); }
  }
});
</script>
